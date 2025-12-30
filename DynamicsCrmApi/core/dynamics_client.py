# coding: utf-8
"""
Cliente HTTP para Dynamics 365 Web API con manejo de errores.
Adaptado de pruebas-azure-connections.
"""

import requests
from typing import Any, Dict, Optional
from shared.utils.logger import get_logger

from .dynamics_authenticator import Dynamics365Authenticator

logger = get_logger("Dynamics365Client")


class Dynamics365Client:
    """Cliente HTTP para realizar peticiones a Dynamics 365 Web API."""

    def __init__(
        self, authenticator: Dynamics365Authenticator, base_url: str
    ) -> None:
        """
        Inicializa el cliente con un autenticador y URL base.

        Args:
            authenticator: Instancia de Dynamics365Authenticator
            base_url: URL base de Dynamics 365 (ej: https://ccmadev.crm2.dynamics.com/api/data/v9.2)
        """
        self.authenticator = authenticator
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        """
        Obtiene un token válido para Dynamics 365.

        Returns:
            Token de acceso
        """
        if self._token is None:
            # Scope para Dynamics 365 es la URL del recurso + /.default
            # Ejemplo: https://ccmadev.crm2.dynamics.com/.default
            # MANTENER SIMPLE como en pruebas-azure-connections
            resource_url = self.base_url.split('/api/')[0]
            scope = f"{resource_url}/.default"
            
            # Validar que el scope sea correcto
            if not scope.startswith("https://"):
                logger.error(f"Scope inválido generado. base_url: '{self.base_url}', resource_url: '{resource_url}', scope: '{scope}'")
                raise ValueError(f"Scope inválido generado: '{scope}'. Verifica que dynamics_url sea correcto (ej: https://ccmadev.crm2.dynamics.com/api/data/v9.2)")
            
            logger.debug(f"Generando token con scope: {scope}")
            
            try:
                self._token = self.authenticator.get_token(scope=scope)
            except Exception as e:
                error_msg = str(e)
                # Mejorar mensaje de error para secret inválido
                if "AADSTS7000215" in error_msg or "Invalid client secret" in error_msg:
                    raise ValueError(
                        f"Error de autenticación con Dynamics 365:\n"
                        f"  - Verifica que el secret no haya expirado\n"
                        f"  - Verifica que estés usando el Secret VALUE (no el Secret ID)\n"
                        f"  - El secret debe estar activo en Azure Portal\n"
                        f"  - Scope usado: {scope}\n"
                        f"  - Error original: {error_msg[:200]}"
                    ) from e
                raise

        return self._token

    def _get_headers(self) -> Dict[str, str]:
        """
        Genera los headers necesarios para las peticiones.

        Returns:
            Diccionario con headers de autorización y contenido
        """
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Prefer": "return=representation",
        }

    def _get_headers_for_log(self) -> Dict[str, str]:
        """
        Genera los headers necesarios para logging (sin exponer el token completo).

        Returns:
            Diccionario con headers, pero con el token ocultado como [token] por seguridad
        """
        headers = self._get_headers()
        # Ocultar el token completo en el log por seguridad
        if "Authorization" in headers:
            headers["Authorization"] = "Bearer [token]"
        return headers

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Realiza una petición GET a Dynamics 365 API.

        Args:
            endpoint: Endpoint relativo (ej: "/sp_documentos")
            params: Parámetros de consulta OData opcionales

        Returns:
            Respuesta JSON como diccionario

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"GET {endpoint} - Parámetros: {params}")
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30,
            )

            # Mejorar mensajes de error con detalles de la respuesta
            if not response.ok:
                error_detail = ""
                error_message = ""
                try:
                    error_json = response.json()
                    error_obj = error_json.get('error', {})
                    error_message = error_obj.get('message', '')
                    error_detail = f" - {error_message}"
                    
                    # Mensajes específicos para errores comunes de Dynamics 365
                    if response.status_code == 403:
                        if "not a member of the organization" in error_message:
                            error_detail = (
                                "\n  ⚠️  La aplicación no tiene acceso al ambiente de Dynamics 365.\n"
                                "  Soluciones:\n"
                                "  1. Verifica que la aplicación tenga permisos API configurados en Azure AD\n"
                                "  2. Verifica que se hayan otorgado permisos de aplicación (Application permissions)\n"
                                "  3. Verifica que el admin haya dado consentimiento para la aplicación\n"
                                "  4. La aplicación necesita permisos en Dynamics 365 (no solo en Azure AD)\n"
                                f"  Error original: {error_message}"
                            )
                except ValueError:
                    error_detail = f" - {response.text[:200]}"
                
                logger.error(f"Error en GET {endpoint}: {response.status_code} {error_detail}")
                raise requests.HTTPError(
                    f"{response.status_code} Client Error: {response.reason} for url: {url}{error_detail}",
                    response=response,
                )

            result = response.json()
            logger.debug(f"GET {endpoint} - Respuesta exitosa: {len(str(result))} caracteres")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Error de red en GET {endpoint}: {str(e)}", exc_info=True)
            raise

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Realiza una petición PATCH a Dynamics 365 API.

        Args:
            endpoint: Endpoint relativo (ej: "/sp_documentos(guid)")
            data: Datos JSON a enviar

        Returns:
            Respuesta JSON como diccionario

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"PATCH {endpoint} - Datos: {data}")
            response = requests.patch(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=30,
            )

            # Mejorar mensajes de error con detalles de la respuesta
            if not response.ok:
                error_detail = ""
                try:
                    error_json = response.json()
                    error_detail = f" - {error_json.get('error', {}).get('message', '')}"
                except ValueError:
                    error_detail = f" - {response.text[:200]}"
                
                logger.error(f"Error en PATCH {endpoint}: {response.status_code} {error_detail}")
                raise requests.HTTPError(
                    f"{response.status_code} Client Error: {response.reason} for url: {url}{error_detail}",
                    response=response,
                )

            if response.status_code == 204 or not response.content:
                logger.debug(f"PATCH {endpoint} - Actualización exitosa (204 No Content)")
                return {}
            
            result = response.json()
            logger.debug(f"PATCH {endpoint} - Respuesta exitosa")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Error de red en PATCH {endpoint}: {str(e)}", exc_info=True)
            raise
