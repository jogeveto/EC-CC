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
    
    def GetVar(_):  # noqa: D401, N802
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


def _load_database_config_from_rocketbot() -> Dict[str, Any]:
    """
    Construye configuración de BD buscando variable por variable en Rocketbot.
    Todas las variables deben estar configuradas en Rocketbot con los nombres exactos especificados.
    No hay valores por defecto, todas son obligatorias.
    
    Returns:
        Diccionario de configuración compatible con DatabaseServiceFactory.get_db_service_from_config()
    
    Raises:
        ValueError: Si falta alguna variable requerida
    """
    # Obtener todas las variables de Rocketbot (todas son requeridas)
    db_type = GetVar("db_type")  # type: ignore[name-defined]
    db_server = GetVar("db_server")  # type: ignore[name-defined]
    db_database = GetVar("db_database")  # type: ignore[name-defined]
    db_user = GetVar("db_user")  # type: ignore[name-defined]
    db_password = GetVar("db_password")  # type: ignore[name-defined]
    db_driver = GetVar("db_driver")  # type: ignore[name-defined]
    db_schema = GetVar("db_schema")  # type: ignore[name-defined]
    
    # Validar que todas las variables estén configuradas (no hay valores por defecto)
    if not db_type or db_type == "":
        raise ValueError("Variable 'db_type' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el tipo de base de datos (ej: sqlserver)")
    if not db_server or db_server == "":
        raise ValueError("Variable 'db_server' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el servidor (ej: localhost,1433)")
    if not db_database or db_database == "":
        raise ValueError("Variable 'db_database' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el nombre de la base de datos")
    if not db_user or db_user == "":
        raise ValueError("Variable 'db_user' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el usuario de la base de datos")
    if not db_password or db_password == "":
        raise ValueError("Variable 'db_password' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con la contraseña de la base de datos")
    if not db_driver or db_driver == "":
        raise ValueError("Variable 'db_driver' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el driver ODBC (ej: ODBC Driver 17 for SQL Server)")
    if not db_schema or db_schema == "":
        raise ValueError("Variable 'db_schema' no encontrada o vacía en Rocketbot. Debe configurarse obligatoriamente con el esquema de la base de datos")
    
    # Construir diccionario de configuración (todas las variables son requeridas)
    db_config: Dict[str, Any] = {
        "db_type": db_type,
        "server": db_server,
        "database": db_database,
        "user": db_user,
        "password": db_password,
        "driver": db_driver,
        "schema": db_schema
    }
    
    logger.info(f"[DB_CONFIG] Configuración de BD construida: tipo={db_type}, server={db_server}, database={db_database}, user={db_user}, driver={db_driver}, schema={db_schema}")
    
    return db_config


# ============================================
# PUNTO DE ENTRADA ROCKETBOT
# ============================================
module = GetParams("module")

try:
    if module == "consultar_por_filtros":
        logger.info("[INICIO] Consulta por filtros")
        result_var = GetParams("result")
        
        # Obtener todas las variables desde Rocketbot (ya configuradas en el sistema)
        subcategorias_ids = GetVar("subcategorias_ids")  # type: ignore[name-defined]
        invt_especificacion = GetVar("invt_especificacion")  # type: ignore[name-defined]
        subcategoria_name = GetVar("subcategoria_name")  # type: ignore[name-defined]
        dynamics_tenant_id = GetVar("dynamics_tenant_id")  # type: ignore[name-defined]
        dynamics_client_id = GetVar("dynamics_client_id")  # type: ignore[name-defined]
        dynamics_client_secret = GetVar("dynamics_client_secret")  # type: ignore[name-defined]
        dynamics_url = GetVar("dynamics_url")  # type: ignore[name-defined]
        
        # Limpiar valores de espacios en blanco y comillas
        # IMPORTANTE: Esta función preserva caracteres especiales como ~, -, _, etc.
        # que son comunes en client secrets de Azure
        def _clean_value(value: str) -> str:
            """
            Limpia valores de espacios y comillas, preservando caracteres especiales.
            
            Args:
                value: Valor a limpiar
                
            Returns:
                Valor limpiado
            """
            if not value:
                return value
            
            # Guardar valor original para logging
            original_value = str(value)
            original_length = len(original_value)
            
            cleaned = original_value.strip()
            
            # Eliminar comillas al inicio y final si existen
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()
            elif cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1].strip()
            
            # Logging si hay cambios significativos (solo para diagnóstico)
            if len(cleaned) != original_length:
                logger.debug(f"[CLEAN_VALUE] Valor limpiado: longitud original={original_length}, longitud final={len(cleaned)}")
            
            # Detectar caracteres problemáticos
            if '\n' in cleaned or '\r' in cleaned:
                logger.warning(f"[CLEAN_VALUE] Valor contiene caracteres de nueva línea! repr: {repr(cleaned[:50])}")
            
            return cleaned
        
        subcategorias_ids = _clean_value(subcategorias_ids)
        invt_especificacion = _clean_value(invt_especificacion)
        subcategoria_name = _clean_value(subcategoria_name)
        dynamics_tenant_id = _clean_value(dynamics_tenant_id)
        dynamics_client_id = _clean_value(dynamics_client_id)
        dynamics_client_secret = _clean_value(dynamics_client_secret)
        dynamics_url = _clean_value(dynamics_url)
        
        try:
            # Inicializar logger sin configuración (usa valores por defecto)
            _inicializar_logger_modulo({})
            
            # Validar variables requeridas
            if not subcategorias_ids or subcategorias_ids == "":
                raise ValueError("Variable 'subcategorias_ids' no encontrada o vacía en Rocketbot")
            if not subcategoria_name or subcategoria_name == "":
                raise ValueError("Variable 'subcategoria_name' no encontrada o vacía en Rocketbot")
            if not dynamics_tenant_id or dynamics_tenant_id == "":
                raise ValueError("Variable 'dynamics_tenant_id' no encontrada o vacía en Rocketbot")
            if not dynamics_client_id or dynamics_client_id == "":
                raise ValueError("Variable 'dynamics_client_id' no encontrada o vacía en Rocketbot")
            if not dynamics_client_secret or dynamics_client_secret == "":
                raise ValueError("Variable 'dynamics_client_secret' no encontrada o vacía en Rocketbot")
            if not dynamics_url or dynamics_url == "":
                raise ValueError("Variable 'dynamics_url' no encontrada o vacía en Rocketbot")
            
            # Validar longitud mínima del secret (los secrets de Azure suelen tener al menos 20 caracteres)
            if len(dynamics_client_secret) < 20:
                logger.warning(f"[SECRET_VALIDATION] El client_secret tiene solo {len(dynamics_client_secret)} caracteres. Esto podría indicar un problema de configuración.")
            
            # Logging seguro del secret (solo primeros y últimos caracteres para diagnóstico)
            # Usar INFO en lugar de DEBUG para que siempre se muestre
            secret_preview = ""
            if len(dynamics_client_secret) >= 8:
                secret_preview = f"{dynamics_client_secret[:4]}...{dynamics_client_secret[-4:]}"
            else:
                secret_preview = "[SECRET DEMASIADO CORTO]"
            
            logger.info(f"[CREDENTIALS] Configuración de Dynamics 365: tenant_id={dynamics_tenant_id[:8]}..., client_id={dynamics_client_id[:8]}..., secret_length={len(dynamics_client_secret)}, url={dynamics_url}")
            logger.info(f"[SECRET_PREVIEW] Secret: {secret_preview} (longitud: {len(dynamics_client_secret)})")
            
            # Verificar si hay caracteres problemáticos
            if '\n' in dynamics_client_secret or '\r' in dynamics_client_secret:
                logger.warning("[SECRET_WARNING] El secret contiene caracteres de nueva línea!")
            if dynamics_client_secret != dynamics_client_secret.strip():
                logger.warning("[SECRET_WARNING] El secret contiene espacios al inicio o final!")
            
            # Mostrar representación para detectar caracteres invisibles (solo primeros 30 caracteres)
            logger.info(f"[SECRET_REPR] repr(secret[:30]): {repr(dynamics_client_secret[:30])}")
            
            # Obtener configuración de BD desde variables de Rocketbot
            db_config = _load_database_config_from_rocketbot()
            
            # Importar y configurar servicios
            from DynamicsCrmApi.core.dynamics_authenticator import Dynamics365Authenticator
            from DynamicsCrmApi.core.dynamics_client import Dynamics365Client
            from DynamicsCrmApi.services.db_service import PqrsDbService
            from DynamicsCrmApi.services.pqrs_service import PqrsService
            
            # Crear autenticador y cliente
            logger.info("[AUTH] Creando autenticador de Dynamics 365...")
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
        result_var = GetParams("result")
        
        # Obtener todas las variables desde Rocketbot (ya configuradas en el sistema)
        subcategoria_name = GetVar("subcategoria_name")  # type: ignore[name-defined]
        dynamics_tenant_id = GetVar("dynamics_tenant_id")  # type: ignore[name-defined]
        dynamics_client_id = GetVar("dynamics_client_id")  # type: ignore[name-defined]
        dynamics_client_secret = GetVar("dynamics_client_secret")  # type: ignore[name-defined]
        dynamics_url = GetVar("dynamics_url")  # type: ignore[name-defined]
        
        # Limpiar valores de espacios en blanco y comillas
        # IMPORTANTE: Esta función preserva caracteres especiales como ~, -, _, etc.
        # que son comunes en client secrets de Azure
        def _clean_value(value: str) -> str:
            """
            Limpia valores de espacios y comillas, preservando caracteres especiales.
            
            Args:
                value: Valor a limpiar
                
            Returns:
                Valor limpiado
            """
            if not value:
                return value
            
            # Guardar valor original para logging
            original_value = str(value)
            original_length = len(original_value)
            
            cleaned = original_value.strip()
            
            # Eliminar comillas al inicio y final si existen
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()
            elif cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1].strip()
            
            # Logging si hay cambios significativos (solo para diagnóstico)
            if len(cleaned) != original_length:
                logger.debug(f"[CLEAN_VALUE] Valor limpiado: longitud original={original_length}, longitud final={len(cleaned)}")
            
            # Detectar caracteres problemáticos
            if '\n' in cleaned or '\r' in cleaned:
                logger.warning(f"[CLEAN_VALUE] Valor contiene caracteres de nueva línea! repr: {repr(cleaned[:50])}")
            
            return cleaned
        
        subcategoria_name = _clean_value(subcategoria_name)
        dynamics_tenant_id = _clean_value(dynamics_tenant_id)
        dynamics_client_id = _clean_value(dynamics_client_id)
        dynamics_client_secret = _clean_value(dynamics_client_secret)
        dynamics_url = _clean_value(dynamics_url)
        
        try:
            # Inicializar logger sin configuración (usa valores por defecto)
            _inicializar_logger_modulo({})
            
            # Validar variables requeridas
            if not subcategoria_name or subcategoria_name == "":
                raise ValueError("Variable 'subcategoria_name' no encontrada o vacía en Rocketbot")
            if not dynamics_tenant_id or dynamics_tenant_id == "":
                raise ValueError("Variable 'dynamics_tenant_id' no encontrada o vacía en Rocketbot")
            if not dynamics_client_id or dynamics_client_id == "":
                raise ValueError("Variable 'dynamics_client_id' no encontrada o vacía en Rocketbot")
            if not dynamics_client_secret or dynamics_client_secret == "":
                raise ValueError("Variable 'dynamics_client_secret' no encontrada o vacía en Rocketbot")
            if not dynamics_url or dynamics_url == "":
                raise ValueError("Variable 'dynamics_url' no encontrada o vacía en Rocketbot")
            
            # Validar longitud mínima del secret (los secrets de Azure suelen tener al menos 20 caracteres)
            if len(dynamics_client_secret) < 20:
                logger.warning(f"[SECRET_VALIDATION] El client_secret tiene solo {len(dynamics_client_secret)} caracteres. Esto podría indicar un problema de configuración.")
            
            # Logging seguro del secret (solo primeros y últimos caracteres para diagnóstico)
            # Usar INFO en lugar de DEBUG para que siempre se muestre
            secret_preview = ""
            if len(dynamics_client_secret) >= 8:
                secret_preview = f"{dynamics_client_secret[:4]}...{dynamics_client_secret[-4:]}"
            else:
                secret_preview = "[SECRET DEMASIADO CORTO]"
            
            logger.info(f"[CREDENTIALS] Configuración de Dynamics 365: tenant_id={dynamics_tenant_id[:8]}..., client_id={dynamics_client_id[:8]}..., secret_length={len(dynamics_client_secret)}, url={dynamics_url}")
            logger.info(f"[SECRET_PREVIEW] Secret: {secret_preview} (longitud: {len(dynamics_client_secret)})")
            
            # Verificar si hay caracteres problemáticos
            if '\n' in dynamics_client_secret or '\r' in dynamics_client_secret:
                logger.warning("[SECRET_WARNING] El secret contiene caracteres de nueva línea!")
            if dynamics_client_secret != dynamics_client_secret.strip():
                logger.warning("[SECRET_WARNING] El secret contiene espacios al inicio o final!")
            
            # Mostrar representación para detectar caracteres invisibles (solo primeros 30 caracteres)
            logger.info(f"[SECRET_REPR] repr(secret[:30]): {repr(dynamics_client_secret[:30])}")
            
            # Obtener configuración de BD desde variables de Rocketbot
            db_config = _load_database_config_from_rocketbot()
            
            # Importar y configurar servicios
            from DynamicsCrmApi.core.dynamics_authenticator import Dynamics365Authenticator
            from DynamicsCrmApi.core.dynamics_client import Dynamics365Client
            from DynamicsCrmApi.services.db_service import PqrsDbService
            from DynamicsCrmApi.services.pqrs_service import PqrsService
            
            # Crear autenticador y cliente
            logger.info("[AUTH] Creando autenticador de Dynamics 365...")
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
        result_var = GetParams("result")
        
        try:
            # Inicializar logger sin configuración (usa valores por defecto)
            _inicializar_logger_modulo({})
            
            # Obtener configuración de BD desde variables de Rocketbot
            try:
                db_config = _load_database_config_from_rocketbot()
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
            except ValueError as config_error:
                result = {
                    "status": "error",
                    "message": f"No se encontró configuración de base de datos: {str(config_error)}",
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
