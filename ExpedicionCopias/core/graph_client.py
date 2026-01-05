"""Cliente HTTP base para Microsoft Graph API con manejo de errores."""
import requests
from pathlib import Path
from typing import Any, List, Dict, Optional

from ExpedicionCopias.core.auth import AzureAuthenticator


class GraphClient:
    """Cliente HTTP para realizar peticiones a Microsoft Graph API."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, authenticator: AzureAuthenticator) -> None:
        """
        Inicializa el cliente con un autenticador.

        Args:
            authenticator: Instancia de AzureAuthenticator
        """
        self.authenticator = authenticator
        self._token: str | None = None

    def _get_token(self) -> str:
        """
        Obtiene un token válido (reutiliza si está en caché).

        Returns:
            Token de acceso
        """
        if self._token is None:
            self._token = self.authenticator.get_token()
        return self._token

    def _get_headers(self) -> dict[str, str]:
        """
        Genera los headers necesarios para las peticiones.

        Returns:
            Diccionario con headers de autorización y contenido
        """
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Realiza una petición GET a Graph API.

        Args:
            endpoint: Endpoint relativo (ej: "/users")
            params: Parámetros de consulta opcionales

        Returns:
            Respuesta JSON como diccionario

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def post(
        self, endpoint: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Realiza una petición POST a Graph API.

        Args:
            endpoint: Endpoint relativo (ej: "/users")
            data: Datos JSON a enviar

        Returns:
            Respuesta JSON como diccionario (o {} si no hay contenido)

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.post(
            url,
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )
        
        if not response.ok:
            error_detail = ""
            try:
                error_json = response.json()
                error_detail = f" - {error_json.get('error', {}).get('message', '')}"
            except ValueError:
                error_detail = f" - {response.text[:200]}"
            raise requests.HTTPError(
                f"{response.status_code} Client Error: {response.reason} for url: {url}{error_detail}",
                response=response
            )
        
        if response.status_code == 202 or not response.content:
            return {}
        
        try:
            return response.json()
        except ValueError:
            return {}

    def put(
        self,
        endpoint: str,
        data: bytes | None = None,
        content_type: str = "application/json",
    ) -> dict[str, Any] | None:
        """
        Realiza una petición PUT a Graph API (útil para subir archivos).

        Args:
            endpoint: Endpoint relativo
            data: Datos binarios a enviar
            content_type: Tipo de contenido del request

        Returns:
            Respuesta JSON como diccionario o None si no hay contenido

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()
        headers["Content-Type"] = content_type

        response = requests.put(
            url,
            headers=headers,
            data=data,
            timeout=60,
        )
        response.raise_for_status()

        if response.content:
            return response.json()
        return None

    def enviar_email(
        self,
        usuario_id: str,
        asunto: str,
        cuerpo: str,
        destinatarios: List[str],
        adjuntos: List[str] | None = None,
        contenido_html: bool = True,
    ) -> Dict[str, Any]:
        """
        Envía un email usando Microsoft Graph API.

        Args:
            usuario_id: ID o email del usuario que envía
            asunto: Asunto del email
            cuerpo: Cuerpo del email
            destinatarios: Lista de direcciones de email destinatarios
            adjuntos: Lista opcional de rutas a archivos para adjuntar
            contenido_html: Si True, el cuerpo es HTML; si False, es texto plano

        Returns:
            Respuesta del envío

        Raises:
            requests.HTTPError: Si el envío falla
        """
        to_recipients = [{"emailAddress": {"address": email}} for email in destinatarios]
        
        message = {
            "subject": asunto,
            "body": {
                "contentType": "HTML" if contenido_html else "Text",
                "content": cuerpo
            },
            "toRecipients": to_recipients
        }
        
        if adjuntos:
            attachments = []
            for adjunto_path in adjuntos:
                with open(adjunto_path, "rb") as f:
                    import base64
                    content_bytes = f.read()
                    content_base64 = base64.b64encode(content_bytes).decode('utf-8')
                    
                    attachments.append({
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": Path(adjunto_path).name,
                        "contentType": "application/pdf",
                        "contentBytes": content_base64
                    })
            
            message["attachments"] = attachments
        
        endpoint = f"/users/{usuario_id}/sendMail"
        payload = {
            "message": message,
            "saveToSentItems": "true"
        }
        
        return self.post(endpoint, data=payload)

    def subir_a_onedrive(
        self, ruta_local: str, carpeta_destino: str, usuario_id: str
    ) -> Dict[str, Any]:
        """
        Sube un archivo a OneDrive.

        Args:
            ruta_local: Ruta del archivo local a subir
            carpeta_destino: Ruta de la carpeta en OneDrive (ej: "/Carpeta/Subcarpeta")
            usuario_id: ID o email del usuario propietario

        Returns:
            Información del archivo subido

        Raises:
            requests.HTTPError: Si la subida falla
        """
        ruta_local_path = Path(ruta_local)
        nombre_archivo = ruta_local_path.name
        
        with open(ruta_local_path, "rb") as f:
            contenido = f.read()
        
        endpoint = f"/users/{usuario_id}/drive/root:{carpeta_destino}/{nombre_archivo}:/content"
        
        return self.put(endpoint, data=contenido, content_type="application/pdf") or {}

    def subir_carpeta_completa(
        self, ruta_carpeta_local: str, carpeta_destino: str, usuario_id: str
    ) -> Dict[str, Any]:
        """
        Sube una carpeta completa a OneDrive (recursivo).

        Args:
            ruta_carpeta_local: Ruta de la carpeta local
            carpeta_destino: Ruta de la carpeta destino en OneDrive
            usuario_id: ID o email del usuario propietario

        Returns:
            Información de la carpeta creada (con id)

        Raises:
            requests.HTTPError: Si la subida falla
        """
        carpeta_local = Path(ruta_carpeta_local)
        if not carpeta_local.is_dir():
            raise ValueError(f"{ruta_carpeta_local} no es una carpeta")
        
        carpeta_destino_clean = carpeta_destino.rstrip("/")
        carpeta_destino_path = f"{carpeta_destino_clean}/{carpeta_local.name}"
        
        self._crear_carpeta_onedrive(carpeta_destino_path, usuario_id)
        
        for item in carpeta_local.rglob("*"):
            if item.is_file():
                ruta_relativa = item.relative_to(carpeta_local)
                carpeta_padre = str(ruta_relativa.parent).replace("\\", "/")
                carpeta_completa = f"{carpeta_destino_path}/{carpeta_padre}" if carpeta_padre != "." else carpeta_destino_path
                
                if carpeta_padre != ".":
                    self._crear_carpeta_onedrive(carpeta_completa, usuario_id)
                
                self.subir_a_onedrive(str(item), carpeta_completa, usuario_id)
        
        info_carpeta = self._obtener_info_carpeta(carpeta_destino_path, usuario_id)
        return info_carpeta

    def _crear_carpeta_onedrive(self, ruta_carpeta: str, usuario_id: str) -> Dict[str, Any]:
        """Crea una carpeta en OneDrive si no existe."""
        partes = ruta_carpeta.strip("/").split("/")
        carpeta_actual = ""
        
        for parte in partes:
            carpeta_siguiente = f"{carpeta_actual}/{parte}" if carpeta_actual else f"/{parte}"
            
            try:
                endpoint = f"/users/{usuario_id}/drive/root:{carpeta_siguiente}"
                self.get(endpoint)
            except requests.HTTPError:
                if carpeta_actual:
                    # Subcarpeta: usar formato root:{ruta}/children
                    carpeta_padre = carpeta_actual.lstrip("/")
                    endpoint = f"/users/{usuario_id}/drive/root:/{carpeta_padre}/children"
                else:
                    # Raíz: usar formato root/children
                    endpoint = f"/users/{usuario_id}/drive/root/children"
                
                self.post(endpoint, data={
                    "name": parte,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                })
            
            carpeta_actual = carpeta_siguiente
        
        return {}

    def _obtener_info_carpeta(self, ruta_carpeta: str, usuario_id: str) -> Dict[str, Any]:
        """Obtiene información de una carpeta en OneDrive."""
        endpoint = f"/users/{usuario_id}/drive/root:{ruta_carpeta}"
        return self.get(endpoint)

    def compartir_carpeta(self, item_id: str, usuario_id: str, tipo_link: str = "view") -> Dict[str, Any]:
        """
        Comparte una carpeta/archivo en OneDrive y obtiene el enlace.

        Args:
            item_id: ID del item (carpeta o archivo)
            usuario_id: ID o email del usuario propietario
            tipo_link: Tipo de enlace ('view' o 'edit')

        Returns:
            Información del enlace compartido

        Raises:
            requests.HTTPError: Si la operación falla
        """
        endpoint = f"/users/{usuario_id}/drive/items/{item_id}/createLink"
        link_data = {
            "type": tipo_link,
            "scope": "organization",
        }
        
        response = self.post(endpoint, data=link_data)
        link_info = response.get("link", {}) if isinstance(response, dict) else {}
        
        return {
            "link": link_info.get("webUrl"),
            "type": "organization_link",
            "scope": link_info.get("scope", "organization"),
        }

    def obtener_enlace_compartido(self, item_id: str, usuario_id: str) -> str:
        """
        Obtiene el enlace compartido de un item (si ya está compartido).

        Args:
            item_id: ID del item
            usuario_id: ID o email del usuario propietario

        Returns:
            URL del enlace compartido

        Raises:
            requests.HTTPError: Si la operación falla
        """
        endpoint = f"/users/{usuario_id}/drive/items/{item_id}/permissions"
        response = self.get(endpoint)
        
        permissions = response.get("value", [])
        for perm in permissions:
            link = perm.get("link", {})
            if link and link.get("webUrl"):
                return link.get("webUrl")
        
        raise ValueError("No se encontró enlace compartido para el item")
