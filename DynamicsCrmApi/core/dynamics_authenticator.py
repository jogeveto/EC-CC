# coding: utf-8
"""
Manejador de autenticación con Azure AD para Dynamics 365.
Adaptado de pruebas-azure-connections para usar credenciales desde variables Rocketbot.
"""

from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError
from shared.utils.logger import get_logger

logger = get_logger("Dynamics365Authenticator")


class Dynamics365Authenticator:
    """Gestiona la autenticación con Dynamics 365 Web API."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        """
        Inicializa el autenticador con credenciales de Dynamics 365.

        Args:
            tenant_id: ID del tenant de Azure AD
            client_id: ID de la aplicación cliente
            client_secret: Secret de la aplicación cliente
        """
        if not tenant_id or not client_id or not client_secret:
            raise ValueError("tenant_id, client_id y client_secret son requeridos")
        
        # Validar longitud mínima del secret (los secrets de Azure suelen tener al menos 20 caracteres)
        if len(client_secret) < 20:
            logger.warning(
                f"[SECRET_VALIDATION] El client_secret tiene solo {len(client_secret)} caracteres. "
                "Los secrets de Azure suelen tener al menos 20-40 caracteres. "
                "Verifica que el secret esté completo y no truncado."
            )
        
        # Logging seguro del secret para diagnóstico (solo primeros y últimos caracteres)
        secret_preview = ""
        if len(client_secret) >= 8:
            secret_preview = f"{client_secret[:4]}...{client_secret[-4:]}"
        else:
            secret_preview = "[SECRET DEMASIADO CORTO]"
        
        logger.debug(
            f"[AUTH_INIT] Inicializando autenticador: "
            f"tenant_id={tenant_id[:8]}..., client_id={client_id[:8]}..., "
            f"secret_length={len(client_secret)}, secret_preview={secret_preview}"
        )
        
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._credential: ClientSecretCredential | None = None

    def get_credential(self) -> ClientSecretCredential:
        """
        Obtiene o crea la credencial de Azure.

        Returns:
            ClientSecretCredential configurada

        Raises:
            ClientAuthenticationError: Si las credenciales son inválidas
        """
        if self._credential is None:
            try:
                # Logging detallado antes de crear la credencial (INFO para que siempre se muestre)
                logger.info(f"[AUTH_CREDENTIAL] Creando credencial - tenant_id: {self.tenant_id[:8]}..., client_id: {self.client_id[:8]}...")
                logger.info(f"[AUTH_CREDENTIAL] Secret length: {len(self.client_secret)}")
                logger.info(f"[AUTH_CREDENTIAL] repr(secret[:30]): {repr(self.client_secret[:30])}")
                
                # Verificar caracteres problemáticos antes de crear la credencial
                if '\n' in self.client_secret or '\r' in self.client_secret:
                    logger.warning("[AUTH_CREDENTIAL] WARNING: El secret contiene caracteres de nueva línea!")
                if self.client_secret != self.client_secret.strip():
                    logger.warning("[AUTH_CREDENTIAL] WARNING: El secret contiene espacios al inicio o final!")
                
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
                logger.info("[AUTH_CREDENTIAL] Credencial creada exitosamente")
            except Exception as e:
                logger.error(f"Error al crear credenciales: {str(e)}", exc_info=True)
                raise ClientAuthenticationError(
                    f"Error al crear credenciales: {str(e)}"
                ) from e

        return self._credential

    def get_token(self, scope: str) -> str:
        """
        Obtiene un token de acceso para Dynamics 365.

        Args:
            scope: Scope del token (ej: https://ccmadev.crm2.dynamics.com/.default)

        Returns:
            Token de acceso como string

        Raises:
            ClientAuthenticationError: Si la autenticación falla
        """
        credential = self.get_credential()
        try:
            logger.debug(f"Obteniendo token para scope: {scope}")
            token = credential.get_token(scope)
            logger.debug("Token obtenido exitosamente")
            return token.token
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error al obtener token: {error_msg}", exc_info=True)
            
            # Mejorar mensaje de error para secret inválido
            if "AADSTS7000215" in error_msg or "Invalid client secret" in error_msg:
                raise ClientAuthenticationError(
                    f"Error de autenticación con Dynamics 365:\n"
                    f"  - Verifica que el secret no haya expirado\n"
                    f"  - Verifica que estés usando el Secret VALUE (no el Secret ID)\n"
                    f"  - El secret debe estar activo en Azure Portal\n"
                    f"  - Scope usado: {scope}\n"
                    f"  - Error original: {error_msg[:200]}"
                ) from e
            raise ClientAuthenticationError(
                f"Error al obtener token: {error_msg}"
            ) from e
