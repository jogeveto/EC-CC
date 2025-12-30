# coding: utf-8
"""
Utilidades para manejo de archivos y descargas.
"""

import os
import shutil
from typing import List, Optional
from pathlib import Path
from shared.utils.logger import get_logger

logger = get_logger("FileHelpers")


def ensure_directory(path: str) -> str:
    """
    Asegura que un directorio exista, creándolo si es necesario.
    
    Args:
        path: Ruta del directorio
    
    Returns:
        Ruta del directorio (normalizada)
    """
    try:
        normalized_path = os.path.normpath(path)
        if not os.path.exists(normalized_path):
            os.makedirs(normalized_path)
            logger.info(f"Directorio creado: {normalized_path}")
        return normalized_path
    except Exception as e:
        logger.error(f"Error al crear directorio: {e}")
        raise


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitiza un nombre de archivo removiendo caracteres inválidos.
    
    Args:
        filename: Nombre de archivo original
        max_length: Longitud máxima del nombre
    
    Returns:
        Nombre de archivo sanitizado
    """
    # Caracteres inválidos en nombres de archivo
    invalid_chars = '<>:"/\\|?*'
    
    # Reemplazar caracteres inválidos
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limitar longitud
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def get_file_size(filepath: str) -> Optional[int]:
    """
    Obtiene el tamaño de un archivo en bytes.
    
    Args:
        filepath: Ruta del archivo
    
    Returns:
        Tamaño en bytes o None si hay error
    """
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        logger.warning(f"Error al obtener tamaño de archivo: {e}")
        return None


def file_exists(filepath: str) -> bool:
    """
    Verifica si un archivo existe.
    
    Args:
        filepath: Ruta del archivo
    
    Returns:
        True si existe, False en caso contrario
    """
    return os.path.isfile(filepath)


def list_files(directory: str, pattern: Optional[str] = None) -> List[str]:
    """
    Lista archivos en un directorio.
    
    Args:
        directory: Directorio donde buscar
        pattern: Patrón opcional para filtrar (ej: "*.pdf")
    
    Returns:
        Lista de rutas de archivos
    """
    try:
        if not os.path.exists(directory):
            return []
        
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                if pattern:
                    if item.endswith(pattern.replace('*', '')):
                        files.append(item_path)
                else:
                    files.append(item_path)
        
        return files
    except Exception as e:
        logger.error(f"Error al listar archivos: {e}")
        return []


def delete_file(filepath: str) -> bool:
    """
    Elimina un archivo de forma segura.
    
    Args:
        filepath: Ruta del archivo a eliminar
    
    Returns:
        True si se eliminó, False en caso contrario
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Archivo eliminado: {filepath}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error al eliminar archivo: {e}")
        return False


def copy_file(source: str, destination: str) -> bool:
    """
    Copia un archivo de una ubicación a otra.
    
    Args:
        source: Ruta del archivo origen
        destination: Ruta del archivo destino
    
    Returns:
        True si se copió exitosamente, False en caso contrario
    """
    try:
        # Asegurar que el directorio destino existe
        dest_dir = os.path.dirname(destination)
        if dest_dir:
            ensure_directory(dest_dir)
        
        shutil.copy2(source, destination)
        logger.info(f"Archivo copiado: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Error al copiar archivo: {e}")
        return False


def get_file_extension(filepath: str) -> str:
    """
    Obtiene la extensión de un archivo.
    
    Args:
        filepath: Ruta del archivo
    
    Returns:
        Extensión del archivo (sin el punto)
    """
    _, ext = os.path.splitext(filepath)
    return ext.lstrip('.')


def join_path(*parts: str) -> str:
    """
    Une partes de una ruta de forma segura.
    
    Args:
        *parts: Partes de la ruta
    
    Returns:
        Ruta unida y normalizada
    """
    return os.path.normpath(os.path.join(*parts))

