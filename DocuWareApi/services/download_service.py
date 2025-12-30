# coding: utf-8
"""
Download Service for DocuWareApi module.
Orchestrates the complete download flow.
"""

import os
import sys
from typing import Dict, Any
from pathlib import Path

# Add shared to path
try:
    tmp_global_obj  # type: ignore[name-defined]
except NameError:
    tmp_global_obj = {"basepath": ""}  # type: ignore[misc]

base_path = tmp_global_obj["basepath"]
modules_path = base_path + "modules" + os.sep
shared_path = modules_path + "shared" + os.sep
docuware_module_path = modules_path + "DocuWareApi" + os.sep

if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if docuware_module_path not in sys.path:
    sys.path.insert(0, docuware_module_path)

from shared.utils.logger import get_logger
from DocuWareApi.core.docuware_client import DocuWareClient

logger = get_logger("DownloadService")


class DownloadService:
    """Servicio que orquesta el flujo completo de descarga desde DocuWare"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el servicio con la configuración.
        
        Args:
            config: Diccionario de configuración con:
                - docuware: Configuración de DocuWare
                - target: Configuración de destino (fileCabinetName, searchDialogName)
                - downloadPath: Ruta base para descargas
        """
        self.config = config
        self.logger = logger
        
    def download_by_matricula(self, matricula: str) -> Dict[str, Any]:
        """
        Descarga todos los documentos de una matrícula.
        
        Args:
            matricula: Matrícula a buscar
            
        Returns:
            Diccionario con:
                - success: bool
                - download_path: str (ruta completa donde se guardaron los archivos)
                - files_downloaded: int
                - error: str (si hubo error)
        """
        try:
            # Validar configuración
            docuware_config = self.config.get('docuware', {})
            if not docuware_config:
                raise ValueError("Configuración 'docuware' es requerida")
            
            target_config = self.config.get('target', {})
            file_cabinet_name = target_config.get('fileCabinetName')
            if not file_cabinet_name:
                raise ValueError("'fileCabinetName' es requerido en configuración 'target'")
            
            download_path_str = self.config.get('downloadPath')
            if not download_path_str:
                raise ValueError("'downloadPath' es requerido")
            
            # Crear ruta base de descarga
            base_download_path = Path(download_path_str)
            base_download_path.mkdir(parents=True, exist_ok=True)
            
            # Crear cliente DocuWare
            client = DocuWareClient(self.config, logger=self.logger)
            
            # 1. Autenticar
            self.logger.info("Iniciando autenticación con DocuWare...")
            client.login()
            
            # 2. Buscar gabinete
            self.logger.info(f"Buscando gabinete: {file_cabinet_name}")
            client.file_cabinet_id = client.get_file_cabinet_id(file_cabinet_name)
            if not client.file_cabinet_id:
                raise Exception(f"No se pudo encontrar el gabinete: {file_cabinet_name}")
            
            # 3. Buscar diálogo de búsqueda
            search_dialog_name = target_config.get('searchDialogName')
            self.logger.info("Buscando diálogo de búsqueda...")
            client.search_dialog_id = client.get_search_dialog_id(client.file_cabinet_id, search_dialog_name)
            if not client.search_dialog_id:
                raise Exception("No se pudo encontrar el diálogo de búsqueda")
            
            # 4. Procesar matrícula
            self.logger.info(f"Procesando matrícula: {matricula}")
            files_downloaded = client.process_matricula(matricula, base_download_path)
            
            # 5. Obtener ruta final donde se guardaron los archivos
            final_download_path = client.get_download_path_for_matricula(base_download_path, matricula)
            
            self.logger.info(f"Proceso completado: {files_downloaded} archivos descargados en {final_download_path}")
            
            # Normalizar ruta: convertir backslashes a forward slashes para Rocketbot
            # Rocketbot tiene problemas con backslashes en variables
            download_path_normalized = str(final_download_path).replace('\\', '/')
            
            return {
                "success": True,
                "download_path": download_path_normalized,
                "files_downloaded": files_downloaded,
                "matricula": matricula
            }
            
        except Exception as e:
            error_msg = f"Error al descargar documentos de matrícula {matricula}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "download_path": "",
                "files_downloaded": 0,
                "matricula": matricula,
                "error": str(e)
            }

