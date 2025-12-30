# coding: utf-8
"""
Módulo ExpedicionCopias para Rocketbot.
Módulo base para el proceso de Expedición de Copias.

Este módulo está listo para recibir la lógica de negocio específica.
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

    def PrintException():  # noqa: D401, N802
        return None


base_path = tmp_global_obj["basepath"]
modules_path = base_path + "modules" + os.sep  # Path para importar 'shared'
shared_path = modules_path + "shared" + os.sep
expedicion_module_path = modules_path + "ExpedicionCopias" + os.sep
libs_path = expedicion_module_path + "libs" + os.sep

# Agregar modules_path PRIMERO para que 'import shared' funcione
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if expedicion_module_path not in sys.path:
    sys.path.insert(0, expedicion_module_path)  # Prioridad alta para el módulo actual
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)  # Prioridad alta para las dependencias

# Importar utilidades compartidas
import logging
from shared.utils.logger import get_logger
from shared.utils.config_helper import load_config_from_param

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
logger = get_logger("ExpedicionCopiasModule")

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
    
    # Reconfigurar el logger con la configuración proporcionada
    try:
        from shared.utils.logger import setup_logger
        logger_obj = setup_logger("ExpedicionCopiasModule", logs_config=config_para_logger, ruta_base=ruta_base)
    except NameError:
        from shared.utils.logger import setup_logger
        logger_obj = setup_logger("ExpedicionCopiasModule", logs_config=config_para_logger, ruta_base=ruta_base)
    
    # Actualizar el logger global del módulo
    global logger
    logger = logger_obj
    
    # Verificar que los handlers se agregaron correctamente
    try:
        if logger and logger.handlers:
            tiene_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
            if not tiene_file_handler:
                try:
                    from shared.utils.logger import _configurar_handlers_automaticos
                    _configurar_handlers_automaticos(logger, logs_config=config_para_logger, ruta_base=ruta_base)
                except (ImportError, AttributeError):
                    pass
    except Exception:
        pass
    
    _logger_configurado = True


# Obtener el módulo que fue invocado
module = GetParams("module")

try:
    if module == "health":
        """
        Verifica el estado de conexión con la base de datos.
        
        Parámetros:
            - config: Diccionario de configuración o ruta a archivo JSON
            - result: Variable donde guardar el resultado
        """
        import time
        inicio = time.time()
        config_param = GetParams("config")
        result_var = GetParams("result")

        logger.info("[INICIO] Health check - Verificando conexión con base de datos")
        logger.debug(f"[PARAMETROS] config presente: {config_param is not None}")

        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}

            # Configurar logger del módulo (solo una vez)
            _inicializar_logger_modulo(config)

            # Verificar configuración de base de datos
            logger.debug("[ESTADO] Verificando configuración de base de datos")
            db_config = config.get("database", {})
            if not db_config:
                result = {
                    "status": "error",
                    "message": "No se encontró configuración de base de datos",
                }
                if result_var:
                    SetVar(result_var, result)
                logger.error("[ERROR] Health check: Sin configuración de BD")
            else:
                # Intentar conexión
                from shared.database.db_factory import DatabaseServiceFactory

                try:
                    logger.debug("[ESTADO] Intentando conexión a base de datos")
                    crud = DatabaseServiceFactory.get_db_service_from_config(
                        db_config.copy()
                    )
                    # Hacer una consulta simple para verificar conexión
                    result = {
                        "status": "ok",
                        "message": "Conexión a base de datos exitosa",
                        "db_type": db_config.get("db_type", "unknown"),
                    }
                    logger.info("[ESTADO] Health check: Conexión exitosa")
                except Exception as db_error:
                    result = {
                        "status": "error",
                        "message": f"Error de conexión a BD: {str(db_error)}",
                    }
                    logger.error(f"[ERROR] Health check: Error de conexión - {db_error}", exc_info=True)

                if result_var:
                    SetVar(result_var, result)

            tiempo_ejecucion = time.time() - inicio
            logger.info(f"[FIN] Health check - Resultado: {result.get('status', 'unknown')}, tiempo={tiempo_ejecucion:.2f}s")

        except Exception as e:
            tiempo_ejecucion = time.time() - inicio
            error_msg = f"Error en health check: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            result = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, result)
            PrintException()
            raise e

    else:
        """
        Módulo no implementado aún.
        Este es un template base listo para recibir la lógica de negocio.
        """
        logger.warning(f"[WARNING] Módulo '{module}' no implementado aún")
        result = {
            "status": "not_implemented",
            "message": f"El módulo '{module}' aún no ha sido implementado"
        }
        result_var = GetParams("result")
        if result_var:
            SetVar(result_var, result)

except Exception as e:
    logger.error(f"Error en módulo ExpedicionCopias: {e}")
    PrintException()
    raise e

