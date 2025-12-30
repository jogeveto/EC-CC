# coding: utf-8
"""
Funciones auxiliares reutilizables.
"""

from datetime import datetime
from typing import Any, Optional, Dict, List


def format_date(date: datetime, format_string: str = "%Y-%m-%d") -> str:
    """
    Formatea una fecha a string.
    
    Args:
        date: Objeto datetime
        format_string: Formato deseado (default: "%Y-%m-%d")
    
    Returns:
        Fecha formateada como string
    
    Example:
        formatted = format_date(datetime.now(), "%Y-%m-%d %H:%M:%S")
    """
    return date.strftime(format_string)


def format_datetime(dt: datetime) -> str:
    """
    Formatea un datetime a string estándar.
    
    Args:
        dt: Objeto datetime
    
    Returns:
        Datetime formateado como "YYYY-MM-DD HH:MM:SS"
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Obtiene un valor de un diccionario de forma segura.
    
    Args:
        data: Diccionario
        key: Clave a buscar
        default: Valor por defecto si no existe
    
    Returns:
        Valor encontrado o default
    
    Example:
        value = safe_get(my_dict, "key", "default_value")
    """
    return data.get(key, default)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Divide una lista en chunks de tamaño especificado.
    
    Args:
        lst: Lista a dividir
        chunk_size: Tamaño de cada chunk
    
    Returns:
        Lista de chunks
    
    Example:
        chunks = chunk_list([1, 2, 3, 4, 5], 2)  # [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def clean_string(text: str) -> str:
    """
    Limpia un string eliminando espacios extra y caracteres especiales.
    
    Args:
        text: String a limpiar
    
    Returns:
        String limpio
    """
    return ' '.join(text.split())


def parse_bool(value: Any) -> bool:
    """
    Convierte un valor a booleano de forma segura.
    
    Args:
        value: Valor a convertir
    
    Returns:
        Valor booleano
    
    Example:
        bool_val = parse_bool("true")  # True
        bool_val = parse_bool("false")  # False
        bool_val = parse_bool(1)  # True
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'si', 'sí')
    return bool(value)

