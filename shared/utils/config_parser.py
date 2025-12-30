# coding: utf-8
"""
Utilidades para parsear y validar configuraciones.
"""

import json
from typing import Any, Dict, Optional, Union
from shared.utils.logger import get_logger

logger = get_logger("ConfigParser")


def parse_config(config: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parsea una configuración que puede ser string JSON o diccionario.
    
    Args:
        config: Configuración como string JSON o diccionario
    
    Returns:
        Diccionario con la configuración parseada
    
    Example:
        config = parse_config('{"key": "value"}')
        config = parse_config({"key": "value"})
    """
    if isinstance(config, dict):
        return config
    
    if isinstance(config, str):
        try:
            return json.loads(config)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}, configuración: {config}")
            raise ValueError(f"Configuración JSON inválida: {e}, configuración: {config}")
    
    raise TypeError(f"Tipo de configuración no soportado: {type(config)}")


def get_config_value(config: Union[str, Dict[str, Any]], key: str, 
                    default: Any = None) -> Any:
    """
    Obtiene un valor de configuración de forma segura.
    
    Args:
        config: Configuración como string JSON o diccionario
        key: Clave a buscar
        default: Valor por defecto si no se encuentra
    
    Returns:
        Valor encontrado o valor por defecto
    """
    try:
        parsed_config = parse_config(config)
        return parsed_config.get(key, default)
    except Exception as e:
        logger.warning(f"Error al obtener valor de configuración: {e}")
        return default


def validate_required_keys(config: Union[str, Dict[str, Any]], 
                          required_keys: list) -> bool:
    """
    Valida que una configuración tenga todas las claves requeridas.
    
    Args:
        config: Configuración como string JSON o diccionario
        required_keys: Lista de claves requeridas
    
    Returns:
        True si todas las claves están presentes, False en caso contrario
    """
    try:
        parsed_config = parse_config(config)
        missing_keys = [key for key in required_keys if key not in parsed_config]
        
        if missing_keys:
            logger.error(f"Claves faltantes en configuración: {missing_keys}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error al validar configuración: {e}")
        return False


def merge_configs(*configs: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combina múltiples configuraciones, las últimas tienen prioridad.
    
    Args:
        *configs: Configuraciones a combinar
    
    Returns:
        Diccionario con configuraciones combinadas
    """
    merged = {}
    
    for config in configs:
        try:
            parsed = parse_config(config)
            merged.update(parsed)
        except Exception as e:
            logger.warning(f"Error al combinar configuración: {e}")
            continue
    
    return merged

