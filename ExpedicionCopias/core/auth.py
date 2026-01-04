"""Manejador de autenticación con Azure AD usando ClientSecretCredential."""
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError


class Dynamics365Authenticator:
    """Gestiona la autenticación con Dynamics 365 Web API."""

    def __init__(
        self, tenant_id: str, client_id: str, client_secret: str
    ) -> None:
        """
        Inicializa el autenticador con credenciales de Dynamics 365.

        Args:
            tenant_id: ID del tenant de Azure AD
            client_id: ID de la aplicación cliente
            client_secret: Secret de la aplicación cliente
        """
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
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            except Exception as e:
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
            token = credential.get_token(scope)
            return token.token
        except Exception as e:
            raise ClientAuthenticationError(
                f"Error al obtener token: {str(e)}"
            ) from e


class AzureAuthenticator:
    """Gestiona la autenticación con Microsoft Graph API."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        """
        Inicializa el autenticador con la configuración proporcionada.

        Args:
            tenant_id: ID del tenant de Azure AD
            client_id: ID de la aplicación cliente
            client_secret: Secret de la aplicación cliente
        """
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
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            except Exception as e:
                raise ClientAuthenticationError(
                    f"Error al crear credenciales: {str(e)}"
                ) from e

        return self._credential

    def get_token(self, scope: str = "https://graph.microsoft.com/.default") -> str:
        """
        Obtiene un token de acceso para Microsoft Graph.

        Args:
            scope: Scope del token (por defecto Graph API)

        Returns:
            Token de acceso como string

        Raises:
            ClientAuthenticationError: Si la autenticación falla
        """
        credential = self.get_credential()
        try:
            token = credential.get_token(scope)
            return token.token
        except Exception as e:
            raise ClientAuthenticationError(
                f"Error al obtener token: {str(e)}"
            ) from e
