# coding: utf-8
"""
Cliente base para Microsoft Graph API.
Maneja autenticación y operaciones base con la API.
"""

from typing import Optional, Dict, Any
from msal import ConfidentialClientApplication
import requests

from shared.utils.logger import get_logger

logger = get_logger("GraphApiClient")


class GraphApiClient:
    """
    Cliente base para Microsoft Graph API.
    Maneja autenticación y operaciones comunes.

    Args:
        config: Diccionario de configuración que debe contener:
            - client_id: ID de la aplicación Azure AD
            - client_secret: Secreto de la aplicación
            - tenant_id: ID del tenant de Azure AD
            - user_email: Email del usuario para operaciones
            - graph_api_endpoint: URL base de Graph API (opcional, por defecto usa v1.0)
            - graph_api_scopes: Lista de scopes requeridos (opcional, por defecto Mail.ReadWrite)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el cliente con la configuración proporcionada.

        Args:
            config: Diccionario de configuración con credenciales de Graph API
        """
        # Extraer configuración de email
        email_config = config.get("email", config)

        self.client_id = email_config.get("client_id")
        self.client_secret = email_config.get("client_secret")
        self.tenant_id = email_config.get("tenant_id")
        self.user_email = email_config.get("user_email")
        self.graph_api_endpoint = email_config.get(
            "graph_api_endpoint", "https://graph.microsoft.com/v1.0"
        )
        self.graph_api_scopes = email_config.get(
            "graph_api_scopes", ["https://graph.microsoft.com/.default"]
        )

        # Validar campos requeridos
        required_fields = ["client_id", "client_secret", "tenant_id", "user_email"]
        missing_fields = [
            field for field in required_fields if not email_config.get(field)
        ]
        if missing_fields:
            raise ValueError(
                f"Faltan campos requeridos en configuración: {missing_fields}"
            )

        self._access_token = None
        self._app = None

    @property
    def app(self) -> ConfidentialClientApplication:
        """Obtiene o crea la aplicación cliente de MSAL."""
        if not self._app:
            self._app = ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            )
        return self._app

    def get_token(self) -> str:
        """
        Obtiene un token de acceso para Microsoft Graph API.

        Returns:
            str: Token de acceso

        Raises:
            ValueError: Si no se puede obtener el token
        """
        if not self._access_token:
            try:
                logger.info(f"Obteniendo token con scopes: {self.graph_api_scopes}")

                result = self.app.acquire_token_silent(
                    scopes=self.graph_api_scopes, account=None
                )
                if not result:
                    logger.info(
                        "Token silent falló, intentando acquire_token_for_client"
                    )
                    result = self.app.acquire_token_for_client(
                        scopes=self.graph_api_scopes
                    )

                if "access_token" not in result:
                    error_desc = result.get("error_description", "Error desconocido")
                    logger.error(f"Error obteniendo token: {error_desc}")
                    logger.error(f"Resultado completo: {result}")
                    raise ValueError(f"No se pudo obtener token: {error_desc}")

                self._access_token = result["access_token"]
                logger.info("Token obtenido exitosamente")

            except Exception as e:
                logger.error(f"Excepción obteniendo token: {str(e)}")
                raise

        return self._access_token

    def make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        binary: bool = False,
    ) -> Any:
        """
        Realiza una petición a Graph API.

        Args:
            method: Método HTTP ('GET', 'POST', etc.)
            endpoint: Endpoint de la API (sin incluir la base URL)
            params: Parámetros de query string
            json_data: Datos para enviar en el body
            binary: Si es True, retorna el contenido binario

        Returns:
            Dict o bytes: Respuesta de la API

        Raises:
            requests.RequestException: Si hay error en la petición
        """
        headers = {"Authorization": f"Bearer {self.get_token()}"}

        if not binary:
            headers["Content-Type"] = "application/json"

        url = f"{self.graph_api_endpoint}/users/{self.user_email}/{endpoint}"

        response = requests.request(
            method=method, url=url, headers=headers, params=params, json=json_data
        )
        response.raise_for_status()

        if binary:
            return response.content
        return response.json() if response.content else {}

    def test_connection(self) -> bool:
        """
        Prueba la conexión con Graph API.

        Returns:
            bool: True si la conexión es exitosa
        """
        logger.info("=== PROBANDO CONEXIÓN CON GRAPH API ===")

        # Probar obtener token y hacer una petición simple
        try:
            self.make_request("GET", "mailFolders")
            logger.info("Conexión con Graph API exitosa")
            logger.info(f"Usuario: {self.user_email}")
            return True
        except Exception as e:
            logger.error(f"Error probando conexión: {e}")
            return False
