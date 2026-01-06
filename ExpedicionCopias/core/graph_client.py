"""Cliente HTTP base para Microsoft Graph API con manejo de errores."""
import requests
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional
from html import unescape
from html.parser import HTMLParser

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

    def delete(self, endpoint: str) -> None:
        """
        Realiza una petición DELETE a Graph API.

        Args:
            endpoint: Endpoint relativo (ej: "/users/{id}/drive/items/{item_id}")

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.delete(
            url,
            headers=self._get_headers(),
            timeout=30,
        )
        response.raise_for_status()

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
        
        # Verificar si la carpeta destino ya existe y eliminarla si es necesario
        self.logger.info(f"[ONEDRIVE] Verificando si la carpeta destino ya existe: {carpeta_destino_path}")
        carpeta_eliminada = self.eliminar_carpeta_onedrive(carpeta_destino_path, usuario_id)
        if carpeta_eliminada:
            self.logger.info(f"[ONEDRIVE] Carpeta existente eliminada antes de subir nuevos documentos: {carpeta_destino_path}")
        
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

    def eliminar_carpeta_onedrive(self, ruta_carpeta: str, usuario_id: str) -> bool:
        """
        Elimina una carpeta en OneDrive por su ruta.
        
        Args:
            ruta_carpeta: Ruta de la carpeta en OneDrive
            usuario_id: ID o email del usuario propietario
        
        Returns:
            True si se eliminó exitosamente, False si no existía
        """
        try:
            # Obtener información de la carpeta para obtener su ID
            info_carpeta = self._obtener_info_carpeta(ruta_carpeta, usuario_id)
            carpeta_id = info_carpeta.get("id", "")
            
            if not carpeta_id:
                self.logger.warning(f"[ONEDRIVE] No se pudo obtener ID de la carpeta: {ruta_carpeta}")
                return False
            
            # Eliminar la carpeta usando su ID
            endpoint = f"/users/{usuario_id}/drive/items/{carpeta_id}"
            self.delete(endpoint)
            
            # Limpiar el cache de carpetas creadas
            # Remover la carpeta y todas sus subcarpetas del cache
            carpetas_a_remover = [
                carpeta for carpeta in self._carpetas_creadas 
                if carpeta == ruta_carpeta or carpeta.startswith(f"{ruta_carpeta}/")
            ]
            for carpeta in carpetas_a_remover:
                self._carpetas_creadas.discard(carpeta)
            
            self.logger.info(f"[ONEDRIVE] Carpeta eliminada exitosamente: {ruta_carpeta}")
            return True
            
        except requests.HTTPError as e:
            # Si la carpeta no existe (404), no es un error
            if e.response and e.response.status_code == 404:
                self.logger.info(f"[ONEDRIVE] La carpeta no existe, no es necesario eliminarla: {ruta_carpeta}")
                return False
            # Para otros errores HTTP, relanzar la excepción
            self.logger.error(f"[ONEDRIVE] Error eliminando carpeta {ruta_carpeta}: {e}")
            raise
        except Exception as e:
            # Para otros errores (ej: no se pudo obtener info), registrar y retornar False
            self.logger.warning(f"[ONEDRIVE] No se pudo eliminar la carpeta {ruta_carpeta}: {e}")
            return False

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
            "sendInvitation": False,  # No enviar email automático de SharePoint, usamos nuestro propio email
            "message": "Se ha compartido un archivo con usted. Puede acceder a través del enlace en este correo."
        }
        
        try:
            response = self.post(endpoint, data=invite_data)
            
            # Siempre obtener el webUrl del item directamente para asegurar que tenemos el enlace
            # La respuesta de /invite puede no incluir el webUrl en algunos casos
            info_item = self._obtener_info_carpeta_by_id(item_id, usuario_id)
            web_url = info_item.get("webUrl", "")
            
            if not web_url:
                # Si aún no tenemos webUrl, intentar obtenerlo de la respuesta de invite
                value = response.get("value", [])
                if value:
                    permiso = value[0]
                    link_info = permiso.get("link", {})
                    web_url = link_info.get("webUrl", "")
            
            if not web_url:
                raise ValueError(f"No se pudo obtener webUrl del item {item_id} después de compartir")
            
            # La respuesta contiene información sobre los permisos creados
            value = response.get("value", [])
            permission_id = ""
            if value:
                permiso = value[0]
                permission_id = permiso.get("id", "")
            
            self.logger.info(
                f"[ONEDRIVE] Archivo/carpeta compartido con {email_destinatario} "
                f"(rol: {rol}). Permiso creado sin email automático. Enlace: {web_url[:50]}..."
            )
            
            return {
                "link": web_url,
                "type": "user_invitation",
                "email": email_destinatario,
                "rol": rol,
                "permission_id": permission_id
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

    def obtener_email_enviado(
        self,
        usuario_id: str,
        asunto: str,
        minutos_ventana: int = 5,
        max_intentos: int = 3,
        espera_intento: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Consulta la carpeta "Sent Items" de Office 365 para obtener un email enviado recientemente.
        
        Busca el email por asunto y fecha/hora de envío dentro de una ventana de tiempo.
        
        Args:
            usuario_id: ID o email del usuario que envió el email
            asunto: Asunto del email a buscar
            minutos_ventana: Ventana de tiempo en minutos para buscar el email (default: 5)
            max_intentos: Número máximo de intentos si no se encuentra el email (default: 3)
            espera_intento: Segundos de espera entre intentos (default: 2)
        
        Returns:
            Diccionario con la información completa del email o None si no se encuentra
        """
        endpoint = f"/users/{usuario_id}/mailFolders/sentItems/messages"
        
        # Calcular fecha límite (últimos N minutos)
        fecha_limite = datetime.utcnow() - timedelta(minutes=minutos_ventana)
        fecha_limite_str = fecha_limite.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Intentar varias veces ya que puede haber latencia en la sincronización
        for intento in range(1, max_intentos + 1):
            try:
                params = {
                    "$filter": f"sentDateTime ge {fecha_limite_str}",
                    "$select": "id,subject,sentDateTime,from,toRecipients,body,bodyPreview",
                    "$orderby": "sentDateTime desc",
                    "$top": 10
                }
                
                response = self.get(endpoint, params=params)
                messages = response.get("value", [])
                
                # Buscar el email que coincida con el asunto
                for message in messages:
                    message_subject = message.get("subject", "")
                    if message_subject == asunto:
                        message_id = message.get("id", "")
                        if message_id:
                            # Obtener el mensaje completo con body
                            try:
                                message_endpoint = f"/users/{usuario_id}/messages/{message_id}"
                                message_params = {
                                    "$select": "id,subject,sentDateTime,from,toRecipients,body,bodyPreview,uniqueBody"
                                }
                                message_completo = self.get(message_endpoint, params=message_params)
                                
                                # Si el body está en HTML, intentar usar bodyPreview o uniqueBody que son texto plano
                                body_info = message_completo.get("body", {})
                                if body_info.get("contentType") == "HTML":
                                    # Preferir uniqueBody (texto completo) sobre bodyPreview (puede estar truncado)
                                    unique_body = message_completo.get("uniqueBody", {})
                                    if unique_body.get("contentType") == "Text" and unique_body.get("content"):
                                        message_completo["body"] = unique_body
                                    else:
                                        # Usar bodyPreview como fallback (texto plano pero puede estar truncado)
                                        body_preview = message_completo.get("bodyPreview", "")
                                        if body_preview:
                                            message_completo["body"] = {
                                                "contentType": "Text",
                                                "content": body_preview
                                            }
                                
                                self.logger.info(
                                    f"[EMAIL] Email encontrado en Sent Items (intento {intento}/{max_intentos}): "
                                    f"Asunto: {asunto[:50]}..."
                                )
                                return message_completo
                            except Exception as e:
                                self.logger.warning(
                                    f"[EMAIL] Error obteniendo body completo del mensaje: {str(e)}. "
                                    f"Usando datos básicos del mensaje."
                                )
                                return message
                        return message
                
                # Si no se encontró en este intento y hay más intentos, esperar
                if intento < max_intentos:
                    self.logger.debug(
                        f"[EMAIL] Email no encontrado en intento {intento}/{max_intentos}. "
                        f"Esperando {espera_intento}s antes del siguiente intento..."
                    )
                    time.sleep(espera_intento)
                else:
                    self.logger.warning(
                        f"[EMAIL] Email no encontrado después de {max_intentos} intentos. "
                        f"Asunto buscado: {asunto[:50]}..."
                    )
                    
            except Exception as e:
                self.logger.warning(
                    f"[EMAIL] Error consultando Sent Items (intento {intento}/{max_intentos}): {str(e)}"
                )
                if intento < max_intentos:
                    time.sleep(espera_intento)
                else:
                    self.logger.error(f"[EMAIL] No se pudo consultar el email después de {max_intentos} intentos")
        
        return None

    def formatear_email_legible(
        self,
        email_data: Dict[str, Any],
        caso: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Formatea un email obtenido de Graph API al formato legible especificado.
        
        El formato es similar a cuando se copia un email desde un cliente de email:
        - Encabezado con asunto
        - Remitente con nombre y email, fecha y hora
        - Destinatario
        - Número de PQRS (si está disponible en caso)
        - Cuerpo del email formateado
        
        Args:
            email_data: Diccionario con la información del email de Graph API
            caso: Diccionario opcional con información del caso (para incluir número PQRS)
        
        Returns:
            String con el email formateado en formato legible
        """
        # Extraer información del email
        asunto = email_data.get("subject", "")
        sent_datetime_str = email_data.get("sentDateTime", "")
        from_info = email_data.get("from", {}).get("emailAddress", {})
        to_recipients = email_data.get("toRecipients", [])
        body = email_data.get("body", {})
        body_content = body.get("content", "")
        body_type = body.get("contentType", "HTML")
        
        # Usar el body directamente si está en formato texto
        # Si está en HTML, ya debería haber sido reemplazado por uniqueBody o bodyPreview en obtener_email_enviado
        if body_type == "Text":
            cuerpo_texto = body_content
        else:
            # Si aún está en HTML (no debería pasar, pero por seguridad), convertir
            cuerpo_texto = self._html_a_texto(body_content) if body_content else ""
        
        # Formatear remitente
        from_name = from_info.get("name", "")
        from_email = from_info.get("address", "")
        remitente = f"{from_name} <{from_email}>" if from_name else from_email
        
        # Formatear fecha y hora
        fecha_hora = self._formatear_fecha_hora_email(sent_datetime_str)
        
        # Formatear destinatarios
        destinatarios = []
        for recipient in to_recipients:
            recipient_info = recipient.get("emailAddress", {})
            recipient_name = recipient_info.get("name", "")
            recipient_email = recipient_info.get("address", "")
            if recipient_name:
                destinatarios.append(f"{recipient_name} <{recipient_email}>")
            else:
                destinatarios.append(recipient_email)
        destinatarios_str = ", ".join(destinatarios)
        
        # Extraer número de PQRS del caso si está disponible
        numero_pqrs = ""
        if caso:
            numero_pqrs = caso.get("sp_name", "") or caso.get("sp_ticketnumber", "")
        
        # Construir el formato legible
        lineas = []
        
        # Encabezado con asunto
        lineas.append(asunto)
        lineas.append("")
        
        # Remitente y fecha
        lineas.append(f"{remitente}\t{fecha_hora}")
        
        # Destinatario
        if destinatarios_str:
            lineas.append(f"Para: {destinatarios_str}")
        
        # Número de PQRS si está disponible
        if numero_pqrs:
            lineas.append(numero_pqrs)
            lineas.append("")
        
        # Cuerpo del email
        lineas.append("")
        lineas.append(cuerpo_texto.strip())
        
        return "\n".join(lineas)

    def _formatear_fecha_hora_email(self, fecha_iso: str) -> str:
        """
        Formatea una fecha ISO a formato legible en español.
        
        Args:
            fecha_iso: Fecha en formato ISO (ej: "2026-01-05T22:18:00Z")
        
        Returns:
            Fecha formateada (ej: "5 de enero de 2026 a las 22:18")
        """
        if not fecha_iso:
            return ""
        
        try:
            # Parsear fecha ISO (puede tener o no Z al final)
            if fecha_iso.endswith("Z"):
                fecha_iso = fecha_iso[:-1] + "+00:00"
            
            # Intentar diferentes formatos
            formatos = [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f"
            ]
            
            fecha_obj = None
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(fecha_iso, formato)
                    break
                except ValueError:
                    continue
            
            if not fecha_obj:
                # Fallback: intentar parsear con dateutil si está disponible
                try:
                    from dateutil import parser
                    fecha_obj = parser.parse(fecha_iso)
                except ImportError:
                    self.logger.warning(f"[EMAIL] No se pudo parsear la fecha: {fecha_iso}")
                    return fecha_iso
            
            # Nombres de meses en español
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            
            dia = fecha_obj.day
            mes = meses[fecha_obj.month - 1]
            año = fecha_obj.year
            hora = fecha_obj.hour
            minuto = fecha_obj.minute
            
            return f"{dia} de {mes} de {año} a las {hora:02d}:{minuto:02d}"
            
        except Exception as e:
            self.logger.warning(f"[EMAIL] Error formateando fecha {fecha_iso}: {str(e)}")
            return fecha_iso

    def _html_a_texto(self, html: str) -> str:
        """
        Convierte HTML a texto plano preservando saltos de línea y estructura básica.
        
        Args:
            html: String con contenido HTML
        
        Returns:
            String con texto plano
        """
        if not html:
            return ""
        
        # Crear un parser HTML simple
        class HTMLToTextParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = False
            
            def handle_data(self, data):
                if not self.skip:
                    self.text.append(data)
            
            def handle_starttag(self, tag, attrs):
                if tag in ['br', 'p', 'div', 'li']:
                    self.text.append('\n')
                elif tag in ['script', 'style']:
                    self.skip = True
            
            def handle_endtag(self, tag):
                if tag in ['p', 'div', 'li', 'tr']:
                    self.text.append('\n')
                elif tag in ['script', 'style']:
                    self.skip = False
            
            def get_text(self):
                return ''.join(self.text)
        
        try:
            # Decodificar entidades HTML
            html_decodificado = unescape(html)
            
            # Remover scripts y estilos
            html_decodificado = re.sub(r'<script[^>]*>.*?</script>', '', html_decodificado, flags=re.DOTALL | re.IGNORECASE)
            html_decodificado = re.sub(r'<style[^>]*>.*?</style>', '', html_decodificado, flags=re.DOTALL | re.IGNORECASE)
            
            # Convertir <br> y <br/> a saltos de línea
            html_decodificado = re.sub(r'<br\s*/?>', '\n', html_decodificado, flags=re.IGNORECASE)
            
            # Convertir <p> y </p> a saltos de línea
            html_decodificado = re.sub(r'</?p[^>]*>', '\n', html_decodificado, flags=re.IGNORECASE)
            
            # Convertir <div> y </div> a saltos de línea
            html_decodificado = re.sub(r'</?div[^>]*>', '\n', html_decodificado, flags=re.IGNORECASE)
            
            # Parsear con HTMLParser
            parser = HTMLToTextParser()
            parser.feed(html_decodificado)
            texto = parser.get_text()
            
            # Limpiar espacios en blanco múltiples y saltos de línea
            texto = re.sub(r'[ \t]+', ' ', texto)
            texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)
            
            return texto.strip()
            
        except Exception as e:
            self.logger.warning(f"[EMAIL] Error convirtiendo HTML a texto: {str(e)}")
            # Fallback: remover tags HTML básicos
            texto_simple = re.sub(r'<[^>]+>', '', html)
            return unescape(texto_simple).strip()
