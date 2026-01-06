"""Cliente para DocuWare API con búsqueda y descarga de documentos."""
import os
import shutil
import tempfile
import requests
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from ExpedicionCopias.core.rules_engine import ExcepcionesValidator
from shared.utils.logger import get_logger


class DocuWareClient:
    """Cliente para interactuar con DocuWare API."""

    def __init__(self, config: Dict[str, Any], rules_validator: ExcepcionesValidator) -> None:
        """
        Inicializa el cliente con configuración y validador de reglas.

        Args:
            config: Diccionario con configuración de DocuWare
            rules_validator: Instancia de ExcepcionesValidator para filtrar documentos
        """
        self.config = config.get("DocuWare", {})
        self.rules_validator = rules_validator
        self.logger = get_logger("DocuWareClient")
        self.verify_ssl = self.config.get("verifySSL", True)
        
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        
        self.access_token: Optional[str] = None
        self.organization_id: Optional[str] = None
        self.file_cabinet_id: Optional[str] = None
        self.search_dialog_id: Optional[str] = None
        self.identity_service_url: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """
        Obtiene los headers con el token de autenticación.

        Returns:
            Diccionario con headers de autenticación

        Raises:
            ValueError: Si no hay token de acceso
        """
        if not self.access_token:
            raise ValueError("No hay token de acceso. Debe autenticarse primero.")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    def _discover_token_endpoint(self) -> str:
        """
        Descubre automáticamente el TokenEndpoint.

        Returns:
            URL del token endpoint

        Raises:
            Exception: Si no se puede descubrir el endpoint
        """
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        
        identity_info_url = f"{server_url}/{platform}/Home/IdentityServiceInfo"
        
        response = requests.get(
            identity_info_url, 
            headers={"Accept": "application/json"}, 
            verify=self.verify_ssl
        )
        response.raise_for_status()
        identity_info = response.json()
        identity_service_url = identity_info.get('IdentityServiceUrl')
        
        if not identity_service_url:
            raise ValueError("No se encontró IdentityServiceUrl en la respuesta")
        
        # Guardar IdentityServiceUrl para usarlo en el cierre de sesión
        self.identity_service_url = identity_service_url
        
        openid_config_url = f"{identity_service_url}/.well-known/openid-configuration"
        response = requests.get(
            openid_config_url, 
            headers={"Accept": "application/json"}, 
            verify=self.verify_ssl
        )
        response.raise_for_status()
        openid_config = response.json()
        token_endpoint = openid_config.get('token_endpoint')
        
        if not token_endpoint:
            raise ValueError("No se encontró token_endpoint en la configuración OpenID")
        
        return token_endpoint

    def autenticar(self) -> bool:
        """
        Autentica con DocuWare usando username y password.

        Returns:
            True si la autenticación fue exitosa

        Raises:
            Exception: Si la autenticación falla
        """
        self.logger.info("[AUTH] Iniciando autenticación con DocuWare")
        
        token_endpoint = self.config.get('tokenEndpoint')
        if not token_endpoint:
            self.logger.info("[AUTH] Token endpoint no configurado, descubriendo automáticamente...")
            token_endpoint = self._discover_token_endpoint()
            self.logger.info(f"[AUTH] Token endpoint descubierto: {token_endpoint}")
        else:
            self.logger.info(f"[AUTH] Usando token endpoint configurado: {token_endpoint}")
        
        username = self.config.get('username', '').strip()
        password = self.config.get('password', '').strip()
        
        if not username:
            raise ValueError("Username de DocuWare no está configurado en la sección DocuWare")
        if not password:
            raise ValueError("Password de DocuWare no está configurado. Verifica que la variable de Rocketbot 'docuware_password' esté configurada")
        
        self.logger.info(f"[AUTH] Autenticando usuario: {username}")
        
        data = {
            "grant_type": "password",
            "scope": "docuware.platform",
            "client_id": "docuware.platform.net.client",
            "username": username,
            "password": password
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(
            token_endpoint, 
            data=data, 
            headers=headers, 
            verify=self.verify_ssl
        )
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get('access_token')
        
        if not self.access_token:
            raise ValueError("No se recibió access_token en la respuesta")
        
        self.logger.info("[AUTH] Token de acceso obtenido exitosamente")
        self.logger.info("[AUTH] Inicializando IDs de organización, file cabinet y search dialog...")
        self._inicializar_ids()
        self.logger.info(f"[AUTH] IDs inicializados - Organization: {self.organization_id or 'N/A'}, File Cabinet: {self.file_cabinet_id or 'N/A'}, Search Dialog: {self.search_dialog_id or 'N/A'}")
        self.logger.info("[AUTH] Autenticación completada exitosamente")
        
        return True

    def cerrar_sesion(self) -> None:
        """
        Cierra la sesión de DocuWare revocando el token OAuth2.
        
        Este método debe llamarse al finalizar el uso del cliente para liberar
        la licencia ocupada y evitar el error "License Used".
        
        El método maneja errores silenciosamente para no interrumpir el flujo
        principal de la aplicación.
        """
        if not self.access_token:
            self.logger.debug("[LOGOUT] No hay token de acceso activo, no se requiere cerrar sesión")
            return
        
        if not self.identity_service_url:
            self.logger.warning("[LOGOUT] No se tiene IdentityServiceUrl almacenado, intentando descubrirlo...")
            try:
                # Intentar descubrir el IdentityServiceUrl si no está guardado
                server_url = self.config['serverUrl']
                platform = self.config['platform']
                identity_info_url = f"{server_url}/{platform}/Home/IdentityServiceInfo"
                response = requests.get(
                    identity_info_url,
                    headers={"Accept": "application/json"},
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                identity_info = response.json()
                self.identity_service_url = identity_info.get('IdentityServiceUrl')
            except Exception as e:
                self.logger.warning(f"[LOGOUT] No se pudo obtener IdentityServiceUrl: {e}. El token puede quedar activo hasta su expiración.")
                # Limpiar el token de todas formas
                self.access_token = None
                return
        
        try:
            self.logger.info("[LOGOUT] Iniciando cierre de sesión de DocuWare...")
            
            # Revocar el token usando el endpoint estándar de OAuth2
            revocation_url = f"{self.identity_service_url}/connect/revocation"
            
            data = {
                "token": self.access_token,
                "token_type_hint": "access_token"
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(
                revocation_url,
                data=data,
                headers=headers,
                verify=self.verify_ssl
            )
            
            # El endpoint de revocación puede devolver 200 o 400 si el token ya fue revocado
            # Ambos casos son aceptables, así que no lanzamos excepción
            if response.status_code in [200, 400]:
                self.logger.info("[LOGOUT] Token revocado exitosamente. Sesión cerrada.")
            else:
                self.logger.warning(f"[LOGOUT] Respuesta inesperada del servidor al revocar token: {response.status_code}. El token puede quedar activo hasta su expiración.")
        
        except Exception as e:
            # No lanzamos la excepción para no interrumpir el flujo principal
            self.logger.warning(f"[LOGOUT] Error al cerrar sesión de DocuWare: {e}. El token puede quedar activo hasta su expiración.")
        finally:
            # Siempre limpiar el token local, incluso si la revocación falló
            self.access_token = None
            self.logger.debug("[LOGOUT] Token local limpiado")

    def _inicializar_ids(self) -> None:
        """Inicializa organization_id, file_cabinet_id y search_dialog_id."""
        self.logger.info("[AUTH] Inicializando organization_id...")
        self._inicializar_organization_id()
        self.logger.info("[AUTH] Inicializando file_cabinet_id...")
        self._inicializar_file_cabinet_id()
        self.logger.info("[AUTH] Inicializando search_dialog_id...")
        self._inicializar_search_dialog_id()

    def _inicializar_organization_id(self) -> None:
        """Inicializa organization_id desde la configuración."""
        org_name = self.config.get('organizationName', '')
        if not org_name:
            return
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        url = f"{server_url}/{platform}/Organizations"
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        response.raise_for_status()
        data = response.json()
        organizations = data.get('Organization', [])
        
        for org in organizations:
            if org.get('Name', '').strip() == org_name.strip():
                self.organization_id = org.get('Id')
                break

    def _inicializar_file_cabinet_id(self) -> None:
        """Inicializa file_cabinet_id desde la configuración."""
        cabinet_name = self.config.get('fileCabinetName', '')
        if not cabinet_name:
            return
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        url = f"{server_url}/{platform}/FileCabinets"
        if self.organization_id:
            url += f"?OrgId={self.organization_id}"
        
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        response.raise_for_status()
        data = response.json()
        cabinets = data.get('FileCabinet', [])
        
        for cabinet in cabinets:
            if (cabinet.get('Name', '').strip() == cabinet_name.strip() or 
                cabinet.get('DisplayName', '').strip() == cabinet_name.strip()):
                self.file_cabinet_id = cabinet.get('Id')
                break

    def _inicializar_search_dialog_id(self) -> None:
        """Inicializa search_dialog_id desde la configuración."""
        dialog_name = self.config.get('searchDialogName')
        if not self.file_cabinet_id or not dialog_name:
            return
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        url = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Dialogs?DialogType=Search"
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        response.raise_for_status()
        data = response.json()
        dialogs = data.get('Dialog', [])
        
        for dialog in dialogs:
            d_display = dialog.get('DisplayName', '')
            d_name = dialog.get('Name', '')
            if (dialog_name.lower() in d_display.lower() or 
                dialog_name.lower() in d_name.lower()):
                self.search_dialog_id = dialog.get('Id')
                return
        
        for dialog in dialogs:
            if dialog.get('IsDefault', False):
                self.search_dialog_id = dialog.get('Id')
                return
        
        if dialogs:
            self.search_dialog_id = dialogs[0].get('Id')

    def buscar_documentos(self, matricula: str) -> Dict[str, Any]:
        """
        Busca documentos por matrícula en DocuWare.

        Args:
            matricula: Matrícula a buscar

        Returns:
            Diccionario con:
            - 'documentos': Lista de documentos encontrados (filtrados por reglas de excepciones)
            - 'total_encontrados': Total de documentos encontrados en DocuWare antes del filtro
            - 'total_disponibles': Total de documentos disponibles después del filtro
        """
        self.logger.info(f"[BUSCAR] Iniciando búsqueda de documentos para matrícula: {matricula}")
        
        if not self.file_cabinet_id or not self.search_dialog_id:
            raise ValueError("No se ha inicializado file_cabinet_id o search_dialog_id")
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        
        url = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Query/DialogExpression"
        url += f"?DialogId={self.search_dialog_id}"
        
        matricula_value = matricula
        if not matricula.startswith('"') and not matricula.endswith('"'):
            matricula_value = f'"{matricula}"'
        
        body = {
            "Condition": [
                {
                    "DBName": "MATRICULA",
                    "Value": [matricula_value]
                }
            ],
            "Operation": "And",
            "SortOrder": [
                {
                    "Field": "DWSTOREDATETIME",
                    "Direction": "Asc"
                }
            ],
            "Start": 0,
            "Count": 100
        }
        
        all_documents = []
        all_items_before_filter = []
        page = 1
        max_pages = 100
        
        while page <= max_pages:
            response = requests.post(
                url, 
                json=body, 
                headers=self._get_headers(), 
                verify=self.verify_ssl
            )
            response.raise_for_status()
            result = response.json()
            
            items = result.get('Items', [])
            if not items:
                break
            
            all_items_before_filter.extend(items)
            
            for item in items:
                if self.rules_validator.debe_descargar(item):
                    all_documents.append(item)
            
            count_info = result.get('Count', {})
            if not count_info.get('HasMore', False):
                break
            
            body["Start"] = len(all_documents)
            page += 1
        
        total_encontrados = len(all_items_before_filter)
        total_despues_filtro = len(all_documents)
        filtrados = total_encontrados - total_despues_filtro
        
        # Log detallado de estadísticas
        self.logger.info(f"[BUSCAR] Matrícula {matricula}: {total_encontrados} documento(s) encontrado(s) en DocuWare")
        
        if total_encontrados == 0:
            self.logger.warning(f"[BUSCAR] Matrícula {matricula}: No se encontraron documentos en DocuWare")
        elif filtrados > 0:
            self.logger.info(f"[BUSCAR] Matrícula {matricula}: {filtrados} documento(s) excluido(s) por excepciones, {total_despues_filtro} documento(s) disponible(s) para descarga")
            if total_despues_filtro == 0:
                self.logger.info(f"[BUSCAR] Matrícula {matricula}: Todos los documentos fueron excluidos por excepciones (comportamiento esperado según reglas de negocio)")
        else:
            self.logger.info(f"[BUSCAR] Matrícula {matricula}: {total_despues_filtro} documento(s) disponible(s) para descarga (ninguno excluido)")
        
        return {
            "documentos": all_documents,
            "total_encontrados": total_encontrados,
            "total_disponibles": total_despues_filtro
        }

    def descargar_documento(self, document_id: str, documento: Dict[str, Any], ruta: str) -> str:
        """
        Descarga un documento de DocuWare.

        Args:
            document_id: ID del documento
            documento: Diccionario con metadatos del documento
            ruta: Ruta donde guardar el archivo

        Returns:
            Ruta del archivo descargado

        Raises:
            Exception: Si la descarga falla
        """
        self.logger.info(f"[DESCARGAR] Iniciando descarga de documento ID: {document_id} a ruta: {ruta}")
        
        # Verificar si es un SOBRE (documento con múltiples secciones)
        if self._es_sobre(documento):
            self.logger.info(f"[DESCARGAR] Documento {document_id}: Detectado como SOBRE, unificando todas las secciones...")
            return self._descargar_y_unificar_sobre(document_id, documento, ruta)
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        
        download_url = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Documents/{document_id}/FileDownload"
        download_url += "?TargetFileType=Auto&KeepAnnotations=false"
        
        response = requests.get(
            download_url, 
            headers=self._get_headers(), 
            stream=True, 
            verify=self.verify_ssl
        )
        
        if response.status_code == 500:
            self.logger.warning(f"[DESCARGAR] Documento {document_id}: Error 500 en descarga directa, usando método alternativo por secciones")
            return self._descargar_por_secciones(document_id, documento, ruta)
        
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'application/pdf')
        filename = self._generar_nombre_archivo(documento, document_id, content_type)
        file_path = Path(ruta) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Guardando en {file_path} (tipo: {content_type})")
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Descarga completada exitosamente - Archivo: {file_path}, Tamaño: {file_size_mb:.2f} MB")
        
        return str(file_path)

    def _descargar_por_secciones(self, document_id: str, documento: Dict[str, Any], ruta: str) -> str:
        """Método alternativo de descarga usando secciones."""
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Usando método alternativo de descarga por secciones")
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        
        url_sections = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections?docid={document_id}"
        response = requests.get(url_sections, headers=self._get_headers(), verify=self.verify_ssl)
        response.raise_for_status()
        
        data = response.json()
        sections = data.get('Section', [])
        
        if not sections:
            raise ValueError("No se encontraron secciones para este documento")
        
        section = sections[0]
        section_id = section.get('Id')
        content_type = section.get('ContentType', 'application/pdf')
        
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Sección encontrada - ID: {section_id}, Tipo: {content_type}")
        
        url_data = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections/{section_id}/Data"
        response_data = requests.get(
            url_data, 
            headers=self._get_headers(), 
            stream=True, 
            verify=self.verify_ssl
        )
        response_data.raise_for_status()
        
        filename = self._generar_nombre_archivo(documento, document_id, content_type)
        file_path = Path(ruta) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Guardando en {file_path} (método: secciones)")
        
        with open(file_path, 'wb') as f:
            for chunk in response_data.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Descarga por secciones completada - Archivo: {file_path}, Tamaño: {file_size_mb:.2f} MB")
        
        return str(file_path)

    def _generar_nombre_archivo(self, documento: Dict[str, Any], document_id: str, content_type: str) -> str:
        """Genera nombre de archivo basado en metadatos."""
        date_str = self._obtener_campo(documento, "DWSTOREDATETIME")
        stored_dt = self._parse_docuware_date(date_str) if date_str else None
        
        if stored_dt:
            date_prefix = stored_dt.strftime("%Y%m%d_%H%M%S")
        else:
            date_prefix = "NODATE"
        
        nombre_doc = self._obtener_campo(documento, "TRDNOMBREDOCUMENTO")
        if not nombre_doc:
            nombre_doc = "NODOCNAME"
        
        ext = ".pdf"
        if "image/tiff" in content_type:
            ext = ".tiff"
        elif "image/jpeg" in content_type or "image/jpg" in content_type:
            ext = ".jpg"
        elif "image/png" in content_type:
            ext = ".png"
        
        filename = f"{date_prefix}_{nombre_doc}_{document_id}{ext}"
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        while "__" in filename:
            filename = filename.replace("__", "_")
        return filename.strip("_")

    def _parse_docuware_date(self, date_str: str) -> Optional[datetime]:
        """Parsea formato /Date(timestamp)/ de DocuWare."""
        if not date_str:
            return None
        match = re.search(r'/Date\((\d+)\)/', date_str)
        if not match:
            return None
        try:
            timestamp_ms = int(match.group(1))
            timestamp_s = timestamp_ms / 1000.0
            return datetime.fromtimestamp(timestamp_s)
        except (ValueError, OSError):
            return None

    def _obtener_campo(self, documento: Dict[str, Any], nombre_campo: str) -> Optional[str]:
        """Obtiene valor de un campo de los metadatos."""
        fields = documento.get("Fields", [])
        for field in fields:
            if field.get("FieldName") == nombre_campo:
                item = field.get("Item")
                if item is not None:
                    return str(item)
        return None

    def _es_sobre(self, documento: Dict[str, Any]) -> bool:
        """
        Verifica si un documento es un SOBRE (tiene múltiples secciones).
        
        Args:
            documento: Diccionario con metadatos del documento
            
        Returns:
            True si el documento tiene más de una sección, False en caso contrario
        """
        section_count = self._obtener_campo(documento, "DWSECTIONCOUNT")
        if section_count:
            try:
                return int(section_count) > 1
            except (ValueError, TypeError):
                return False
        return False

    def _descargar_y_unificar_sobre(self, document_id: str, documento: Dict[str, Any], ruta: str) -> str:
        """
        Descarga todas las secciones de un SOBRE y las unifica en un solo PDF.
        
        Args:
            document_id: ID del documento
            documento: Diccionario con metadatos del documento
            ruta: Ruta donde guardar el archivo unificado
            
        Returns:
            Ruta del archivo PDF unificado
            
        Raises:
            Exception: Si no se pueden descargar o unificar las secciones
        """
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Detectado SOBRE - Descargando y unificando todas las secciones...")
        
        server_url = self.config['serverUrl']
        platform = self.config['platform']
        
        # Obtener todas las secciones del documento
        url_sections = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections?docid={document_id}"
        
        try:
            response = requests.get(url_sections, headers=self._get_headers(), verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            sections = data.get('Section', [])
            
            if not sections:
                raise ValueError(f"No se encontraron secciones para el SOBRE {document_id}")
            
            self.logger.info(f"[DESCARGAR] Documento {document_id}: SOBRE tiene {len(sections)} sección(es) - Descargando...")
            
            # Crear directorio temporal para las secciones
            temp_dir = tempfile.mkdtemp(prefix=f"sobre_{document_id}_")
            secciones_descargadas = []
            
            try:
                # Descargar cada sección
                for idx, section in enumerate(sections, 1):
                    section_id = section.get('Id')
                    content_type = section.get('ContentType', 'application/pdf')
                    
                    self.logger.info(f"[DESCARGAR] Documento {document_id}: Descargando sección {idx}/{len(sections)}: {section_id}")
                    
                    url_data = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections/{section_id}/Data"
                    
                    try:
                        response_data = requests.get(
                            url_data, 
                            headers=self._get_headers(), 
                            stream=True, 
                            verify=self.verify_ssl
                        )
                        response_data.raise_for_status()
                        
                        # Guardar sección temporalmente
                        temp_file = os.path.join(temp_dir, f"seccion_{idx}_{section_id}.pdf")
                        with open(temp_file, 'wb') as f:
                            for chunk in response_data.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        secciones_descargadas.append(temp_file)
                        file_size = os.path.getsize(temp_file)
                        self.logger.info(f"[DESCARGAR] Documento {document_id}: Sección {idx} descargada: {file_size} bytes")
                        
                    except requests.exceptions.RequestException as e:
                        self.logger.warning(f"[DESCARGAR] Documento {document_id}: Error descargando sección {idx}: {e}")
                        # Continuar con las demás secciones
                        continue
                
                if not secciones_descargadas:
                    raise ValueError(f"No se pudo descargar ninguna sección del SOBRE {document_id}")
                
                # Unificar todas las secciones en un solo PDF
                self.logger.info(f"[DESCARGAR] Documento {document_id}: Unificando {len(secciones_descargadas)} sección(es) en un solo PDF...")
                
                # Generar nombre del archivo final
                content_type = "application/pdf"
                filename = self._generar_nombre_archivo(documento, document_id, content_type)
                file_path = Path(ruta) / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Unificar PDFs usando pypdf
                writer = PdfWriter()
                
                for seccion_path in secciones_descargadas:
                    try:
                        reader = PdfReader(seccion_path)
                        for page in reader.pages:
                            writer.add_page(page)
                    except Exception as e:
                        self.logger.warning(f"[DESCARGAR] Documento {document_id}: Error procesando sección {seccion_path}: {e}")
                        continue
                
                # Guardar PDF unificado
                with open(file_path, 'wb') as output_file:
                    writer.write(output_file)
                
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"[DESCARGAR] Documento {document_id}: SOBRE unificado exitosamente - Archivo: {file_path}, Tamaño: {file_size_mb:.2f} MB")
                
                return str(file_path)
                
            finally:
                # Limpiar archivos temporales
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"[DESCARGAR] Documento {document_id}: Archivos temporales eliminados")
                except Exception as e:
                    self.logger.warning(f"[DESCARGAR] Documento {document_id}: Error eliminando archivos temporales: {e}")
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[DESCARGAR] Documento {document_id}: Error procesando SOBRE: {e}")
            raise
