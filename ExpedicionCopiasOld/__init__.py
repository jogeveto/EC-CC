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

from __future__ import annotations  # Makes all annotations strings - no runtime evaluation

import os
import sys
from typing import TYPE_CHECKING, cast

# Type imports for IDE support (only evaluated by type checkers, not at runtime)
# This provides type information to the IDE and type checkers
if TYPE_CHECKING:
    from services.expedicion_service import ExpedicionService

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
from shared.utils.logger import get_logger
from shared.utils.config_helper import load_config_from_param

# Logger del módulo
logger = get_logger("ExpedicionCopiasModule")


def _import_expedicion_service(module_path: str) -> type[ExpedicionService]:
    """
    Importa ExpedicionService con soporte completo para typing.
    
    Intenta importación normal primero (funciona en IDE/desarrollo y preserva typing),
    luego fallback a importlib (funciona en Rocketbot).
    
    El tipo de retorno referencia ExpedicionService (definido arriba con TYPE_CHECKING).
    Con `from __future__ import annotations`, esto es una string literal automáticamente.
    
    Args:
        module_path: Ruta base del módulo ExpedicionCopias
        
    Returns:
        Clase ExpedicionService - IDE reconocerá el tipo gracias a TYPE_CHECKING arriba
    """
    # Try 1: Normal import (works in IDE/development) - preserves full typing
    try:
        from services.expedicion_service import ExpedicionService
        return ExpedicionService  # type: ignore[return-value]
    except (ImportError, ModuleNotFoundError):
        pass
    
    # Try 2: Full module path import - also preserves typing
    try:
        from ExpedicionCopias.services.expedicion_service import ExpedicionService
        return ExpedicionService  # type: ignore[return-value]
    except (ImportError, ModuleNotFoundError):
        pass
    
    # Try 3: importlib fallback (works in Rocketbot)
    # Cast to preserve typing - TYPE_CHECKING import above provides type info for IDE
    import importlib.util
    expedicion_service_path = module_path + "services" + os.sep + "expedicion_service.py"
    spec = importlib.util.spec_from_file_location("expedicion_service", expedicion_service_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar expedicion_service desde {expedicion_service_path}")
    
    expedicion_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(expedicion_module)
    
    if not hasattr(expedicion_module, "ExpedicionService"):
        raise ImportError("ExpedicionService no encontrado en expedicion_service.py")
    
    # Cast preserves typing info - TYPE_CHECKING import provides the type definition
    return cast(type[ExpedicionService], expedicion_module.ExpedicionService)  # type: ignore[return-value, type-arg]


# Obtener el módulo que fue invocado
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
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}

            # Obtener variables de Rocketbot
            graph_client_secret = GetParams("graph_client_secret")
            dynamics_client_secret = GetParams("dynamics_client_secret")
            docuware_password = GetParams("docuware_password")
            database_password = GetParams("database_password")
            
            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")
            
            # Agregar secrets a la configuración
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            config.setdefault("DocuWare", {})["password"] = docuware_password
            if database_password:
                config.setdefault("Database", {})["password"] = database_password

            # Import ExpedicionService with full typing support
            # The helper function tries multiple import methods and preserves typing for IDE
            ExpedicionServiceClass = _import_expedicion_service(expedicion_module_path)
            # With 'from __future__ import annotations', this annotation becomes a string
            # The IDE will resolve ExpedicionService from the TYPE_CHECKING block above
            service: ExpedicionService = ExpedicionServiceClass(config, logger)  # type: ignore[assignment]
            resultado = service.procesar_particulares()

            logger.info(f"Procesamiento de copias completado: {resultado.get('casos_procesados', 0)} casos procesados, {resultado.get('casos_error', 0)} errores")

            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error al procesar copias: {str(e)}"
            logger.error(error_msg)
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
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}

            # Obtener variables de Rocketbot
            graph_client_secret = GetParams("graph_client_secret")
            dynamics_client_secret = GetParams("dynamics_client_secret")
            docuware_password = GetParams("docuware_password")
            database_password = GetParams("database_password")
            
            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")
            
            # Agregar secrets a la configuración
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            config.setdefault("DocuWare", {})["password"] = docuware_password
            if database_password:
                config.setdefault("Database", {})["password"] = database_password

            # Import ExpedicionService with full typing support
            # The helper function tries multiple import methods and preserves typing for IDE
            ExpedicionServiceClass = _import_expedicion_service(expedicion_module_path)
            # With 'from __future__ import annotations', this annotation becomes a string
            # The IDE will resolve ExpedicionService from the TYPE_CHECKING block above
            service: ExpedicionService = ExpedicionServiceClass(config, logger)  # type: ignore[assignment]
            resultado = service.procesar_oficiales()

            logger.info(f"Procesamiento de copias oficiales completado: {resultado.get('casos_procesados', 0)} casos procesados, {resultado.get('casos_error', 0)} errores")

            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error al procesar copias oficiales: {str(e)}"
            logger.error(error_msg)
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
        config_param = GetParams("config")
        result_var = GetParams("result")

        try:
            # Cargar configuración
            config = load_config_from_param(config_param) if config_param else {}

            # Obtener variables de Rocketbot
            graph_client_secret = GetParams("graph_client_secret")
            dynamics_client_secret = GetParams("dynamics_client_secret")
            docuware_password = GetParams("docuware_password")
            database_password = GetParams("database_password")
            
            if not graph_client_secret:
                raise ValueError("Variable de Rocketbot 'graph_client_secret' no está configurada")
            if not dynamics_client_secret:
                raise ValueError("Variable de Rocketbot 'dynamics_client_secret' no está configurada")
            if not docuware_password:
                raise ValueError("Variable de Rocketbot 'docuware_password' no está configurada")
            
            # Agregar secrets a la configuración
            config["graph_client_secret"] = graph_client_secret
            config["dynamics_client_secret"] = dynamics_client_secret
            config.setdefault("DocuWare", {})["password"] = docuware_password
            if database_password:
                config.setdefault("Database", {})["password"] = database_password

            resultado = {
                "crm": {"status": "unknown", "message": ""},
                "docuware": {"status": "unknown", "message": ""},
                "graph": {"status": "unknown", "message": ""},
                "database": {"status": "stub", "message": "Auditoría no implementada"}
            }
            
            # Verificar conexión con Dynamics 365 CRM
            try:
                from core.auth import Dynamics365Authenticator
                from core.crm_client import CRMClient
                
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
                from core.docuware_client import DocuWareClient
                from core.rules_engine import ExcepcionesValidator
                
                rules_validator = ExcepcionesValidator([])
                docuware = DocuWareClient(config, rules_validator)
                docuware.autenticar()
                resultado["docuware"] = {"status": "ok", "message": "Autenticación exitosa"}
            except Exception as e:
                resultado["docuware"] = {"status": "error", "message": str(e)}
            
            # Verificar conexión con Microsoft Graph API
            try:
                from core.auth import AzureAuthenticator
                from core.graph_client import GraphClient
                
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

            if result_var:
                SetVar(result_var, resultado)

        except Exception as e:
            error_msg = f"Error en health check: {str(e)}"
            logger.error(error_msg)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e

    elif module == "test_action":
        """
        Acción dummy para verificar que el módulo se carga correctamente en RocketBot.
        Esta acción puede ser eliminada después de verificar que el módulo funciona.
        
        Parámetros:
            - result (opcional): Variable donde guardar el resultado
        
        Retorna:
            Diccionario con mensaje de éxito
        """
        result_var = GetParams("result")
        
        try:
            resultado = {
                "status": "ok",
                "message": "Módulo ExpedicionCopias cargado correctamente",
                "module_name": "ExpedicionCopias",
                "actions_available": ["procesar_copias", "procesar_copias_oficiales", "health", "test_action"]
            }
            
            if result_var:
                SetVar(result_var, resultado)
            
            logger.info("Test Action: Módulo ExpedicionCopias cargado correctamente")
            
        except Exception as e:
            error_msg = f"Error en test_action: {str(e)}"
            logger.error(error_msg)
            resultado = {"status": "error", "message": error_msg}
            if result_var:
                SetVar(result_var, resultado)
            PrintException()
            raise e

except Exception as e:
    logger.error(f"Error en módulo ExpedicionCopias: {e}")
    PrintException()
    raise e
