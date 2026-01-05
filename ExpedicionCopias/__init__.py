# coding: utf-8
"""
Módulo ExpedicionCopias para Rocketbot.
Procesa casos de expedición de copias para particulares y entidades oficiales.

Funcionalidades:
- Procesamiento de casos de COPIAS (particulares)
- Procesamiento de casos de COPIAS ENTIDADES OFICIALES
- Integración con Dynamics 365 CRM
- Integración con DocuWare para descarga de documentos
- Integración con Microsoft Graph API
- Validación de reglas y excepciones
- Generación y organización de archivos PDF
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, cast, Dict, Any

# Type imports for IDE support (only evaluated by type checkers, not at runtime)
if TYPE_CHECKING:
    from ExpedicionCopias.services.expedicion_service import ExpedicionService

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
expedicion_module_path = modules_path + "ExpedicionCopias" + os.sep
libs_path = expedicion_module_path + "libs" + os.sep

# Agregar paths al sys.path
if modules_path not in sys.path:
    sys.path.insert(0, modules_path)
if shared_path not in sys.path:
    sys.path.append(shared_path)
if expedicion_module_path not in sys.path:
    sys.path.insert(0, expedicion_module_path)
# Solo agregar libs_path si existe (opcional - para librerías vendored)
if os.path.exists(libs_path) and libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# ============================================
# IMPORTS DE SHARED
# ============================================
import logging
from shared.utils.logger import get_logger
from shared.utils.config_helper import load_config_from_param

# ============================================
# CONFIGURACIÓN DEL LOGGER
# ============================================
logger = get_logger("ExpedicionCopiasModule")
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
        logger_obj = setup_logger("ExpedicionCopiasModule", logs_config=config_para_logger, ruta_base=ruta_base)
        logger = logger_obj
    except Exception:
        pass

    _logger_configurado = True


def _import_expedicion_service(module_path: str) -> type[ExpedicionService]:
    """
    Importa ExpedicionService con soporte completo para typing.

    Intenta importación normal primero (funciona en IDE/desarrollo y preserva typing),
    luego fallback a importlib (funciona en Rocketbot).

    Args:
        module_path: Ruta base del módulo ExpedicionCopias

    Returns:
        Clase ExpedicionService
    """
    # Try 1: Normal import (works in IDE/development) - preserves full typing
    try:
        from ExpedicionCopias.services.expedicion_service import ExpedicionService
        return ExpedicionService  # type: ignore[return-value]
    except (ImportError, ModuleNotFoundError):
        pass

    # Try 2: Full module path import - also preserves typing
    try:
        from services.expedicion_service import ExpedicionService
        return ExpedicionService  # type: ignore[return-value]
    except (ImportError, ModuleNotFoundError):
        pass

    # Try 3: importlib fallback (works in Rocketbot)
    import importlib.util
    expedicion_service_path = module_path + "services" + os.sep + "expedicion_service.py"
    spec = importlib.util.spec_from_file_location("expedicion_service", expedicion_service_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar expedicion_service desde {expedicion_service_path}")

    expedicion_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(expedicion_module)

    if not hasattr(expedicion_module, "ExpedicionService"):
        raise ImportError("ExpedicionService no encontrado en expedicion_service.py")

    return cast(type[ExpedicionService], expedicion_module.ExpedicionService)  # type: ignore[return-value, type-arg]


# ============================================
# PUNTO DE ENTRADA ROCKETBOT
# ============================================
module = GetParams("module")

try:
    if module == "procesar_copias":
        """
        Procesa casos de COPIAS (particulares).

        Parámetros:
            - config: Diccionario de configuración o ruta a archivo JSON
            - result: Variable donde guardar el resultado

        Flujo:
            1. Obtiene configuración y variables de Rocketbot
            2. Inicializa ExpedicionService
            3. Ejecuta procesar_particulares()
            4. Retorna resumen de procesamiento
        """
        logger.info("[INICIO] Procesamiento de copias (particulares)")
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            logger.info(f"Cargando configuración desde: {config_param}")
            config = load_config_from_param(config_param) if config_param else {}
            logger.info("Configuración cargada exitosamente")

            # Inicializar logger del módulo
            logger.info("Inicializando logger del módulo...")
            _inicializar_logger_modulo(config)
            logger.info("Logger del módulo inicializado")

            # Obtener variables de Rocketbot
            logger.info("Obteniendo variables de Rocketbot...")
            graph_client_secret = GetVar("graph_client_secret")  # type: ignore[name-defined]
            dynamics_client_secret = GetVar("dynamics_client_secret")  # type: ignore[name-defined]
            docuware_password = GetVar("docuware_password")  # type: ignore[name-defined]
            database_password = GetVar("database_password")  # type: ignore[name-defined]

            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")

            logger.info("Variables de Rocketbot obtenidas exitosamente")

            # Agregar secrets a la configuración (sin modificar estructura original del JSON)
            # Los secrets se obtienen de variables de Rocketbot y se agregan al config dict
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            # Asegurar que DocuWare existe antes de agregar password
            if "DocuWare" not in config:
                config["DocuWare"] = {}
            config["DocuWare"]["password"] = docuware_password
            # Database password es opcional
            if database_password:
                if "Database" not in config:
                    config["Database"] = {}
                config["Database"]["password"] = database_password

            # Import ExpedicionService with full typing support
            logger.info("Importando ExpedicionService...")
            ExpedicionServiceClass = _import_expedicion_service(expedicion_module_path)
            logger.info("Creando instancia de ExpedicionService...")
            service: ExpedicionService = ExpedicionServiceClass(config)  # type: ignore[assignment]
            logger.info("Ejecutando procesar_particulares()...")
            resultado = service.procesar_particulares()

            casos_procesados = resultado.get('casos_procesados', 0)
            casos_error = resultado.get('casos_error', 0)
            reporte_path = resultado.get('reporte_path', 'N/A')
            
            logger.info(f"[FIN] Procesamiento completado: {casos_procesados} casos procesados, {casos_error} errores")
            logger.info(f"[FIN] Reporte generado en: {reporte_path}")
            
            # Obtener IDs de casos procesados y con error para el resumen
            casos_procesados_ids = []
            casos_error_ids = []
            if hasattr(service, 'casos_procesados'):
                for item in service.casos_procesados:
                    caso = item.get('caso', {})
                    case_id = caso.get('sp_documentoid', 'N/A')
                    casos_procesados_ids.append(case_id)
            if hasattr(service, 'casos_error'):
                for item in service.casos_error:
                    caso = item.get('caso', {})
                    case_id = caso.get('sp_documentoid', 'N/A')
                    casos_error_ids.append(case_id)
            
            if casos_procesados_ids:
                logger.info(f"[FIN] Casos procesados exitosamente (IDs): {', '.join(casos_procesados_ids)}")
            if casos_error_ids:
                logger.warning(f"[FIN] Casos con error (IDs): {', '.join(casos_error_ids)}")

            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error al procesar copias: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg, "casos_procesados": 0, "casos_error": 0}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e

    elif module == "procesar_copias_oficiales":
        """
        Procesa casos de COPIAS ENTIDADES OFICIALES.

        Parámetros:
            - config: Diccionario de configuración o ruta a archivo JSON
            - result: Variable donde guardar el resultado

        Flujo:
            1. Obtiene configuración y variables de Rocketbot
            2. Inicializa ExpedicionService
            3. Ejecuta procesar_oficiales()
            4. Retorna resumen de procesamiento
        """
        logger.info("[INICIO] Procesamiento de copias oficiales")
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            logger.info(f"Cargando configuración desde: {config_param}")
            config = load_config_from_param(config_param) if config_param else {}
            logger.info("Configuración cargada exitosamente")

            # Inicializar logger del módulo
            logger.info("Inicializando logger del módulo...")
            _inicializar_logger_modulo(config)
            logger.info("Logger del módulo inicializado")

            # Obtener variables de Rocketbot
            logger.info("Obteniendo variables de Rocketbot...")
            graph_client_secret = GetVar("graph_client_secret")  # type: ignore[name-defined]
            dynamics_client_secret = GetVar("dynamics_client_secret")  # type: ignore[name-defined]
            docuware_password = GetVar("docuware_password")  # type: ignore[name-defined]
            database_password = GetVar("database_password")  # type: ignore[name-defined]

            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")

            logger.info("Variables de Rocketbot obtenidas exitosamente")

            # Agregar secrets a la configuración (sin modificar estructura original del JSON)
            # Los secrets se obtienen de variables de Rocketbot y se agregan al config dict
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            # Asegurar que DocuWare existe antes de agregar password
            if "DocuWare" not in config:
                config["DocuWare"] = {}
            config["DocuWare"]["password"] = docuware_password
            # Database password es opcional
            if database_password:
                if "Database" not in config:
                    config["Database"] = {}
                config["Database"]["password"] = database_password

            # Import ExpedicionService with full typing support
            logger.info("Importando ExpedicionService...")
            ExpedicionServiceClass = _import_expedicion_service(expedicion_module_path)
            logger.info("Creando instancia de ExpedicionService...")
            service: ExpedicionService = ExpedicionServiceClass(config)  # type: ignore[assignment]
            logger.info("Ejecutando procesar_oficiales()...")
            resultado = service.procesar_oficiales()

            casos_procesados = resultado.get('casos_procesados', 0)
            casos_error = resultado.get('casos_error', 0)
            reporte_path = resultado.get('reporte_path', 'N/A')
            
            logger.info(f"[FIN] Procesamiento completado: {casos_procesados} casos procesados, {casos_error} errores")
            logger.info(f"[FIN] Reporte generado en: {reporte_path}")
            
            # Obtener IDs de casos procesados y con error para el resumen
            casos_procesados_ids = []
            casos_error_ids = []
            if hasattr(service, 'casos_procesados'):
                for item in service.casos_procesados:
                    caso = item.get('caso', {})
                    case_id = caso.get('sp_documentoid', 'N/A')
                    casos_procesados_ids.append(case_id)
            if hasattr(service, 'casos_error'):
                for item in service.casos_error:
                    caso = item.get('caso', {})
                    case_id = caso.get('sp_documentoid', 'N/A')
                    casos_error_ids.append(case_id)
            
            if casos_procesados_ids:
                logger.info(f"[FIN] Casos procesados exitosamente (IDs): {', '.join(casos_procesados_ids)}")
            if casos_error_ids:
                logger.warning(f"[FIN] Casos con error (IDs): {', '.join(casos_error_ids)}")

            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error al procesar copias oficiales: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg, "casos_procesados": 0, "casos_error": 0}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e

    elif module == "health":
        """
        Verifica el estado de conexión con CRM, DocuWare, Graph API y Base de Datos.

        Parámetros:
            - config: Diccionario de configuración o ruta a archivo JSON
            - result: Variable donde guardar el resultado
        """
        logger.info("[INICIO] Health check")
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}

            # Inicializar logger del módulo
            _inicializar_logger_modulo(config)

            # Obtener variables de Rocketbot
            graph_client_secret = GetVar("graph_client_secret")  # type: ignore[name-defined]
            dynamics_client_secret = GetVar("dynamics_client_secret")  # type: ignore[name-defined]
            docuware_password = GetVar("docuware_password")  # type: ignore[name-defined]
            database_password = GetVar("database_password")  # type: ignore[name-defined]

            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")

            # Agregar secrets a la configuración (sin modificar estructura original del JSON)
            # Los secrets se obtienen de variables de Rocketbot y se agregan al config dict
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            # Asegurar que DocuWare existe antes de agregar password
            if "DocuWare" not in config:
                config["DocuWare"] = {}
            config["DocuWare"]["password"] = docuware_password
            # Database password es opcional
            if database_password:
                if "Database" not in config:
                    config["Database"] = {}
                config["Database"]["password"] = database_password

            resultado = {
                "crm": {"status": "unknown", "message": ""},
                "docuware": {"status": "unknown", "message": ""},
                "graph": {"status": "unknown", "message": ""},
                "database": {"status": "stub", "message": "Auditoría no implementada"}
            }

            # Verificar conexión con Dynamics 365 CRM
            try:
                from ExpedicionCopias.core.auth import Dynamics365Authenticator
                from ExpedicionCopias.core.crm_client import CRMClient

                dynamics_config = config.get("Dynamics365", {})
                dynamics_client_secret = config.get("dynamics_client_secret", "")
                if not dynamics_client_secret:
                    raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
                auth = Dynamics365Authenticator(
                    tenant_id=dynamics_config.get("tenant_id", ""),
                    client_id=dynamics_config.get("client_id", ""),
                    client_secret=dynamics_client_secret
                )
                crm = CRMClient(auth, dynamics_config.get("base_url", ""))
                crm.get("/sp_documentos?$top=1")
                resultado["crm"] = {"status": "ok", "message": "Conexión exitosa"}
            except Exception as e:
                resultado["crm"] = {"status": "error", "message": str(e)}

            # Verificar conexión con DocuWare
            try:
                from ExpedicionCopias.core.docuware_client import DocuWareClient
                from ExpedicionCopias.core.rules_engine import ExcepcionesValidator

                rules_validator = ExcepcionesValidator([])
                docuware = DocuWareClient(config, rules_validator)
                docuware.autenticar()
                resultado["docuware"] = {"status": "ok", "message": "Autenticación exitosa"}
            except Exception as e:
                resultado["docuware"] = {"status": "error", "message": str(e)}

            # Verificar conexión con Microsoft Graph API
            try:
                from ExpedicionCopias.core.auth import AzureAuthenticator
                from ExpedicionCopias.core.graph_client import GraphClient

                graph_config = config.get("GraphAPI", {})
                graph_client_secret = config.get("graph_client_secret", "")
                if not graph_client_secret:
                    raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
                auth = AzureAuthenticator(
                    tenant_id=graph_config.get("tenant_id", ""),
                    client_id=graph_config.get("client_id", ""),
                    client_secret=graph_client_secret
                )
                graph = GraphClient(auth)
                graph.get("/users?$top=1")
                resultado["graph"] = {"status": "ok", "message": "Conexión exitosa"}
            except Exception as e:
                resultado["graph"] = {"status": "error", "message": str(e)}

            logger.info(f"[FIN] Health check completado")
            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error en health check: {str(e)}"
            logger.error(f"[ERROR] {error_msg}", exc_info=True)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e

except Exception as e:
    logger.error(f"Error en módulo ExpedicionCopias: {e}", exc_info=True)
    PrintException()
    raise e
