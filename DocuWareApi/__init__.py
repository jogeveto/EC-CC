# coding: utf-8
"""
Módulo DocuWareApi para Rocketbot.
Módulo para descargar documentos desde DocuWare Platform API por matrícula.
"""

from __future__ import annotations  # Makes all annotations strings - no runtime evaluation

import os
import sys
from typing import Dict, Any

# Agregar shared, libs y directorio actual del módulo al path
try:  # Permite importación fuera de Rocketbot (tests unitarios)
    tmp_global_obj  # type: ignore[name-defined]
except NameError:  # pragma: no cover
    tmp_global_obj = {"basepath": ""}

    def GetParams(_):  # noqa: D401, N802
        return None

    def SetVar(_, __):  # noqa: D401, N802
        return None

    def GetVar(_):  # noqa: D401, N802
        return None

    def PrintException():  # noqa: D401, N802
        return None


base_path = tmp_global_obj["basepath"]
modules_path = base_path + "modules" + os.sep  # Path para importar 'shared'
shared_path = modules_path + "shared" + os.sep
docuware_module_path = modules_path + "DocuWareApi" + os.sep
libs_path = docuware_module_path + "libs" + os.sep

# Agregar modules_path PRIMERO para que 'import shared' funcione
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if docuware_module_path not in sys.path:
    sys.path.insert(0, docuware_module_path)  # Prioridad alta para el módulo actual
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)  # Prioridad alta para las dependencias

# Importar utilidades compartidas
import logging
from shared.utils.logger import get_logger

# Definir función dummy primero (fallback)
def establecer_configuracion_global(logs_config=None, ruta_base=None):
    """Función dummy cuando establecer_configuracion_global no está disponible."""
    pass

# Intentar importar establecer_configuracion_global y reemplazar la dummy si está disponible
try:
    from shared.utils.logger import establecer_configuracion_global as _establecer_config_global
    establecer_configuracion_global = _establecer_config_global
except (ImportError, AttributeError):
    # Mantener la función dummy si no está disponible
    pass

# Logger del módulo
logger = get_logger("DocuWareApiModule")

# Variable para rastrear si el logger ya fue configurado
_logger_configurado = False


def _inicializar_logger_modulo(config: Dict[str, Any]) -> None:
    """
    Configura el logger del módulo una sola vez usando la configuración proporcionada.
    
    Args:
        config: Diccionario de configuración que puede contener:
            - Logs: Configuración de logs (RutaLogAuditoria, NombreLogAuditoria, etc.)
            - Globales: Configuración global (RutaBaseProyecto, etc.)
    """
    global _logger_configurado, logger
    
    if _logger_configurado:
        return  # Ya configurado, no hacer nada
    
    # Extraer configuración de logs y ruta base
    logs_config = None
    ruta_base = None
    
    # Intentar obtener Logs directamente
    if "Logs" in config:
        logs_config = config.get("Logs")
    
    # Intentar obtener Globales directamente
    if "Globales" in config:
        globales = config.get("Globales", {})
        if isinstance(globales, dict):
            ruta_base = globales.get("RutaBaseProyecto")
    
    # Si no se encontró, intentar buscar en otras estructuras posibles
    if not logs_config:
        for key in ["Logs", "logs", "LOG"]:
            if key in config:
                logs_config = config.get(key)
                break
    
    if not ruta_base:
        for key in ["Globales", "globales", "GLOBAL"]:
            if key in config:
                globales = config.get(key, {})
                if isinstance(globales, dict):
                    ruta_base = globales.get("RutaBaseProyecto") or globales.get("ruta_base") or globales.get("RutaBase")
                    if ruta_base:
                        break
    
    # Preparar configuración para setup_logger
    config_para_logger = None
    
    if logs_config and isinstance(logs_config, dict) and logs_config:
        ya_normalizado = "auditoria" in logs_config or "sistema" in logs_config
        
        if ya_normalizado:
            config_para_logger = logs_config
        else:
            config_para_logger = {
                "Logs": logs_config,
                "Globales": {"RutaBaseProyecto": ruta_base} if ruta_base else {}
            }
    elif ruta_base:
        config_para_logger = {
            "Logs": {},
            "Globales": {"RutaBaseProyecto": ruta_base}
        }
    
    # Establecer configuración global para que todos los loggers la usen
    try:
        establecer_configuracion_global(config_para_logger, ruta_base)
    except NameError:
        pass
    
    # Reobtener logger con la nueva configuración (get_logger usará la config global)
    try:
        from shared.utils.logger import get_logger
        global logger
        logger = get_logger("DocuWareApiModule", logs_config=config_para_logger, ruta_base=ruta_base)
    except Exception:
        # Si falla, mantener el logger inicial
        pass
    
    _logger_configurado = True


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parsea un valor a booleano"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


def _resolve_project_var(value: Any) -> Any:
    """
    Resuelve una variable del proyecto si el valor es un template de Rocketbot.
    
    Si GetParams retorna "{{variableName}}", intenta resolverlo usando GetVar()
    para obtener el valor real de la variable del proyecto.
    
    Args:
        value: Valor que puede ser un template "{{variableName}}" o un valor directo
        
    Returns:
        Valor resuelto de GetVar() si es un template, o el valor original
    """
    if not isinstance(value, str):
        return value
    
    value_stripped = value.strip()
    
    # Detectar si es un template de variable {{variableName}}
    if value_stripped.startswith("{{") and value_stripped.endswith("}}"):
        var_name = value_stripped[2:-2].strip()
        
        # Llamar GetVar directamente (ya está definido por Rocketbot o función dummy)
        resolved = GetVar(var_name)
        
        # GetVar puede retornar None si la variable no existe
        if resolved is not None:
            # Limpiar el valor resuelto: eliminar llaves si las tiene
            if isinstance(resolved, str):
                resolved_clean = resolved.strip()
                # Si el valor resuelto tiene llaves al inicio y final, eliminarlas
                if resolved_clean.startswith("{") and resolved_clean.endswith("}"):
                    resolved_clean = resolved_clean[1:-1].strip()
                return resolved_clean
            else:
                return resolved
    
    # Si el valor original tiene llaves pero no es un template, limpiarlas también
    if value_stripped.startswith("{") and value_stripped.endswith("}") and not value_stripped.startswith("{{"):
        return value_stripped[1:-1].strip()
    
    return value


# Obtener el módulo que fue invocado
module = GetParams("module")

try:
    if module == "download_by_matricula":
        """
        Descarga documentos desde DocuWare por matrícula.
        
        Parámetros:
            - serverUrl: URL del servidor DocuWare (requerido)
            - username: Usuario de DocuWare (requerido)
            - password: Contraseña de DocuWare (requerido)
            - tokenEndpoint: Endpoint para token (opcional, vacío para descubrimiento automático)
            - organizationId: ID de organización (opcional)
            - platform: Plataforma DocuWare (default: "DocuWare/Platform")
            - verifySSL: Verificar certificados SSL (default: "true")
            - fileCabinetName: Nombre del gabinete (requerido)
            - searchDialogName: Nombre del diálogo de búsqueda (opcional)
            - matricula: Matrícula a buscar (requerido)
            - downloadPath: Ruta base para descargas (requerido)
            - result: Variable donde guardar el resultado (opcional)
        """
        import time
        inicio = time.time()
        
        # Obtener todas las variables individualmente y resolver templates del proyecto
        server_url = _resolve_project_var(GetParams("serverUrl"))
        username = _resolve_project_var(GetParams("username"))
        password = _resolve_project_var(GetParams("password"))
        token_endpoint = _resolve_project_var(GetParams("tokenEndpoint")) or ""
        organization_id = _resolve_project_var(GetParams("organizationId")) or ""
        platform = _resolve_project_var(GetParams("platform")) or "DocuWare/Platform"
        verify_ssl_str = _resolve_project_var(GetParams("verifySSL")) or "true"
        file_cabinet_name = _resolve_project_var(GetParams("fileCabinetName"))
        search_dialog_name = _resolve_project_var(GetParams("searchDialogName")) or ""
        matricula = _resolve_project_var(GetParams("matricula"))
        download_path = _resolve_project_var(GetParams("downloadPath"))
        result_var = _resolve_project_var(GetParams("result"))
        
        logger.info("[INICIO] download_by_matricula - Descargando documentos desde DocuWare")
        logger.debug(f"[PARAMETROS] matricula={matricula}, serverUrl={server_url}")
        
        try:
            # Validar variables requeridas
            required_params = {
                "serverUrl": server_url,
                "username": username,
                "password": password,
                "fileCabinetName": file_cabinet_name,
                "matricula": matricula,
                "downloadPath": download_path
            }
            
            missing_params = [param for param, value in required_params.items() if not value]
            if missing_params:
                error_msg = f"Parámetros requeridos faltantes: {', '.join(missing_params)}"
                logger.error(f"[ERROR] {error_msg}")
                result = {
                    "success": False,
                    "download_path": "",
                    "files_downloaded": 0,
                    "error": error_msg
                }
                if result_var:
                    SetVar(result_var, result)
                raise ValueError(error_msg)
            
            # Construir configuración
            config = {
                "docuware": {
                    "serverUrl": server_url.strip(),
                    "username": username.strip(),
                    "password": password.strip(),
                    "platform": platform.strip(),
                    "verifySSL": verify_ssl_str.strip().lower() in ('true', '1', 'yes', 'on')
                },
                "target": {
                    "fileCabinetName": file_cabinet_name.strip()
                },
                "downloadPath": download_path.strip()
            }
            
            # Agregar parámetros opcionales solo si tienen valor
            if token_endpoint and token_endpoint.strip():
                config["docuware"]["tokenEndpoint"] = token_endpoint.strip()
            
            if organization_id and organization_id.strip():
                config["docuware"]["organizationId"] = organization_id.strip()
            
            if search_dialog_name and search_dialog_name.strip():
                config["target"]["searchDialogName"] = search_dialog_name.strip()
            
            # Configurar logger del módulo (solo una vez)
            _inicializar_logger_modulo({})
            
            # Importar y usar el servicio
            from DocuWareApi.services.download_service import DownloadService
            
            # Crear servicio
            service = DownloadService(config)
            
            # Ejecutar descarga
            result = service.download_by_matricula(matricula.strip())
            
            if result_var:
                SetVar(result_var, result)
            
            tiempo_ejecucion = time.time() - inicio
            if result.get("success"):
                logger.info(f"[FIN] download_by_matricula - Éxito: {result.get('files_downloaded', 0)} archivos descargados en {result.get('download_path', '')}, tiempo={tiempo_ejecucion:.2f}s")
            else:
                logger.error(f"[FIN] download_by_matricula - Error: {result.get('error', 'Desconocido')}, tiempo={tiempo_ejecucion:.2f}s")
            
        except Exception as e:
            tiempo_ejecucion = time.time() - inicio
            error_msg = f"Error en download_by_matricula: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            result = {
                "success": False,
                "download_path": "",
                "files_downloaded": 0,
                "error": error_msg
            }
            if result_var:
                SetVar(result_var, result)
            PrintException()
            raise e
    
    else:
        """
        Módulo no reconocido.
        """
        logger.warning(f"[WARNING] Módulo '{module}' no reconocido")
        result = {
            "success": False,
            "error": f"El módulo '{module}' no está implementado. Use 'download_by_matricula'"
        }
        result_var = GetParams("result")
        if result_var:
            SetVar(result_var, result)

except Exception as e:
    logger.error(f"Error en módulo DocuWareApi: {e}", exc_info=True)
    PrintException()
    raise e

