# coding: utf-8
"""
Validaciones comunes reutilizables.
"""

import re
from datetime import datetime
from typing import Any, Optional


def validate_email(email: str) -> bool:
    """
    Valida si un email tiene formato válido.
    
    Args:
        email: Email a validar
    
    Returns:
        True si es válido, False en caso contrario
    
    Example:
        if validate_email("user@example.com"):
            print("Email válido")
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Valida si una URL tiene formato válido.
    
    Args:
        url: URL a validar
    
    Returns:
        True si es válido, False en caso contrario
    
    Example:
        if validate_url("https://example.com"):
            print("URL válida")
    """
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?$'
    return bool(re.match(pattern, url))


def validate_date(date_string: str, format_string: str = "%Y-%m-%d") -> bool:
    """
    Valida si una fecha tiene formato válido.
    
    Args:
        date_string: Fecha como string
        format_string: Formato esperado (default: "%Y-%m-%d")
    
    Returns:
        True si es válido, False en caso contrario
    
    Example:
        if validate_date("2024-01-15"):
            print("Fecha válida")
    """
    try:
        datetime.strptime(date_string, format_string)
        return True
    except ValueError:
        return False


def validate_not_empty(value: Any) -> bool:
    """
    Valida si un valor no está vacío.
    
    Args:
        value: Valor a validar
    
    Returns:
        True si no está vacío, False en caso contrario
    """
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict, tuple)):
        return len(value) > 0
    return True


def validate_numeric(value: Any) -> bool:
    """
    Valida si un valor es numérico.
    
    Args:
        value: Valor a validar
    
    Returns:
        True si es numérico, False en caso contrario
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

