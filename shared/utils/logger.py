# coding: utf-8
"""
Sistema de logging centralizado.
Proporciona configuración estándar para todos los módulos.
Configura los loggers para escribir en archivos CSV según la configuración proporcionada.
Si no se proporciona configuración, usa valores por defecto basados en base_path.
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import os

# Exportar funciones públicas
__all__ = [
    'setup_logger',
    'get_logger',
    'configurar_loggers',
    'establecer_configuracion_global'
]

# Variable global para caché de base_path
_base_path_cache: Optional[str] = None

# Configuración global de logs (se establece cuando se inicializa el logger del módulo)
_logs_config_global: Optional[Dict[str, Any]] = None
_ruta_base_global: Optional[str] = None

# Valores por defecto para logs (rutas relativas desde base_path)
_DEFAULT_LOG_CONFIG = {
    "RutaLogAuditoria": "Logs/Logs Auditoria",
    "NombreLogAuditoria": "_LOG_DE_AUDITORIA_YYYYMMDD.csv",
    "RutaLogSistema": "Logs/Logs Sistema",
    "NombreLogSistema": "_LOG_DE_ERRORES_YYYYMMDD.csv"
}


def _obtener_ruta_base_proyecto() -> str:
    """
    Obtiene la ruta base del proyecto desde tmp_global_obj o calcula desde el archivo actual.
    Usa caché para evitar cálculos repetidos.
    
    Returns:
        Ruta base del proyecto con separador al final
    """
    global _base_path_cache
    
    if _base_path_cache is not None:
        return _base_path_cache
    
    try:
        tmp_global_obj  # type: ignore[name-defined]
        base_path = tmp_global_obj["basepath"]
        if base_path:
            _base_path_cache = base_path if base_path.endswith(os.sep) else base_path + os.sep
            return _base_path_cache
    except NameError:
        pass
    
    # Si no existe tmp_global_obj, calcular desde la ubicación del archivo
    # shared/utils/logger.py -> shared/utils/ -> shared/ -> raíz del proyecto
    current_file = os.path.abspath(__file__)
    # Subir 3 niveles: shared/utils/logger.py -> shared/utils/ -> shared/ -> raíz
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    _base_path_cache = base_path + os.sep
    return _base_path_cache


def _reemplazar_fecha_en_nombre(nombre: str) -> str:
    """
    Reemplaza YYYYMMDD en el nombre del archivo con la fecha actual.
    
    Args:
        nombre: Nombre del archivo que puede contener YYYYMMDD
        
    Returns:
        Nombre con la fecha reemplazada
    """
    fecha_actual = datetime.now().strftime("%Y%m%d")
    return nombre.replace("YYYYMMDD", fecha_actual)


def _construir_ruta_log(ruta_relativa: str, nombre_archivo: str, ruta_base: Optional[str] = None) -> str:
    """
    Construye la ruta completa del archivo de log.
    
    Args:
        ruta_relativa: Ruta relativa desde base_path (ej: "Logs/Logs Sistema" o "/Logs/Logs Sistema")
        nombre_archivo: Nombre del archivo (puede contener YYYYMMDD)
        ruta_base: Ruta base del proyecto (opcional, usa base_path calculado si no se proporciona)
        
    Returns:
        Ruta completa del archivo de log normalizada
    """
    # Obtener ruta base del proyecto
    if ruta_base is None:
        ruta_base = _obtener_ruta_base_proyecto()
    elif not ruta_base.endswith(os.sep):
        ruta_base = ruta_base + os.sep
    
    # Limpiar ruta relativa (remover / inicial si existe)
    ruta_relativa = ruta_relativa.lstrip("/\\")
    
    # Reemplazar fecha en nombre
    nombre_archivo = _reemplazar_fecha_en_nombre(nombre_archivo)
    
    # Construir y normalizar ruta completa
    ruta_completa = os.path.normpath(os.path.join(ruta_base, ruta_relativa, nombre_archivo))
    
    return ruta_completa


def _normalizar_logs_config(logs_config: Optional[Dict[str, Any]], ruta_base: Optional[str] = None) -> Dict[str, Any]:
    """
    Normaliza la configuración de logs al formato esperado.
    Acepta formato normalizado o formato con estructura de Logs.
    Si no se proporciona o está incompleta, usa valores por defecto basados en base_path.
    
    Args:
        logs_config: Configuración de logs que puede estar en formato:
            - Normalizado: {"auditoria": {"ruta": "...", "nombre": "..."}, "sistema": {...}}
            - Con estructura Logs: {"Logs": {"RutaLogAuditoria": "...", "NombreLogAuditoria": "...", ...}, "Globales": {"RutaBaseProyecto": "..."}}
            - None: se usará configuración por defecto basada en base_path
        ruta_base: Ruta base del proyecto (opcional, usa base_path calculado si no se proporciona)
    
    Returns:
        Diccionario normalizado con estructura:
            {
                "auditoria": {"ruta": "...", "nombre": "..."},
                "sistema": {"ruta": "...", "nombre": "..."}
            }
    """
    # Si no se proporciona, usar configuración por defecto
    if logs_config is None:
        return _obtener_configuracion_logs_con_fallback(ruta_base)
    
    # Si ya está en formato normalizado, validar y retornar
    if "auditoria" in logs_config or "sistema" in logs_config:
        # Validar que tenga la estructura correcta
        resultado = {
            "auditoria": logs_config.get("auditoria", {}),
            "sistema": logs_config.get("sistema", {})
        }
        # Debug: Log para verificar qué se está normalizando
        try:
            import logging as logging_module
            debug_logger = logging_module.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging_module.StreamHandler())
            debug_logger.info(f"[DEBUG _normalizar_logs_config] logs_config ya normalizado detectado")
            debug_logger.info(f"[DEBUG _normalizar_logs_config] resultado auditoria: {resultado.get('auditoria')}")
            debug_logger.info(f"[DEBUG _normalizar_logs_config] resultado sistema: {resultado.get('sistema')}")
        except Exception:
            pass
        # Si falta alguno, completar con valores por defecto
        if not resultado["auditoria"] or not resultado["sistema"]:
            default_config = _obtener_configuracion_logs_con_fallback(ruta_base)
            if not resultado["auditoria"]:
                resultado["auditoria"] = default_config["auditoria"]
            if not resultado["sistema"]:
                resultado["sistema"] = default_config["sistema"]
        return resultado
    
    # Si está en formato con estructura Logs, normalizarlo
    if "Logs" in logs_config:
        logs_config_raw = logs_config["Logs"]
        
        # Obtener ruta base del proyecto (prioridad: parámetro > Globales > base_path calculado)
        if ruta_base is None and "Globales" in logs_config and "RutaBaseProyecto" in logs_config["Globales"]:
            ruta_base = logs_config["Globales"]["RutaBaseProyecto"]
        
        # Si logs_config_raw está vacío o es None, usar valores por defecto
        if not logs_config_raw or not isinstance(logs_config_raw, dict):
            # Usar valores por defecto completamente
            return _obtener_configuracion_logs_con_fallback(ruta_base)
        
        # Usar valores por defecto para campos faltantes
        ruta_auditoria = logs_config_raw.get("RutaLogAuditoria") or _DEFAULT_LOG_CONFIG["RutaLogAuditoria"]
        nombre_auditoria = logs_config_raw.get("NombreLogAuditoria") or _DEFAULT_LOG_CONFIG["NombreLogAuditoria"]
        ruta_sistema = logs_config_raw.get("RutaLogSistema") or _DEFAULT_LOG_CONFIG["RutaLogSistema"]
        nombre_sistema = logs_config_raw.get("NombreLogSistema") or _DEFAULT_LOG_CONFIG["NombreLogSistema"]
        
        # Construir rutas completas
        ruta_auditoria_completa = _construir_ruta_log(ruta_auditoria, nombre_auditoria, ruta_base)
        ruta_sistema_completa = _construir_ruta_log(ruta_sistema, nombre_sistema, ruta_base)
        
        return {
            "auditoria": {
                "ruta": os.path.dirname(ruta_auditoria_completa),
                "nombre": os.path.basename(ruta_auditoria_completa)
            },
            "sistema": {
                "ruta": os.path.dirname(ruta_sistema_completa),
                "nombre": os.path.basename(ruta_sistema_completa)
            }
        }
    
    # Si no coincide con ningún formato conocido, usar valores por defecto
    return _obtener_configuracion_logs_con_fallback(ruta_base)


def _obtener_configuracion_logs_con_fallback(ruta_base: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración de logs usando valores por defecto basados en base_path.
    Siempre retorna una configuración válida.
    
    Args:
        ruta_base: Ruta base del proyecto (opcional, usa base_path calculado si no se proporciona)
    
    Returns:
        Diccionario normalizado con estructura:
            {
                "auditoria": {"ruta": "...", "nombre": "..."},
                "sistema": {"ruta": "...", "nombre": "..."}
            }
    """
    # Usar valores por defecto
    ruta_auditoria = _DEFAULT_LOG_CONFIG["RutaLogAuditoria"]
    nombre_auditoria = _DEFAULT_LOG_CONFIG["NombreLogAuditoria"]
    ruta_sistema = _DEFAULT_LOG_CONFIG["RutaLogSistema"]
    nombre_sistema = _DEFAULT_LOG_CONFIG["NombreLogSistema"]
    
    # Construir rutas completas usando base_path
    ruta_auditoria_completa = _construir_ruta_log(ruta_auditoria, nombre_auditoria, ruta_base)
    ruta_sistema_completa = _construir_ruta_log(ruta_sistema, nombre_sistema, ruta_base)
    
    return {
        "auditoria": {
            "ruta": os.path.dirname(ruta_auditoria_completa),
            "nombre": os.path.basename(ruta_auditoria_completa)
        },
        "sistema": {
            "ruta": os.path.dirname(ruta_sistema_completa),
            "nombre": os.path.basename(ruta_sistema_completa)
        }
    }


def _agregar_handler_archivo(logger: logging.Logger, log_file: str, level: int, formatter: logging.Formatter) -> None:
    """
    Agrega un handler de archivo a un logger si no existe ya.
    
    Args:
        logger: Logger al que agregar el handler
        log_file: Ruta completa del archivo de log
        level: Nivel mínimo de logging
        formatter: Formateador para los mensajes
    """
    # Debug: Log para verificar qué archivo se está intentando agregar
    try:
        debug_logger = logging.getLogger("LoggerDebug")
        if not debug_logger.handlers:
            debug_logger.addHandler(logging.StreamHandler())
        debug_logger.info(f"[DEBUG _agregar_handler_archivo] Intentando agregar handler para: {log_file}")
    except Exception:
        pass
    
    # Crear directorio si no existe
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        try:
            debug_logger = logging.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging.StreamHandler())
            debug_logger.info(f"[DEBUG _agregar_handler_archivo] Directorio creado: {log_dir}")
        except Exception:
            pass
    
    # Verificar si el logger ya tiene un handler para este archivo
    log_file_abs = os.path.abspath(log_file)
    tiene_handler = any(
        isinstance(h, logging.FileHandler) and
        hasattr(h, 'baseFilename') and
        os.path.abspath(h.baseFilename) == log_file_abs
        for h in logger.handlers
    )
    
    if not tiene_handler:
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        try:
            debug_logger = logging.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging.StreamHandler())
            debug_logger.info(f"[DEBUG _agregar_handler_archivo] Handler agregado exitosamente para: {log_file}")
            debug_logger.info(f"[DEBUG _agregar_handler_archivo] Total handlers en logger: {len(logger.handlers)}")
        except Exception:
            pass
    else:
        try:
            debug_logger = logging.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging.StreamHandler())
            debug_logger.info(f"[DEBUG _agregar_handler_archivo] Handler ya existe para: {log_file}")
        except Exception:
            pass


def _configurar_handlers_automaticos(logger: logging.Logger, logs_config: Optional[Dict[str, Any]] = None, ruta_base: Optional[str] = None) -> None:
    """
    Configura automáticamente los handlers de archivo para un logger.
    Si se proporciona logs_config, usa esa configuración; si no, usa configuración global o valores por defecto basados en base_path.
    Cada logger puede tener sus propios handlers para los mismos archivos.
    
    Args:
        logger: Logger a configurar
        logs_config: Configuración de logs opcional. Si se proporciona, debe tener estructura:
            {
                "auditoria": {"ruta": "...", "nombre": "..."},
                "sistema": {"ruta": "...", "nombre": "..."}
            }
            O formato con estructura Logs: {"Logs": {...}, "Globales": {"RutaBaseProyecto": "..."}}
            Si no se proporciona, usa configuración global o valores por defecto basados en base_path
        ruta_base: Ruta base del proyecto (opcional, usa configuración global o base_path calculado si no se proporciona)
    """
    global _logs_config_global, _ruta_base_global
    
    # Si no se proporciona configuración explícita, usar configuración global si existe
    if logs_config is None and _logs_config_global is not None:
        logs_config = _logs_config_global
    if ruta_base is None and _ruta_base_global is not None:
        ruta_base = _ruta_base_global
    
    # Normalizar configuración (siempre retorna una configuración válida)
    logs_config_normalizado = _normalizar_logs_config(logs_config, ruta_base)
    
    # Debug: Log para verificar qué se está usando
    try:
        debug_logger = logging.getLogger("LoggerDebug")
        if not debug_logger.handlers:
            debug_logger.addHandler(logging.StreamHandler())
        debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] logs_config recibido: {logs_config}")
        debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] logs_config_normalizado: {logs_config_normalizado}")
        if logs_config_normalizado.get("auditoria"):
            debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] auditoria ruta: {logs_config_normalizado['auditoria'].get('ruta')}, nombre: {logs_config_normalizado['auditoria'].get('nombre')}")
        if logs_config_normalizado.get("sistema"):
            debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] sistema ruta: {logs_config_normalizado['sistema'].get('ruta')}, nombre: {logs_config_normalizado['sistema'].get('nombre')}")
    except Exception:
        pass
    
    # Formato estándar para logs CSV
    formatter = logging.Formatter(
        '%(asctime)s,%(name)s,%(levelname)s,%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configurar handler de auditoría (todos los niveles: DEBUG y superior)
    if logs_config_normalizado.get("auditoria"):
        auditoria = logs_config_normalizado["auditoria"]
        log_file = os.path.join(auditoria["ruta"], auditoria["nombre"])
        try:
            debug_logger = logging.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging.StreamHandler())
            debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] Agregando handler auditoria: {log_file}")
        except Exception:
            pass
        # Usar DEBUG como nivel mínimo para capturar todos los logs
        _agregar_handler_archivo(logger, log_file, logging.DEBUG, formatter)
    
    # Configurar handler de sistema (todos los niveles: DEBUG y superior)
    if logs_config_normalizado.get("sistema"):
        sistema = logs_config_normalizado["sistema"]
        log_file = os.path.join(sistema["ruta"], sistema["nombre"])
        try:
            debug_logger = logging.getLogger("LoggerDebug")
            if not debug_logger.handlers:
                debug_logger.addHandler(logging.StreamHandler())
            debug_logger.info(f"[DEBUG _configurar_handlers_automaticos] Agregando handler sistema: {log_file}")
        except Exception:
            pass
        # Usar DEBUG como nivel mínimo para capturar todos los logs
        _agregar_handler_archivo(logger, log_file, logging.DEBUG, formatter)


def setup_logger(name: str, level: int = logging.INFO, 
                 log_file: Optional[str] = None,
                 logs_config: Optional[Dict[str, Any]] = None,
                 ruta_base: Optional[str] = None) -> logging.Logger:
    """
    Configura un logger con formato estándar.
    Automáticamente configura handlers de archivo según la configuración proporcionada
    o usa valores por defecto basados en base_path si no se proporciona.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (default: INFO)
        log_file: Ruta opcional para archivo de log adicional (se agrega además de los automáticos)
        logs_config: Configuración de logs opcional. Si se proporciona, debe tener estructura:
            {
                "auditoria": {"ruta": "...", "nombre": "..."},
                "sistema": {"ruta": "...", "nombre": "..."}
            }
            O puede ser un dict con estructura de Logs:
            {
                "Logs": {
                    "RutaLogAuditoria": "...",
                    "NombreLogAuditoria": "...",
                    "RutaLogSistema": "...",
                    "NombreLogSistema": "..."
                },
                "Globales": {
                    "RutaBaseProyecto": "..."  # Opcional
                }
            }
            Si no se proporciona, usa valores por defecto basados en base_path
        ruta_base: Ruta base del proyecto (opcional, usa base_path calculado si no se proporciona)
    
    Returns:
        Logger configurado
    
    Example:
        logger = setup_logger("EmailModule")
        logger.info("Procesando correos...")
        
        # Con configuración personalizada
        logs_config = {
            "auditoria": {"ruta": "/custom/logs", "nombre": "audit.csv"},
            "sistema": {"ruta": "/custom/logs", "nombre": "errors.csv"}
        }
        logger = setup_logger("EmailModule", logs_config=logs_config)
    """
    logger = logging.getLogger(name)
    # Usar DEBUG como nivel mínimo para capturar TODOS los logs
    logger.setLevel(logging.DEBUG)
    
    # Debug: Log para verificar qué handlers tiene el logger antes de configurar
    try:
        debug_logger = logging.getLogger("LoggerDebug")
        if not debug_logger.handlers:
            debug_logger.addHandler(logging.StreamHandler())
        debug_logger.info(f"[DEBUG setup_logger] Logger '{name}' - handlers antes de configurar: {len(logger.handlers)}")
        for i, h in enumerate(logger.handlers):
            debug_logger.info(f"[DEBUG setup_logger] Handler {i}: {type(h).__name__}, level: {h.level}")
            if isinstance(h, logging.FileHandler) and hasattr(h, 'baseFilename'):
                debug_logger.info(f"[DEBUG setup_logger] Handler {i} archivo: {h.baseFilename}")
    except Exception:
        pass
    
    # Siempre limpiar handlers de archivo existentes para reconfigurar
    # Esto asegura que se usen las rutas correctas y que ambos archivos reciban todos los logs
    # IMPORTANTE: Siempre remover y reconfigurar para asegurar que ambos archivos tengan todos los logs
    handlers_a_remover = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    for handler in handlers_a_remover:
        # Cerrar el handler para asegurar que se escriban todos los logs pendientes
        handler.flush()
        handler.close()
        logger.removeHandler(handler)
    try:
        debug_logger = logging.getLogger("LoggerDebug")
        if not debug_logger.handlers:
            debug_logger.addHandler(logging.StreamHandler())
        debug_logger.info(f"[DEBUG setup_logger] Removidos {len(handlers_a_remover)} FileHandlers existentes para reconfigurar")
    except Exception:
        pass
    
    # Evitar duplicar handlers básicos (consola)
    tiene_consola = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    
    # Formato estándar para consola
    formatter_consola = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola (solo si no tiene uno)
    # Usar DEBUG como nivel mínimo para capturar todos los logs
    if not tiene_consola:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter_consola)
        logger.addHandler(console_handler)
    
    # Configurar handlers automáticos (normaliza internamente)
    # Esto agregará los handlers de archivo según la configuración proporcionada
    _configurar_handlers_automaticos(logger, logs_config, ruta_base)
    
    # Debug: Log para verificar qué handlers tiene el logger después de configurar
    try:
        debug_logger = logging.getLogger("LoggerDebug")
        if not debug_logger.handlers:
            debug_logger.addHandler(logging.StreamHandler())
        debug_logger.info(f"[DEBUG setup_logger] Logger '{name}' - handlers después de configurar: {len(logger.handlers)}")
        for i, h in enumerate(logger.handlers):
            debug_logger.info(f"[DEBUG setup_logger] Handler {i}: {type(h).__name__}, level: {h.level}")
            if isinstance(h, logging.FileHandler) and hasattr(h, 'baseFilename'):
                debug_logger.info(f"[DEBUG setup_logger] Handler {i} archivo: {h.baseFilename}")
    except Exception:
        pass
    
    # Handler para archivo adicional (opcional, si se proporciona)
    if log_file:
        # Verificar si ya tiene este handler
        tiene_handler_archivo = any(
            isinstance(h, logging.FileHandler) and
            hasattr(h, 'baseFilename') and
            os.path.abspath(h.baseFilename) == os.path.abspath(log_file)
            for h in logger.handlers
        )
        
        if not tiene_handler_archivo:
            # Crear directorio si no existe
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            # El handler debe tener nivel DEBUG para capturar todos los mensajes del nivel configurado
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter_consola)  # Usar formato de consola para archivos adicionales
            logger.addHandler(file_handler)
    
    return logger


def establecer_configuracion_global(logs_config: Optional[Dict[str, Any]], ruta_base: Optional[str] = None) -> None:
    """
    Establece la configuración global de logs para que todos los loggers la usen automáticamente.
    Esta función debe llamarse una vez al inicio del módulo cuando se recibe la configuración.
    
    Args:
        logs_config: Configuración de logs en formato normalizado o con estructura Logs
        ruta_base: Ruta base del proyecto
    """
    global _logs_config_global, _ruta_base_global
    _logs_config_global = logs_config
    _ruta_base_global = ruta_base

# Alias para compatibilidad (mantener nombre privado también disponible)
_establecer_configuracion_global = establecer_configuracion_global


def get_logger(name: str, logs_config: Optional[Dict[str, Any]] = None, ruta_base: Optional[str] = None) -> logging.Logger:
    """
    Obtiene un logger existente o crea uno nuevo.
    Automáticamente configura handlers de archivo según la configuración proporcionada
    o usa valores por defecto basados en base_path si no se proporciona.
    
    Si no se proporciona logs_config ni ruta_base, intenta usar la configuración global
    establecida por _inicializar_logger_modulo().
    
    IMPORTANTE: Si no hay configuración global ni explícita, NO configura handlers automáticamente
    para evitar escribir en archivos de fallback antes de la configuración correcta.
    
    Args:
        name: Nombre del logger
        logs_config: Configuración de logs opcional. Si se proporciona, debe tener estructura:
            {
                "auditoria": {"ruta": "...", "nombre": "..."},
                "sistema": {"ruta": "...", "nombre": "..."}
            }
            O puede ser un dict con estructura de Logs: {"Logs": {...}, "Globales": {"RutaBaseProyecto": "..."}}
            Si no se proporciona, usa configuración global o valores por defecto basados en base_path
        ruta_base: Ruta base del proyecto (opcional, usa configuración global o base_path calculado si no se proporciona)
    
    Returns:
        Logger configurado con handlers automáticos (solo si hay configuración disponible)
    
    Example:
        logger = get_logger("EmailModule")
        
        # Con configuración personalizada
        logs_config = {
            "auditoria": {"ruta": "/custom/logs", "nombre": "audit.csv"},
            "sistema": {"ruta": "/custom/logs", "nombre": "errors.csv"}
        }
        logger = get_logger("EmailModule", logs_config=logs_config)
    """
    global _logs_config_global, _ruta_base_global
    
    # Si no se proporciona configuración explícita, usar configuración global si existe
    if logs_config is None and _logs_config_global is not None:
        logs_config = _logs_config_global
    if ruta_base is None and _ruta_base_global is not None:
        ruta_base = _ruta_base_global
    
    logger = logging.getLogger(name)
    
    # Siempre configurar handlers (con configuración explícita, global, o por defecto)
    # Esto asegura que todos los logs se capturen desde el inicio
    if not logger.handlers:
        return setup_logger(name, logs_config=logs_config, ruta_base=ruta_base)
    else:
        # Si ya tiene handlers, asegurar que tenga los handlers automáticos con la configuración actual
        _configurar_handlers_automaticos(logger, logs_config, ruta_base)
    
    return logger


def configurar_loggers(config_dict: Optional[Dict[str, Any]] = None, module_name: str = "Module", 
                       main_logger_name: Optional[str] = None, ruta_base: Optional[str] = None) -> Dict[str, logging.Logger]:
    """
    Configura los loggers de auditoría y sistema basándose en la configuración proporcionada.
    Si no se proporciona config_dict, usa valores por defecto basados en base_path.
    Crea archivos físicos de log en las rutas especificadas.
    Función genérica y reutilizable para cualquier módulo.
    
    Args:
        config_dict: Diccionario con la configuración completa (opcional).
            Si se proporciona, debe incluir:
            - logs.auditoria.ruta: Ruta donde se guardarán los logs de auditoría
            - logs.auditoria.nombre: Nombre del archivo de log (puede incluir extensión)
            - logs.sistema.ruta: Ruta donde se guardarán los logs de sistema/errores
            - logs.sistema.nombre: Nombre del archivo de log (puede incluir extensión)
            O puede tener estructura: {"Logs": {...}, "Globales": {"RutaBaseProyecto": "..."}}
            Si no se proporciona, usa valores por defecto basados en base_path
        module_name: Nombre del módulo para identificar los loggers (ej: "Docuware", "Email")
        main_logger_name: Nombre del logger principal para mensajes informativos (opcional)
        ruta_base: Ruta base del proyecto (opcional, usa base_path calculado si no se proporciona)
    
    Returns:
        Diccionario con los loggers configurados:
            - auditoria: Logger de auditoría (nivel INFO)
            - sistema: Logger de sistema/errores (nivel ERROR)
    
    Example:
        loggers = configurar_loggers(config_dict, module_name="Docuware", main_logger_name="DocuwareMain")
        logger_auditoria = loggers.get("auditoria")
        logger_sistema = loggers.get("sistema")
        
        # O sin config_dict (usa valores por defecto)
        loggers = configurar_loggers(module_name="Email")
    """
    loggers = {}
    
    # Determinar el nombre del logger principal
    if main_logger_name is None:
        main_logger_name = f"{module_name}Main"
    
    try:
        # Obtener ruta_base desde config_dict si está disponible
        if ruta_base is None and config_dict is not None:
            if "Globales" in config_dict and "RutaBaseProyecto" in config_dict["Globales"]:
                ruta_base = config_dict["Globales"]["RutaBaseProyecto"]
        
        # Obtener configuración de logs (siempre retorna una configuración válida)
        if config_dict is None:
            logs_config = _obtener_configuracion_logs_con_fallback(ruta_base)
        else:
            logs_config = config_dict.get("logs", {})
            # Si no hay logs en config_dict, usar valores por defecto
            if not logs_config:
                logs_config = _obtener_configuracion_logs_con_fallback(ruta_base)
            else:
                # Normalizar la configuración proporcionada
                logs_config = _normalizar_logs_config(logs_config, ruta_base)
        
        # Configurar logger de auditoría
        auditoria_config = logs_config.get("auditoria", {})
        if auditoria_config.get("ruta") and auditoria_config.get("nombre"):
            ruta_auditoria = auditoria_config["ruta"]
            nombre_auditoria = auditoria_config["nombre"]
            # Construir ruta completa del archivo de log
            log_auditoria_file = os.path.join(ruta_auditoria, nombre_auditoria)
            # Configurar logger de auditoría (INFO y superior)
            logger_name_auditoria = f"{module_name}Auditoria"
            logger_auditoria = setup_logger(logger_name_auditoria, level=logging.INFO, log_file=log_auditoria_file)
            loggers["auditoria"] = logger_auditoria
            # Usar el logger principal para informar
            try:
                main_logger = logging.getLogger(main_logger_name)
                if not main_logger.handlers:
                    main_logger = get_logger(main_logger_name)
                main_logger.info(f"Logger de auditoría configurado: {log_auditoria_file}")
            except Exception:
                pass  # Si no se puede usar el logger principal, continuar
        
        # Configurar logger de sistema/errores
        sistema_config = logs_config.get("sistema", {})
        if sistema_config.get("ruta") and sistema_config.get("nombre"):
            ruta_sistema = sistema_config["ruta"]
            nombre_sistema = sistema_config["nombre"]
            # Construir ruta completa del archivo de log
            log_sistema_file = os.path.join(ruta_sistema, nombre_sistema)
            # Configurar logger de sistema (ERROR y superior)
            logger_name_sistema = f"{module_name}Sistema"
            logger_sistema = setup_logger(logger_name_sistema, level=logging.ERROR, log_file=log_sistema_file)
            loggers["sistema"] = logger_sistema
            # Usar el logger principal para informar
            try:
                main_logger = logging.getLogger(main_logger_name)
                if not main_logger.handlers:
                    main_logger = get_logger(main_logger_name)
                main_logger.info(f"Logger de sistema/errores configurado: {log_sistema_file}")
            except Exception:
                pass  # Si no se puede usar el logger principal, continuar
    except Exception as e:
        # Intentar usar el logger principal, si no existe crear uno básico
        try:
            main_logger = logging.getLogger(main_logger_name)
            if not main_logger.handlers:
                main_logger = get_logger(main_logger_name)
            main_logger.warning(f"No se pudieron configurar los loggers físicos: {e}")
        except Exception:
            print(f"Error al configurar loggers: {e}")
    
    return loggers

