"""Cliente para DocuWare API con búsqueda y descarga de documentos."""
import os
import shutil
import tempfile
import requests
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# Intentar importar PyMuPDF para extraer attachments de PDFs
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from ExpedicionCopias.core.rules_engine import ExcepcionesValidator
from shared.utils.logger import get_logger
from ExpedicionCopias.core.constants import (
    CAMPO_DOCUWARE_MATRICULA, CAMPO_DOCUWARE_DWSTOREDATETIME, ORDEN_ASC,
    SCOPE_DOCUWARE_PLATFORM, CLIENT_ID_DOCUWARE,
    MSG_DOCUWARE_USERNAME_NO_CONFIG, MSG_DOCUWARE_PASSWORD_NO_CONFIG,
    MSG_PYMUPDF_NO_INSTALADO, MSG_PYMUPDF_INSTALAR, MSG_PDF_SIN_EMBEBIDOS,
    MSG_NO_PDF_VALIDO, VALOR_DEFECTO_NODATE, VALOR_DEFECTO_NODOCNAME,
    EXTENSION_PDF, EXTENSION_TIFF, EXTENSION_JPG, EXTENSION_PNG
)


class DocuWareClient:
    """Cliente para interactuar con DocuWare API."""

    def __init__(self, config: Dict[str, Any], rules_validator: ExcepcionesValidator, incluir_caratula: bool = False) -> None:
        """
        Inicializa el cliente con configuración y validador de reglas.

        Args:
            config: Diccionario con configuración de DocuWare
            rules_validator: Instancia de ExcepcionesValidator para filtrar documentos
            incluir_caratula: Si True, incluye la carátula (PDF original) al mergear attachments de sobres
        """
        self.config = config.get("DocuWare", {})
        self.rules_validator = rules_validator
        self.incluir_caratula = incluir_caratula
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

    def _reintentar_con_backoff(self, func, *args, **kwargs):
        """
        Reintenta una función con backoff exponencial en caso de errores de conexión.
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            **kwargs: Argumentos con nombre para la función
        
        Returns:
            Resultado de la función si es exitosa
        
        Raises:
            La última excepción si todos los reintentos fallan
        """
        max_reintentos = 3
        delays = [1, 2, 4]  # segundos
        
        for intento in range(max_reintentos):
            try:
                return func(*args, **kwargs)
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.ChunkedEncodingError,
                    ConnectionError) as e:
                if intento == max_reintentos - 1:
                    # Último intento falló, relanzar la excepción
                    raise
                delay = delays[intento]
                self.logger.warning(
                    f"[BUSCAR] Error de conexión (intento {intento + 1}/{max_reintentos}): {e}. "
                    f"Reintentando en {delay}s..."
                )
                time.sleep(delay)
        
        # Este punto no debería alcanzarse, pero por seguridad
        raise ConnectionError("Todos los reintentos fallaron")

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
            raise ValueError(MSG_DOCUWARE_USERNAME_NO_CONFIG)
        if not password:
            raise ValueError(MSG_DOCUWARE_PASSWORD_NO_CONFIG)
        
        self.logger.info(f"[AUTH] Autenticando usuario: {username}")
        
        data = {
            "grant_type": "password",
            "scope": SCOPE_DOCUWARE_PLATFORM,
            "client_id": CLIENT_ID_DOCUWARE,
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
                    "DBName": CAMPO_DOCUWARE_MATRICULA,
                    "Value": [matricula_value]
                }
            ],
            "Operation": "And",
            "SortOrder": [
                {
                    "Field": CAMPO_DOCUWARE_DWSTOREDATETIME,
                    "Direction": ORDEN_ASC
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
            def hacer_request():
                return requests.post(
                    url, 
                    json=body, 
                    headers=self._get_headers(), 
                    verify=self.verify_ssl
                )
            
            response = self._reintentar_con_backoff(hacer_request)
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
        Si el documento descargado tiene attachments embebidos (SOBRE), los extrae y mergea.

        Args:
            document_id: ID del documento
            documento: Diccionario con metadatos del documento
            ruta: Ruta donde guardar el archivo

        Returns:
            Ruta del archivo descargado (o mergeado si era un SOBRE)

        Raises:
            Exception: Si la descarga falla
        """
        self.logger.info(f"[DESCARGAR] Iniciando descarga de documento ID: {document_id} a ruta: {ruta}")
        
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
        self.logger.info(f"[DESCARGAR] Documento {document_id}: Descarga completada - Archivo: {file_path}, Tamaño: {file_size_mb:.2f} MB")
        
        # Verificar si el PDF descargado tiene attachments embebidos (SOBRE)
        if self._es_sobre(file_path):
            self.logger.info(f"[DESCARGAR] Documento {document_id}: Detectado SOBRE con attachments embebidos - Extrayendo y mergeando...")
            
            # Crear ruta temporal para el PDF mergeado
            temp_merged_path = file_path.parent / f"{file_path.stem}_merged{file_path.suffix}"
            
            try:
                # Extraer y mergear attachments
                merged_path = self._extraer_y_mergear_adjuntos_sobre(
                    pdf_path=file_path,
                    output_path=temp_merged_path,
                    incluir_caratula=self.incluir_caratula
                )
                
                # Reemplazar el archivo original con el mergeado
                file_path.unlink()  # Eliminar original
                temp_merged_path.rename(file_path)  # Renombrar mergeado al nombre original
                
                file_size_mb_final = file_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"[DESCARGAR] Documento {document_id}: SOBRE procesado exitosamente - Archivo final: {file_path}, Tamaño: {file_size_mb_final:.2f} MB")
                
            except Exception as e:
                self.logger.error(f"[DESCARGAR] Documento {document_id}: Error procesando SOBRE: {e}")
                # Si falla el procesamiento del sobre, mantener el archivo original
                if temp_merged_path.exists():
                    temp_merged_path.unlink()
                raise
        
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
            date_prefix = VALOR_DEFECTO_NODATE
        
        nombre_doc = self._obtener_campo(documento, "TRDNOMBREDOCUMENTO")
        if not nombre_doc:
            nombre_doc = VALOR_DEFECTO_NODOCNAME
        
        ext = EXTENSION_PDF
        if "image/tiff" in content_type:
            ext = EXTENSION_TIFF
        elif "image/jpeg" in content_type or "image/jpg" in content_type:
            ext = EXTENSION_JPG
        elif "image/png" in content_type:
            ext = EXTENSION_PNG
        
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

    def _es_sobre(self, pdf_path: Path) -> bool:
        """
        Verifica si un PDF es un SOBRE (tiene archivos embebidos/attachments).
        
        Args:
            pdf_path: Ruta al archivo PDF descargado
            
        Returns:
            True si el PDF tiene attachments embebidos, False en caso contrario
        """
        if not HAS_PYMUPDF:
            self.logger.warning(f"[SOBRE] {MSG_PYMUPDF_NO_INSTALADO}")
            return False
        
        if not pdf_path.exists():
            return False
        
        try:
            doc = fitz.open(str(pdf_path))
            tiene_attachments = doc.embfile_count() > 0
            doc.close()
            return tiene_attachments
        except Exception as e:
            self.logger.warning(f"[SOBRE] Error verificando attachments en {pdf_path}: {e}")
            return False

    def _extraer_y_mergear_adjuntos_sobre(self, pdf_path: Path, output_path: Path, incluir_caratula: bool = False) -> str:
        """
        Extrae todos los attachments embebidos de un PDF SOBRE y los mergea en un solo PDF.
        
        Args:
            pdf_path: Ruta al PDF que contiene los attachments
            output_path: Ruta donde guardar el PDF mergeado
            incluir_caratula: Si True, incluye el PDF original (carátula) al inicio del merge
            
        Returns:
            Ruta del archivo PDF mergeado
            
        Raises:
            Exception: Si no se pueden extraer o mergear los attachments
        """
        if not HAS_PYMUPDF:
            raise ValueError(MSG_PYMUPDF_INSTALAR)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"El archivo PDF no existe: {pdf_path}")
        
        self.logger.info(f"[SOBRE] Extrayendo y mergeando attachments de {pdf_path}")
        
        try:
            doc = fitz.open(str(pdf_path))
            
            if not doc.embfile_count():
                doc.close()
                raise ValueError(MSG_PDF_SIN_EMBEBIDOS)
            
            self.logger.info(f"[SOBRE] Detectados {doc.embfile_count()} archivo(s) embebido(s) en el PDF")
            
            # Crear directorio temporal para los attachments extraídos
            temp_dir = tempfile.mkdtemp(prefix=f"sobre_attachments_")
            archivos_para_mergear = []
            
            try:
                # Extraer cada attachment
                for i in range(doc.embfile_count()):
                    try:
                        embfile = doc.embfile_info(i)
                        nombre_archivo = embfile.get("filename", f"adjunto_{i+1}")
                        
                        datos_archivo = doc.embfile_get(i)
                        
                        # Sanitizar nombre del archivo
                        nombre_safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in nombre_archivo)
                        while "__" in nombre_safe:
                            nombre_safe = nombre_safe.replace("__", "_")
                        nombre_safe = nombre_safe.strip("_")
                        
                        # Si no tiene extensión, asumir PDF
                        if not any(nombre_safe.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff']):
                            nombre_safe += ".pdf"
                        
                        archivo_path = Path(temp_dir) / nombre_safe
                        
                        with open(archivo_path, 'wb') as f:
                            f.write(datos_archivo)
                        
                        # Solo agregar PDFs a la lista de merge
                        if nombre_safe.lower().endswith('.pdf'):
                            archivos_para_mergear.append(str(archivo_path))
                            tamaño_kb = len(datos_archivo) / 1024
                            self.logger.info(f"[SOBRE] Extraído: {nombre_safe} ({tamaño_kb:.2f} KB)")
                        else:
                            self.logger.warning(f"[SOBRE] Archivo {nombre_safe} no es PDF, se omite del merge")
                            
                    except Exception as e:
                        self.logger.warning(f"[SOBRE] Error extrayendo attachment {i+1}: {e}")
                        continue
                
                doc.close()
                
                if not archivos_para_mergear:
                    raise ValueError(MSG_NO_PDF_VALIDO)
                
                # Si se debe incluir la carátula, agregarla al inicio
                if incluir_caratula:
                    archivos_para_mergear.insert(0, str(pdf_path))
                    self.logger.info(f"[SOBRE] Incluyendo carátula al inicio del merge")
                
                # Mergear todos los PDFs
                self.logger.info(f"[SOBRE] Mergeando {len(archivos_para_mergear)} archivo(s) en un solo PDF...")
                
                writer = PdfWriter()
                
                for archivo_pdf in archivos_para_mergear:
                    try:
                        reader = PdfReader(archivo_pdf)
                        for page in reader.pages:
                            writer.add_page(page)
                    except Exception as e:
                        self.logger.warning(f"[SOBRE] Error procesando {archivo_pdf}: {e}")
                        continue
                
                # Asegurar que el directorio de salida existe
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Guardar PDF mergeado
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"[SOBRE] PDF mergeado exitosamente: {output_path}, Tamaño: {file_size_mb:.2f} MB")
                
                return str(output_path)
                
            finally:
                # Limpiar archivos temporales
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"[SOBRE] Archivos temporales eliminados")
                except Exception as e:
                    self.logger.warning(f"[SOBRE] Error eliminando archivos temporales: {e}")
        
        except Exception as e:
            self.logger.error(f"[SOBRE] Error procesando attachments: {e}")
            raise

