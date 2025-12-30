# coding: utf-8
"""
Helper para carga de configuración desde dict o archivo JSON.
Utilidad compartida para todos los módulos.
"""

import os
import json
from typing import Union, Dict, Any
from shared.utils.config_parser import parse_config
from shared.utils.logger import get_logger

logger = get_logger("ConfigHelper")


def load_config_from_param(config_param: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Carga configuración desde un diccionario o ruta a archivo JSON.
    
    Args:
        config_param: Puede ser:
            - Dict: Diccionario de configuración directamente
            - str: Ruta a archivo JSON con configuración o string JSON
    
    Returns:
        Diccionario con la configuración cargada
    
    Raises:
        ValueError: Si la configuración es inválida o el archivo no existe
        TypeError: Si el tipo no es soportado
    """
    try:
        # Si es un diccionario, retornarlo directamente
        if isinstance(config_param, dict):
            return config_param
        
        # Si es string, intentar cargar como archivo JSON
        if isinstance(config_param, str):
            # Verificar si es una ruta de archivo
            if os.path.isfile(config_param):
                # Intentar leer como archivo JSON primero
                try:
                    with open(config_param, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        logger.info(f"Configuración cargada desde archivo JSON: {config_param}")
                        return config
                except json.JSONDecodeError:
                    # Si falla como JSON, intentar leer como archivo Python (diccionario)
                    try:
                        import ast
                        with open(config_param, 'r', encoding='utf-8') as f:
                            content = f.read()
                            config = ast.literal_eval(content)
                            if isinstance(config, dict):
                                logger.info(f"Configuración cargada desde archivo Python: {config_param}")
                                return config
                            else:
                                raise ValueError(f"El archivo evaluado no es un diccionario: {type(config)}")
                    except Exception as eval_error:
                        logger.error(f"No se pudo parsear el archivo como JSON ni como diccionario Python: {eval_error}")
                        raise ValueError(f"Error al cargar configuración desde archivo: {eval_error}, archivo: {config_param}") from eval_error
            else:
                # Intentar parsear como string JSON
                try:
                    config = parse_config(config_param)
                    logger.info("Configuración parseada desde string JSON")
                    return config
                except ValueError as e:
                    # Si falla, intentar evaluar como string de diccionario de Python
                    # (con comillas simples en lugar de dobles)
                    try:
                        import ast
                        config = ast.literal_eval(config_param)
                        if isinstance(config, dict):
                            logger.info("Configuración parseada desde string de diccionario Python")
                            return config
                        else:
                            raise ValueError(f"El string evaluado no es un diccionario: {type(config)}")
                    except Exception as eval_error:
                        logger.error(f"No se pudo parsear la configuración como JSON ni como diccionario Python: {eval_error}")
                        raise ValueError(f"Error al cargar configuración: {e}, configuración: {config_param}") from e
        
        raise TypeError(f"Tipo de configuración no soportado: {type(config_param)}")
    
    except FileNotFoundError as e:
        logger.error(f"Archivo de configuración no encontrado: {config_param}")
        raise ValueError(f"Archivo de configuración no encontrado: {config_param}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON: {e}")
        raise ValueError(f"Error al parsear JSON: {e}") from e
    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        raise ValueError(f"Error al cargar configuración: {e}") from e


def validate_email_config(config: Dict[str, Any]) -> bool:
    """
    Valida que la configuración tenga los campos requeridos para email.
    
    Args:
        config: Diccionario de configuración
    
    Returns:
        True si la configuración es válida
    """
    email_config = config.get("email", config)
    required_fields = ["client_id", "client_secret", "tenant_id", "user_email"]
    missing_fields = [field for field in required_fields if not email_config.get(field)]
    
    if missing_fields:
        logger.error(f"Campos faltantes en configuración de email: {missing_fields}")
        return False
    
    return True


def validate_database_config(config: Dict[str, Any]) -> bool:
    """
    Valida que la configuración tenga los campos requeridos para base de datos.
    
    Args:
        config: Diccionario de configuración
    
    Returns:
        True si la configuración es válida
    """
    db_config = config.get("database", {})
    
    if not db_config:
        logger.warning("No se encontró configuración de base de datos")
        return False
    
    # Validar que tenga al menos db_type
    if not db_config.get("db_type"):
        logger.error("Falta db_type en configuración de base de datos")
        return False
    
    return True

