# coding: utf-8
"""
DocuWare API Client
Cliente para interactuar con la API de DocuWare Platform Services.
"""

import re
import requests
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import ssl
import urllib3
from shared.utils.helpers import parse_bool


class DocuWareClient:
    """Cliente para interactuar con DocuWare Platform API"""
    
    def __init__(self, config: Dict, logger=None):
        """
        Inicializa el cliente con la configuración.
        
        Args:
            config: Diccionario de configuración con:
                - serverUrl: URL del servidor DocuWare
                - username: Usuario
                - password: Contraseña
                - tokenEndpoint: (opcional) Endpoint para token
                - organizationId: (opcional) ID de organización
                - platform: (default: "DocuWare/Platform")
                - verifySSL: (default: True) Verificar certificados SSL
            logger: Logger instance (opcional)
        """
        self.config = config
        self.logger = logger
        
        # Extraer configuración de DocuWare
        self.docuware = config.get('docuware', {})
        if not self.docuware:
            raise ValueError("Configuración 'docuware' es requerida")
        
        # Configuración SSL - usar parse_bool para convertir correctamente a bool
        self.verify_ssl = parse_bool(self.docuware.get('verifySSL', True))
        
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            ssl._create_default_https_context = ssl._create_unverified_context
            if self.logger:
                self.logger.warning("⚠ Verificación SSL deshabilitada (solo para desarrollo/local)")
        
        # Estado de la sesión
        self.access_token: Optional[str] = None
        self.organization_id: Optional[str] = None
        self.file_cabinet_id: Optional[str] = None
        self.search_dialog_id: Optional[str] = None
        
    def _log(self, message: str, level: str = 'info'):
        """Registra un mensaje usando el logger"""
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            elif level == 'debug':
                self.logger.debug(message)
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene los headers con el token de autenticación"""
        if not self.access_token:
            raise Exception("No hay token de acceso. Debe autenticarse primero.")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
    
    def discover_token_endpoint(self) -> str:
        """Descubre automáticamente el TokenEndpoint siguiendo el flujo de Postman"""
        self._log("=== Descubriendo TokenEndpoint ===")
        
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        # Paso 1: Obtener IdentityServiceUrl
        self._log("  Paso 1: Obteniendo IdentityServiceUrl...", 'debug')
        identity_info_url = f"{server_url}/{platform}/Home/IdentityServiceInfo"
        
        try:
            response = requests.get(identity_info_url, headers={"Accept": "application/json"}, verify=self.verify_ssl)
            response.raise_for_status()
            identity_info = response.json()
            identity_service_url = identity_info.get('IdentityServiceUrl')
            
            if not identity_service_url:
                raise Exception("No se encontró IdentityServiceUrl en la respuesta")
            
            self._log(f"  ✓ IdentityServiceUrl: {identity_service_url}", 'debug')
            
        except requests.exceptions.RequestException as e:
            error_msg = f"  ✗ Error obteniendo IdentityServiceUrl: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"    Status Code: {e.response.status_code}", 'error')
                self._log(f"    Respuesta: {e.response.text[:500]}", 'error')
            raise
        
        # Paso 2: Obtener TokenEndpoint desde OpenID Configuration
        self._log("  Paso 2: Obteniendo TokenEndpoint desde OpenID Configuration...", 'debug')
        openid_config_url = f"{identity_service_url}/.well-known/openid-configuration"
        
        try:
            response = requests.get(openid_config_url, headers={"Accept": "application/json"}, verify=self.verify_ssl)
            response.raise_for_status()
            openid_config = response.json()
            token_endpoint = openid_config.get('token_endpoint')
            
            if not token_endpoint:
                raise Exception("No se encontró token_endpoint en la configuración OpenID")
            
            self._log(f"  ✓ TokenEndpoint descubierto: {token_endpoint}", 'debug')
            return token_endpoint
            
        except requests.exceptions.RequestException as e:
            error_msg = f"  ✗ Error obteniendo OpenID Configuration: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"    Status Code: {e.response.status_code}", 'error')
                self._log(f"    Respuesta: {e.response.text[:500]}", 'error')
            raise
    
    def login(self) -> bool:
        """Autentica con DocuWare usando username y password"""
        self._log("=== Iniciando autenticación ===")
        
        # Intentar descubrir el TokenEndpoint automáticamente si no está configurado
        token_endpoint = self.docuware.get('tokenEndpoint', '').strip()
        if not token_endpoint:
            self._log("  TokenEndpoint no configurado, descubriendo automáticamente...", 'debug')
            token_endpoint = self.discover_token_endpoint()
        else:
            self._log(f"  Usando TokenEndpoint configurado: {token_endpoint}", 'debug')
        
        # Limpiar espacios en blanco de las credenciales
        username = self.docuware['username'].strip()
        password = self.docuware['password'].strip()
        
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
        
        self._log(f"  Intentando autenticar con usuario: '{username}'", 'debug')
        
        try:
            response = requests.post(token_endpoint, data=data, headers=headers, verify=self.verify_ssl)
            response.raise_for_status()
            
            try:
                token_data = response.json()
            except Exception as json_err:
                error_msg = f"✗ La respuesta no es JSON válido: {json_err}"
                self._log(error_msg, 'error')
                self._log(f"  Status Code: {response.status_code}", 'error')
                self._log(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}", 'error')
                self._log(f"  Respuesta (primeros 500 chars): {response.text[:500]}", 'error')
                raise Exception(f"Respuesta del servidor no es JSON: {json_err}")
            
            self.access_token = token_data.get('access_token')
            
            if not self.access_token:
                raise Exception("No se recibió access_token en la respuesta")
            
            self._log("✓ Autenticación exitosa")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"✗ Error en autenticación: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"  Status Code: {e.response.status_code}", 'error')
                self._log(f"  Respuesta: {e.response.text[:500]}", 'error')
            raise
    
    def get_file_cabinet_id(self, cabinet_name: str) -> Optional[str]:
        """Busca el ID del gabinete por su nombre"""
        self._log(f"=== Buscando gabinete: {cabinet_name} ===")
        
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        # Usar organization_id si está disponible
        org_id = self.organization_id or self.docuware.get('organizationId', '')
        
        url = f"{server_url}/{platform}/FileCabinets"
        if org_id:
            url += f"?OrgId={org_id}"
        
        try:
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            cabinets = data.get('FileCabinet', [])
            
            for cabinet in cabinets:
                # Buscar por Name o DisplayName
                if (cabinet.get('Name', '').strip() == cabinet_name.strip() or 
                    cabinet.get('DisplayName', '').strip() == cabinet_name.strip()):
                    cabinet_id = cabinet.get('Id')
                    self._log(f"✓ Gabinete encontrado: {cabinet_name} (ID: {cabinet_id})")
                    return cabinet_id
            
            self._log(f"✗ No se encontró el gabinete: {cabinet_name}", 'error')
            self._log(f"  Gabinetes disponibles: {[c.get('Name', 'N/A') for c in cabinets]}", 'debug')
            return None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"✗ Error al buscar gabinete: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"  Respuesta: {e.response.text}", 'error')
            raise
    
    def get_search_dialog_id(self, file_cabinet_id: str, dialog_name: Optional[str] = None) -> Optional[str]:
        """Obtiene el ID del diálogo de búsqueda del gabinete"""
        self._log("=== Buscando diálogo de búsqueda ===")
        if dialog_name:
            self._log(f"  Buscando diálogo específico: '{dialog_name}'", 'debug')
        
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        url = f"{server_url}/{platform}/FileCabinets/{file_cabinet_id}/Dialogs?DialogType=Search"
        
        try:
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            dialogs = data.get('Dialog', [])
            
            # 1. Si se pidió un nombre específico, buscarlo primero
            if dialog_name:
                for dialog in dialogs:
                    d_display = dialog.get('DisplayName', '')
                    d_name = dialog.get('Name', '')
                    
                    # Comparación flexible (case insensitive y contains)
                    if (dialog_name.lower() in d_display.lower() or 
                        dialog_name.lower() in d_name.lower()):
                        dialog_id = dialog.get('Id')
                        self._log(f"✓ Diálogo encontrado por nombre: {d_display} (ID: {dialog_id})")
                        return dialog_id
                
                self._log(f"⚠ No se encontró el diálogo con nombre '{dialog_name}', buscando alternativas...", 'warning')
            
            # 2. Buscar el diálogo por defecto
            for dialog in dialogs:
                if dialog.get('IsDefault', False):
                    dialog_id = dialog.get('Id')
                    self._log(f"✓ Diálogo de búsqueda encontrado (Default): {dialog_id}")
                    return dialog_id
            
            # 3. Si no hay default, usar el primero disponible
            if dialogs:
                dialog_id = dialogs[0].get('Id')
                self._log(f"✓ Diálogo de búsqueda encontrado (Primero disponible): {dialog_id}")
                return dialog_id
            
            self._log("✗ No se encontró ningún diálogo de búsqueda", 'error')
            return None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"✗ Error al buscar diálogo: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"  Respuesta: {e.response.text}", 'error')
            raise
    
    def _parse_docuware_date(self, date_str: str) -> Optional[datetime]:
        """Parsea el formato /Date(timestamp)/ de DocuWare a datetime"""
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
    
    def _get_field_value(self, documento: Dict, field_name: str) -> Optional[str]:
        """Extrae el valor de un campo de los metadatos del documento"""
        fields = documento.get("Fields", [])
        for field in fields:
            if field.get("FieldName") == field_name:
                item = field.get("Item")
                if item is not None:
                    return str(item)
        return None
    
    def _generate_custom_filename(self, documento: Dict, document_id: str, content_type: str = "application/pdf") -> str:
        """Genera nombre personalizado: DWSTOREDATETIME_TRDNOMBREDOCUMENTO_documentId.ext"""
        # Obtener DWSTOREDATETIME
        date_str = self._get_field_value(documento, "DWSTOREDATETIME")
        stored_dt = self._parse_docuware_date(date_str) if date_str else None
        
        if stored_dt:
            date_prefix = stored_dt.strftime("%Y%m%d_%H%M%S")
        else:
            date_prefix = "NODATE"
        
        # Obtener TRDNOMBREDOCUMENTO
        nombre_doc = self._get_field_value(documento, "TRDNOMBREDOCUMENTO")
        if not nombre_doc:
            nombre_doc = "NODOCNAME"
        
        # Determinar extensión
        ext = ".pdf"
        if "image/tiff" in content_type:
            ext = ".tiff"
        elif "image/jpeg" in content_type or "image/jpg" in content_type:
            ext = ".jpg"
        elif "image/png" in content_type:
            ext = ".png"
        
        # Combinar: DWSTOREDATETIME_TRDNOMBREDOCUMENTO_documentId.ext
        filename = f"{date_prefix}_{nombre_doc}_{document_id}{ext}"
        
        # Sanitizar nombre
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        while "__" in filename:
            filename = filename.replace("__", "_")
        return filename.strip("_")
    
    def get_download_path_for_matricula(self, base_download_path: Path, matricula: str) -> Path:
        """Obtiene la ruta de descarga para una matrícula específica (crea subcarpeta)"""
        # Sanitizar matrícula para nombre de carpeta
        safe_matricula = "".join(c if c.isalnum() or c in "._-" else "_" for c in matricula)
        while "__" in safe_matricula:
            safe_matricula = safe_matricula.replace("__", "_")
        safe_matricula = safe_matricula.strip("_")
        
        matricula_path = base_download_path / safe_matricula
        matricula_path.mkdir(parents=True, exist_ok=True)
        return matricula_path
    
    def search_documents_by_matricula(self, matricula: str, start: int = 0, count: int = 100) -> Dict:
        """Busca documentos por Matricula"""
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        url = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Query/DialogExpression"
        url += f"?DialogId={self.search_dialog_id}"
        
        # Agregar comillas si no las tiene
        matricula_value = matricula
        if not matricula.startswith('"') and not matricula.endswith('"'):
            matricula_value = f'"{matricula}"'
        
        # Construir el cuerpo de la búsqueda
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
            "Start": start,
            "Count": count
        }
        
        self._log(f"  Buscando con valor: {matricula_value} (Campo: MATRICULA)", 'debug')
        
        try:
            response = requests.post(url, json=body, headers=self._get_headers(), verify=self.verify_ssl)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"✗ Error en búsqueda: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"  Respuesta: {e.response.text}", 'error')
            raise
    
    def download_section_fallback(self, document_id: str, documento: Dict, download_path: Path) -> bool:
        """Intenta descargar el archivo obteniendo la sección directamente (Fallback)"""
        self._log(f"  ⚠ Intentando método alternativo (Secciones)...", 'warning')
        
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        # 1. Obtener lista de secciones
        url_sections = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections?docid={document_id}"
        
        try:
            response = requests.get(url_sections, headers=self._get_headers(), verify=self.verify_ssl)
            response.raise_for_status()
            
            data = response.json()
            sections = data.get('Section', [])
            
            if not sections:
                self._log("  ✗ No se encontraron secciones para este documento", 'error')
                return False
                
            # Tomamos la primera sección
            section = sections[0]
            section_id = section.get('Id')
            content_type = section.get('ContentType', 'application/pdf')
            
            self._log(f"  ✓ Sección encontrada: {section_id} ({content_type})", 'debug')
            
            # 2. Descargar datos de la sección
            url_data = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Sections/{section_id}/Data"
            
            response_data = requests.get(url_data, headers=self._get_headers(), stream=True, verify=self.verify_ssl)
            response_data.raise_for_status()
            
            # Generar nombre personalizado
            filename = self._generate_custom_filename(documento, document_id, content_type)
            file_path = download_path / filename
            
            with open(file_path, 'wb') as f:
                for chunk in response_data.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self._log(f"  ✓ Descargado (vía Sección): {filename}")
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"  ✗ Falló también el método alternativo: {e}"
            self._log(error_msg, 'error')
            if hasattr(e, 'response') and e.response is not None:
                self._log(f"    Respuesta: {e.response.text[:200]}", 'error')
            return False
    
    def download_document(self, document_id: str, documento: Dict, download_path: Path) -> bool:
        """Descarga un documento"""
        server_url = self.docuware['serverUrl']
        platform = self.docuware.get('platform', 'DocuWare/Platform')
        
        url = f"{server_url}/{platform}/FileCabinets/{self.file_cabinet_id}/Documents/{document_id}/FileDownload"
        url += "?TargetFileType=Auto&KeepAnnotations=false"
        
        try:
            response = requests.get(url, headers=self._get_headers(), stream=True, verify=self.verify_ssl)
            response.raise_for_status()
            
            # Obtener content type de la respuesta
            content_type = response.headers.get('Content-Type', 'application/pdf')
            
            # Generar nombre personalizado
            filename = self._generate_custom_filename(documento, document_id, content_type)
            file_path = download_path / filename
            
            # Guardar el archivo
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self._log(f"  ✓ Descargado: {filename}")
            return True
            
        except requests.exceptions.RequestException as e:
            # Si es error 500, intentar fallback
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 500:
                self._log(f"  ⚠ Error 500 en descarga directa. Intentando fallback...", 'warning')
                return self.download_section_fallback(document_id, documento, download_path)
                
            error_msg = f"  ✗ Error al descargar documento {document_id}: {e}"
            self._log(error_msg, 'error')
            return False
    
    def process_matricula(self, matricula: str, base_download_path: Path) -> int:
        """
        Procesa todos los documentos de una matrícula.
        Ordena por fecha (más antiguo primero) pero procesa de atrás hacia adelante.
        
        Returns:
            Número de archivos descargados
        """
        self._log(f"\n{'='*60}")
        self._log(f"Procesando Matricula: {matricula}")
        self._log(f"{'='*60}")
        
        # Obtener ruta de descarga para esta matrícula
        download_path = self.get_download_path_for_matricula(base_download_path, matricula)
        
        # Primero, obtener el total de documentos
        count = 100
        first_result = self.search_documents_by_matricula(matricula, 0, count)
        count_info = first_result.get('Count', {})
        total_count = count_info.get('Value', 0)
        
        if total_count == 0:
            self._log(f"  No se encontraron documentos para la matricula {matricula}", 'warning')
            return 0
        
        self._log(f"  Total de documentos encontrados: {total_count}")
        
        # Calcular número de páginas
        total_pages = (total_count + count - 1) // count
        self._log(f"  Total de páginas: {total_pages}", 'debug')
        
        total_downloaded = 0
        document_counter = total_count
        
        # Procesar páginas de atrás hacia adelante (última página primero)
        for page in range(total_pages - 1, -1, -1):
            start = page * count
            self._log(f"\n  --- Procesando página {page + 1}/{total_pages} (índice {start}) ---", 'debug')
            
            # Buscar documentos de esta página
            search_result = self.search_documents_by_matricula(matricula, start, count)
            items = search_result.get('Items', [])
            
            if not items:
                break
            
            # Procesar documentos de atrás hacia adelante (último primero)
            for idx in range(len(items) - 1, -1, -1):
                documento = items[idx]
                document_id = documento.get('Id')
                
                self._log(f"\n--- Documento {document_counter} (Página {page + 1}, Ítem {idx + 1}/{len(items)}) ---", 'debug')
                
                # Descargar documento
                if self.download_document(document_id, documento, download_path):
                    total_downloaded += 1
                
                document_counter -= 1
        
        self._log(f"\n✓ Matricula {matricula} procesada: {total_downloaded} archivos descargados")
        return total_downloaded

