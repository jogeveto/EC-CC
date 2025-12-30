# coding: utf-8
"""
Módulo DynamicsCrmApi para Rocketbot.
Puente entre Rocketbot y Dynamics CRM con persistencia en SQL Server.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Any, Union

# ============================================
# CONFIGURACIÓN DE PATHS (NO MODIFICAR)
# ============================================
try:
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
modules_path = base_path + "modules" + os.sep
shared_path = modules_path + "shared" + os.sep
dynamics_module_path = modules_path + "DynamicsCrmApi" + os.sep
libs_path = dynamics_module_path + "libs" + os.sep

# Agregar paths al sys.path
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if dynamics_module_path not in sys.path:
    sys.path.insert(0, dynamics_module_path)
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# ============================================
# IMPORTS DE SHARED
# ============================================
import logging
from shared.utils.logger import get_logger
from shared.utils.config_helper import load_config_from_param
from shared.database.db_factory import DatabaseServiceFactory

# ============================================
# CONFIGURACIÓN DEL LOGGER
# ============================================
logger = get_logger("DynamicsCrmApi")
_logger_configurado = False

def _inicializar_logger_modulo(config: Dict[str, Any]) -> None:
    """Configura el logger del módulo."""
    global _logger_configurado, logger
    
    if _logger_configurado:
        return
    
    logs_config = config.get("Logs")
    ruta_base = config.get("Globales", {}).get("RutaBaseProyecto")
    
    config_para_logger = None
    if logs_config and isinstance(logs_config, dict):
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
    
    try:
        from shared.utils.logger import establecer_configuracion_global
        establecer_configuracion_global(config_para_logger, ruta_base)
    except (ImportError, AttributeError):
        pass
    
    try:
        from shared.utils.logger import setup_logger
        logger_obj = setup_logger("DynamicsCrmApi", logs_config=config_para_logger, ruta_base=ruta_base)
        logger = logger_obj
    except Exception:
        pass
    
    _logger_configurado = True


def _clean_rocketbot_config(config_param: Any) -> Any:
    """
    Limpia las llaves dobles de templates de Rocketbot en la configuración.
    
    Si Rocketbot pasa la configuración como "{{...JSON...}}", limpia las llaves
    externas para que pueda ser parseada correctamente como JSON.
    
    Args:
        config_param: Configuración que puede tener llaves dobles de template
    
    Returns:
        Configuración limpia sin llaves dobles externas
    """
    if not isinstance(config_param, str):
        return config_param
    
    # Limpiar espacios al inicio y final
    config_cleaned = config_param.strip()
    original = config_cleaned
    
    # Intentar limpiar llaves dobles múltiples veces (por si hay anidamiento)
    max_iterations = 3
    for iteration in range(max_iterations):
        # Verificar si tiene llaves dobles al inicio y final
        if not (config_cleaned.startswith("{{") and config_cleaned.endswith("}}")):
            break
        
        # Extraer contenido interno (eliminar {{ y }})
        inner = config_cleaned[2:-2].strip()
        
        # Si el contenido interno parece JSON (empieza y termina con {}),
        # usar el contenido interno
        if inner.startswith("{") and inner.endswith("}"):
            config_cleaned = inner
            logger.debug(f"[CLEAN_CONFIG] Iteración {iteration + 1}: Limpiadas llaves dobles externas")
        else:
            # Si no es JSON válido, podría ser un template de variable
            # En ese caso, no limpiar más y retornar como está
            break
    
    if config_cleaned != original:
        logger.debug(f"[CLEAN_CONFIG] Configuración limpiada: {original[:50]}... -> {config_cleaned[:50]}...")
    
    return config_cleaned


# ============================================
# PUNTO DE ENTRADA ROCKETBOT
# ============================================
module = GetParams("module")

try:
    if module == "consultar_por_filtros":
        logger.info("[INICIO] Consulta por filtros")
        config_param = GetParams("config")
        result_var = GetParams("result")
        
        # Variables de Rocketbot
        subcategorias_ids = GetParams("subcategorias_ids")
        invt_especificacion = GetParams("invt_especificacion")
        subcategoria_name = GetParams("subcategoria_name")
        dynamics_tenant_id = GetParams("dynamics_tenant_id")
        dynamics_client_id = GetParams("dynamics_client_id")
        dynamics_client_secret = GetParams("dynamics_client_secret")
        dynamics_url = GetParams("dynamics_url")
        
        try:
            # Cargar configuración (limpiar llaves dobles de Rocketbot si existen)
            config_param_cleaned = _clean_rocketbot_config(config_param) if config_param else None
            config = load_config_from_param(config_param_cleaned) if config_param_cleaned else {}
            _inicializar_logger_modulo(config)
            
            # Validar variables requeridas
            if not subcategorias_ids:
                raise ValueError("Variable 'subcategorias_ids' es requerida")
            if not subcategoria_name:
                raise ValueError("Variable 'subcategoria_name' es requerida")
            if not dynamics_tenant_id:
                raise ValueError("Variable 'dynamics_tenant_id' es requerida")
            if not dynamics_client_id:
                raise ValueError("Variable 'dynamics_client_id' es requerida")
            if not dynamics_client_secret:
                raise ValueError("Variable 'dynamics_client_secret' es requerida")
            if not dynamics_url:
                raise ValueError("Variable 'dynamics_url' es requerida")
            
            # Obtener configuración de BD
            db_config = config.get("database", {})
            if not db_config:
                raise ValueError("Configuración de base de datos no encontrada en 'config'")
            
            # Importar y configurar servicios
            from DynamicsCrmApi.core.dynamics_authenticator import Dynamics365Authenticator
            from DynamicsCrmApi.core.dynamics_client import Dynamics365Client
            from DynamicsCrmApi.services.db_service import PqrsDbService
            from DynamicsCrmApi.services.pqrs_service import PqrsService
            
            # Crear autenticador y cliente
            authenticator = Dynamics365Authenticator(
                tenant_id=dynamics_tenant_id,
                client_id=dynamics_client_id,
                client_secret=dynamics_client_secret
            )
            dynamics_client = Dynamics365Client(
                authenticator=authenticator,
                base_url=dynamics_url
            )
            
            # Crear servicios
            db_service = PqrsDbService(db_config)
            pqrs_service = PqrsService(dynamics_client, db_service)
            
            # Ejecutar consulta
            resultado = pqrs_service.consultar_por_filtros(
                subcategorias_ids=subcategorias_ids,
                invt_especificacion=invt_especificacion,
                subcategoria_name=subcategoria_name
            )
            
            logger.info(f"[FIN] Consulta completada: {resultado.get('status')}")
            if result_var:
                SetVar(result_var, resultado)
                
        except Exception as e:
            error_msg = f"Error en consulta por filtros: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e
    
    elif module == "actualizar_pqrs":
        logger.info("[INICIO] Actualización de PQRS")
        config_param = GetParams("config")
        result_var = GetParams("result")
        
        # Variables de Rocketbot
        subcategoria_name = GetParams("subcategoria_name")
        dynamics_tenant_id = GetParams("dynamics_tenant_id")
        dynamics_client_id = GetParams("dynamics_client_id")
        dynamics_client_secret = GetParams("dynamics_client_secret")
        dynamics_url = GetParams("dynamics_url")
        
        try:
            # Cargar configuración (limpiar llaves dobles de Rocketbot si existen)
            config_param_cleaned = _clean_rocketbot_config(config_param) if config_param else None
            config = load_config_from_param(config_param_cleaned) if config_param_cleaned else {}
            _inicializar_logger_modulo(config)
            
            # Validar variables requeridas
            if not subcategoria_name:
                raise ValueError("Variable 'subcategoria_name' es requerida")
            if not dynamics_tenant_id:
                raise ValueError("Variable 'dynamics_tenant_id' es requerida")
            if not dynamics_client_id:
                raise ValueError("Variable 'dynamics_client_id' es requerida")
            if not dynamics_client_secret:
                raise ValueError("Variable 'dynamics_client_secret' es requerida")
            if not dynamics_url:
                raise ValueError("Variable 'dynamics_url' es requerida")
            
            # Obtener configuración de BD
            db_config = config.get("database", {})
            if not db_config:
                raise ValueError("Configuración de base de datos no encontrada en 'config'")
            
            # Importar y configurar servicios
            from DynamicsCrmApi.core.dynamics_authenticator import Dynamics365Authenticator
            from DynamicsCrmApi.core.dynamics_client import Dynamics365Client
            from DynamicsCrmApi.services.db_service import PqrsDbService
            from DynamicsCrmApi.services.pqrs_service import PqrsService
            
            # Crear autenticador y cliente
            authenticator = Dynamics365Authenticator(
                tenant_id=dynamics_tenant_id,
                client_id=dynamics_client_id,
                client_secret=dynamics_client_secret
            )
            dynamics_client = Dynamics365Client(
                authenticator=authenticator,
                base_url=dynamics_url
            )
            
            # Crear servicios
            db_service = PqrsDbService(db_config)
            pqrs_service = PqrsService(dynamics_client, db_service)
            
            # Ejecutar actualización
            resultado = pqrs_service.actualizar_pqrs(subcategoria_name=subcategoria_name)
            
            logger.info(f"[FIN] Actualización completada: {resultado.get('status')}")
            if result_var:
                SetVar(result_var, resultado)
                
        except Exception as e:
            error_msg = f"Error en actualización de PQRS: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e
    
    elif module == "health_check":
        logger.info("[INICIO] Health check")
        config_param = GetParams("config")
        result_var = GetParams("result")
        
        try:
            # Cargar configuración (limpiar llaves dobles de Rocketbot si existen)
            config_param_cleaned = _clean_rocketbot_config(config_param) if config_param else None
            config = load_config_from_param(config_param_cleaned) if config_param_cleaned else {}
            _inicializar_logger_modulo(config)
            
            db_config = config.get("database", {})
            if not db_config:
                result = {
                    "status": "error",
                    "message": "No se encontró configuración de base de datos",
                }
            else:
                try:
                    crud = DatabaseServiceFactory.get_db_service_from_config(db_config.copy())
                    result = {
                        "status": "ok",
                        "message": "Conexión a base de datos exitosa",
                        "db_type": db_config.get("db_type", "unknown"),
                    }
                except Exception as db_error:
                    result = {
                        "status": "error",
                        "message": f"Error de conexión: {str(db_error)}",
                    }
            
            if result_var:
                SetVar(result_var, result)
            logger.info(f"[FIN] Health check: {result.get('status')}")
            
        except Exception as e:
            error_msg = f"Error en health check: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            result = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, result)
            PrintException()
            raise e

except Exception as e:
    logger.error(f"Error en módulo DynamicsCrmApi: {e}")
    PrintException()
    raise e
