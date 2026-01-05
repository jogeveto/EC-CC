"""Cliente HTTP base para Microsoft Graph API con manejo de errores."""
import requests
import time
from pathlib import Path
from typing import Any, List, Dict, Optional

from ExpedicionCopias.core.auth import AzureAuthenticator
from shared.utils.logger import get_logger


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
        self.logger = get_logger("GraphClient")
        self._carpetas_creadas: set[str] = set()  # Cache de carpetas ya creadas

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

        # Timeout dinámico basado en tamaño: 1 min por MB, mínimo 60s, máximo 300s
        if data:
            tamaño_mb = len(data) / (1024 * 1024)
            timeout = max(60, min(300, int(tamaño_mb * 60)))
        else:
            timeout = 60

        response = requests.put(
            url,
            headers=headers,
            data=data,
            timeout=timeout,
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
        
        # Validación: verificar que el archivo existe
        if not ruta_local_path.exists():
            raise FileNotFoundError(f"El archivo no existe: {ruta_local}")
        
        if not ruta_local_path.is_file():
            raise ValueError(f"La ruta no es un archivo: {ruta_local}")
        
        nombre_archivo = ruta_local_path.name
        tamaño_archivo = ruta_local_path.stat().st_size
        tamaño_mb = tamaño_archivo / (1024 * 1024)
        
        # Validación: verificar que el archivo no está vacío
        if tamaño_archivo == 0:
            raise ValueError(f"El archivo está vacío: {ruta_local}")
        
        inicio_tiempo = time.time()
        self.logger.info(f"[ONEDRIVE] Subiendo archivo: {nombre_archivo} ({tamaño_mb:.2f} MB) a {carpeta_destino}")
        
        try:
            with open(ruta_local_path, "rb") as f:
                contenido = f.read()
            
            endpoint = f"/users/{usuario_id}/drive/root:{carpeta_destino}/{nombre_archivo}:/content"
            
            resultado = self.put(endpoint, data=contenido, content_type="application/pdf") or {}
            
            tiempo_transcurrido = time.time() - inicio_tiempo
            self.logger.info(f"[ONEDRIVE] Archivo {nombre_archivo} subido exitosamente en {tiempo_transcurrido:.2f}s")
            
            return resultado
        except Exception as e:
            tiempo_transcurrido = time.time() - inicio_tiempo
            self.logger.error(f"[ONEDRIVE] Error subiendo archivo {nombre_archivo} después de {tiempo_transcurrido:.2f}s: {e}")
            raise

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
        
        # Obtener lista de archivos antes de empezar
        archivos = [item for item in carpeta_local.rglob("*") if item.is_file()]
        total_archivos = len(archivos)
        
        # Calcular tamaño total
        tamaño_total = sum(f.stat().st_size for f in archivos)
        tamaño_total_mb = tamaño_total / (1024 * 1024)
        
        self.logger.info(f"[ONEDRIVE] Iniciando subida de carpeta: {ruta_carpeta_local} -> {carpeta_destino_path}")
        self.logger.info(f"[ONEDRIVE] Total de archivos a subir: {total_archivos}")
        self.logger.info(f"[ONEDRIVE] Tamaño total: {tamaño_total_mb:.2f} MB")
        
        # Crear carpeta destino principal
        self._crear_carpeta_onedrive(carpeta_destino_path, usuario_id)
        
        # Contadores para resumen
        archivos_exitosos = 0
        archivos_fallidos = 0
        archivos_fallidos_detalle = []
        
        inicio_tiempo_total = time.time()
        
        # Subir cada archivo
        for idx, item in enumerate(archivos, 1):
            try:
                ruta_relativa = item.relative_to(carpeta_local)
                carpeta_padre = str(ruta_relativa.parent).replace("\\", "/")
                carpeta_completa = f"{carpeta_destino_path}/{carpeta_padre}" if carpeta_padre != "." else carpeta_destino_path
                
                # Crear subcarpetas si es necesario
                if carpeta_padre != ".":
                    self._crear_carpeta_onedrive(carpeta_completa, usuario_id)
                
                self.logger.info(f"[ONEDRIVE] Subiendo archivo {idx}/{total_archivos}: {item.name}")
                self.subir_a_onedrive(str(item), carpeta_completa, usuario_id)
                archivos_exitosos += 1
                
            except Exception as e:
                archivos_fallidos += 1
                nombre_archivo = item.name
                archivos_fallidos_detalle.append(f"{nombre_archivo}: {str(e)}")
                self.logger.error(f"[ONEDRIVE] Error subiendo archivo {idx}/{total_archivos} ({nombre_archivo}): {e}")
                # Continuar con el siguiente archivo en lugar de detener todo el proceso
        
        tiempo_total = time.time() - inicio_tiempo_total
        
        # Resumen final
        self.logger.info(f"[ONEDRIVE] Resumen de subida: {total_archivos} archivos procesados - {archivos_exitosos} exitosos, {archivos_fallidos} fallidos")
        self.logger.info(f"[ONEDRIVE] Tiempo total de subida: {tiempo_total:.2f}s")
        
        if archivos_fallidos > 0:
            self.logger.warning(f"[ONEDRIVE] Archivos fallidos: {', '.join(archivos_fallidos_detalle)}")
        
        # Si todos los archivos fallaron, lanzar excepción
        if archivos_exitosos == 0 and total_archivos > 0:
            raise RuntimeError(f"Todos los archivos fallaron al subir. Errores: {', '.join(archivos_fallidos_detalle)}")
        
        info_carpeta = self._obtener_info_carpeta(carpeta_destino_path, usuario_id)
        return info_carpeta

    def _crear_carpeta_onedrive(self, ruta_carpeta: str, usuario_id: str) -> Dict[str, Any]:
        """Crea una carpeta en OneDrive si no existe."""
        # Verificar cache primero
        if ruta_carpeta in self._carpetas_creadas:
            return {}
        
        partes = ruta_carpeta.strip("/").split("/")
        carpeta_actual = ""
        
        for parte in partes:
            carpeta_siguiente = f"{carpeta_actual}/{parte}" if carpeta_actual else f"/{parte}"
            
            # Verificar si la carpeta ya existe en cache
            if carpeta_siguiente in self._carpetas_creadas:
                carpeta_actual = carpeta_siguiente
                continue
            
            try:
                endpoint = f"/users/{usuario_id}/drive/root:{carpeta_siguiente}"
                self.get(endpoint)
                # Carpeta existe, agregar a cache
                self._carpetas_creadas.add(carpeta_siguiente)
            except requests.HTTPError:
                # Carpeta no existe, crearla
                if carpeta_actual:
                    # Subcarpeta: usar formato root:{ruta}:/children (dos puntos antes de children)
                    carpeta_padre = carpeta_actual.lstrip("/")
                    endpoint = f"/users/{usuario_id}/drive/root:/{carpeta_padre}:/children"
                else:
                    # Raíz: usar formato root/children
                    endpoint = f"/users/{usuario_id}/drive/root/children"
                
                self.post(endpoint, data={
                    "name": parte,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                })
                self.logger.info(f"[ONEDRIVE] Carpeta creada: {carpeta_siguiente}")
                # Agregar a cache
                self._carpetas_creadas.add(carpeta_siguiente)
            
            carpeta_actual = carpeta_siguiente
        
        return {}

    def _obtener_info_carpeta(self, ruta_carpeta: str, usuario_id: str) -> Dict[str, Any]:
        """Obtiene información de una carpeta en OneDrive."""
        endpoint = f"/users/{usuario_id}/drive/root:{ruta_carpeta}"
        return self.get(endpoint)

    def compartir_carpeta(self, item_id: str, usuario_id: str, tipo_link: str = "view") -> Dict[str, Any]:
        """
        Comparte una carpeta/archivo en OneDrive y obtiene el enlace.
        Intenta primero con scope "anonymous" para lectura pública.
        Si el tenant tiene deshabilitado el compartir anónimo, usa "organization" como fallback.

        Args:
            item_id: ID del item (carpeta o archivo)
            usuario_id: ID o email del usuario propietario
            tipo_link: Tipo de enlace ('view' o 'edit')

        Returns:
            Información del enlace compartido

        Raises:
            requests.HTTPError: Si todas las operaciones fallan
        """
        endpoint = f"/users/{usuario_id}/drive/items/{item_id}/createLink"
        
        # Intentar primero con scope "anonymous" (lectura pública)
        link_data = {
            "type": tipo_link,
            "scope": "anonymous",
        }
        
        try:
            response = self.post(endpoint, data=link_data)
            link_info = response.get("link", {}) if isinstance(response, dict) else {}
            
            self.logger.info(f"[ONEDRIVE] Carpeta compartida con acceso público (anonymous)")
            return {
                "link": link_info.get("webUrl"),
                "type": "anonymous_link",
                "scope": link_info.get("scope", "anonymous"),
            }
        except requests.HTTPError as e:
            # Si el compartir anónimo está deshabilitado (403), usar "organization" como fallback
            if e.response and e.response.status_code == 403:
                error_msg = str(e)
                if "sharing has been disabled" in error_msg.lower() or "forbidden" in error_msg.lower():
                    self.logger.warning(
                        f"[ONEDRIVE] El compartir anónimo está deshabilitado en el tenant. "
                        f"Usando scope 'organization' como fallback. "
                        f"NOTA: El link solo será accesible para usuarios de la organización."
                    )
                    
                    # Usar "organization" como fallback
                    link_data_fallback = {
                        "type": tipo_link,
                        "scope": "organization",
                    }
                    
                    response = self.post(endpoint, data=link_data_fallback)
                    link_info = response.get("link", {}) if isinstance(response, dict) else {}
                    
                    return {
                        "link": link_info.get("webUrl"),
                        "type": "organization_link",
                        "scope": link_info.get("scope", "organization"),
                    }
            
            # Si es otro error, relanzarlo
            raise

    def compartir_con_usuario(
        self, item_id: str, usuario_id: str, email_destinatario: str, rol: str = "read"
    ) -> Dict[str, Any]:
        """
        Comparte un archivo/carpeta en OneDrive con un usuario específico por correo electrónico.
        Envía una invitación automática al usuario con acceso al archivo/carpeta.

        Args:
            item_id: ID del item (carpeta o archivo) en OneDrive
            usuario_id: ID o email del usuario propietario del archivo
            email_destinatario: Email del destinatario con quien compartir
            rol: Rol de acceso ("read" para lectura, "write" para edición)

        Returns:
            Diccionario con información del permiso creado, incluyendo el enlace de acceso

        Raises:
            requests.HTTPError: Si la operación falla
        """
        endpoint = f"/users/{usuario_id}/drive/items/{item_id}/invite"
        
        # Mapear rol a roles de Microsoft Graph
        roles = []
        if rol == "write":
            roles = ["write"]
        else:
            roles = ["read"]
        
        invite_data = {
            "recipients": [
                {
                    "email": email_destinatario
                }
            ],
            "roles": roles,
            "requireSignIn": True,
            "sendInvitation": True,
            "message": "Se ha compartido un archivo con usted. Puede acceder a través del enlace en este correo."
        }
        
        try:
            response = self.post(endpoint, data=invite_data)
            
            # La respuesta contiene información sobre los permisos creados
            value = response.get("value", [])
            if value:
                permiso = value[0]
                link_info = permiso.get("link", {})
                web_url = link_info.get("webUrl", "")
                
                self.logger.info(
                    f"[ONEDRIVE] Archivo/carpeta compartido con {email_destinatario} "
                    f"(rol: {rol}). Invitación enviada por correo."
                )
                
                return {
                    "link": web_url,
                    "type": "user_invitation",
                    "email": email_destinatario,
                    "rol": rol,
                    "permission_id": permiso.get("id", "")
                }
            else:
                # Si no hay value, intentar obtener webUrl del item directamente
                info_item = self._obtener_info_carpeta_by_id(item_id, usuario_id)
                web_url = info_item.get("webUrl", "")
                
                self.logger.warning(
                    f"[ONEDRIVE] Compartido con {email_destinatario} pero no se obtuvo link en respuesta. "
                    f"Usando webUrl del item."
                )
                
                return {
                    "link": web_url,
                    "type": "user_invitation",
                    "email": email_destinatario,
                    "rol": rol
                }
                
        except requests.HTTPError as e:
            error_msg = str(e)
            self.logger.error(
                f"[ONEDRIVE] Error compartiendo con {email_destinatario}: {error_msg}"
            )
            raise

    def _obtener_info_carpeta_by_id(self, item_id: str, usuario_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un item en OneDrive por su ID.

        Args:
            item_id: ID del item
            usuario_id: ID o email del usuario propietario

        Returns:
            Información del item
        """
        endpoint = f"/users/{usuario_id}/drive/items/{item_id}"
        return self.get(endpoint)

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
