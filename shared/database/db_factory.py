# coding: utf-8
"""
Factory para crear conexiones y servicios de base de datos.
Simplifica el uso común de CRUDOperations.
"""

from typing import Dict, Any, Optional
from .connection import create_connection, DatabaseConnection
from .crud import CRUDOperations
from shared.utils.logger import get_logger

logger = get_logger("DatabaseServiceFactory")


class DatabaseServiceFactory:
    """Factory para crear servicios de base de datos."""
    
    @staticmethod
    def get_db_service(db_type: str = "sqlite", **db_config) -> CRUDOperations:
        """
        Crea un servicio de BD (CRUDOperations) con configuración simplificada.
        
        Args:
            db_type: Tipo de BD (sqlite, postgresql, mysql)
            **db_config: Configuración de BD (database, host, port, user, password, etc.)
        
        Returns:
            Instancia de CRUDOperations lista para usar
        
        Example:
            # SQLite
            crud = DatabaseServiceFactory.get_db_service("sqlite", database="test.db")
            
            # PostgreSQL
            crud = DatabaseServiceFactory.get_db_service(
                "postgresql",
                host="localhost",
                port=5432,
                database="mydb",
                user="user",
                password="pass"
            )
        """
        try:
            logger.info(f"get_db_service llamado con db_type={db_type}, parámetros: {list(db_config.keys())}")
            logger.info(f"Valores recibidos: server={db_config.get('server')}, database={db_config.get('database')}, user={db_config.get('user')}")
            logger.info(f"db_config completo: {db_config}")
            
            # Validar que los parámetros no sean None antes de pasar a create_connection
            if db_type in ["sqlserver", "mssql"]:
                server_val = db_config.get('server') or db_config.get('host')
                database_val = db_config.get('database')
                user_val = db_config.get('user')
                password_val = db_config.get('password')
                
                logger.info(f"Validación pre-create_connection: server={server_val}, database={database_val}, user={user_val}, password={'***' if password_val else None}")
                
                if not server_val:
                    raise ValueError(f"Server/host es None o vacío. db_config: {db_config}")
                if not database_val:
                    raise ValueError(f"Database es None o vacío. db_config: {db_config}")
                if not user_val:
                    raise ValueError(f"User es None o vacío. db_config: {db_config}")
                if not password_val:
                    raise ValueError(f"Password es None o vacío. db_config: {db_config}")
            
            logger.info("Llamando a create_connection...")
            connection = create_connection(db_type, **db_config)
            logger.info("create_connection completado exitosamente")
            
            crud = CRUDOperations(connection)
            logger.info(f"Servicio de BD creado: {db_type}")
            return crud
        except Exception as e:
            logger.error(f"Error al crear servicio de BD: {e}")
            logger.error(f"Parámetros recibidos en get_db_service: {db_config}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            raise
    
    @staticmethod
    def normalize_db_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza la configuración de BD para mantener compatibilidad.
        Convierte 'host' y 'port' a 'server' para SQL Server cuando sea necesario.
        Preserva el parámetro 'Esquema' o 'schema' para uso en queries.
        
        Args:
            config: Diccionario con configuración de BD
        
        Returns:
            Diccionario de configuración normalizado
        """
        config = config.copy()
        db_type = config.get("db_type", "sqlite").lower()
        
        logger.info(f"Normalizando configuración BD. Tipo: {db_type}, Campos originales: {list(config.keys())}")
        
        # Normalizar nombres de campos comunes de BaseDatos a formato estándar
        # BaseDatos (nombre de BD) -> database
        if "BaseDatos" in config and "database" not in config:
            config["database"] = config.pop("BaseDatos")
            logger.debug("Normalizado: BaseDatos -> database")
        
        # Server -> server
        if "Server" in config and "server" not in config:
            config["server"] = config.pop("Server")
            logger.debug(f"Normalizado: Server -> server = {config['server']}")
        
        # Normalizar esquema: aceptar tanto 'Esquema' como 'schema'
        if "Esquema" in config and "schema" not in config:
            config["schema"] = config.pop("Esquema")
            logger.debug(f"Normalizado: Esquema -> schema = {config['schema']}")
        elif "esquema" in config and "schema" not in config:
            config["schema"] = config.pop("esquema")
            logger.debug(f"Normalizado: esquema -> schema = {config['schema']}")
        
        # Para SQL Server, convertir host/port a server si es necesario
        if db_type in ["sqlserver", "mssql"]:
            # Si ya tiene 'server', usarlo directamente
            if "server" not in config and "host" in config:
                host = config.pop("host")
                port = config.pop("port", 1433)
                # Construir server en formato 'hostname,puerto'
                config["server"] = f"{host},{port}"
                logger.debug(f"Normalizado SQL Server config: host={host}, port={port} -> server={config['server']}")
            elif "server" in config and "," not in str(config["server"]) and "port" in config:
                # Si server no tiene puerto pero port está separado, combinarlos
                server = config.pop("server")
                port = config.pop("port", 1433)
                config["server"] = f"{server},{port}"
                logger.debug(f"Normalizado SQL Server config: server={server}, port={port} -> server={config['server']}")
            elif "server" in config:
                logger.debug(f"SQL Server config ya tiene server: {config['server']}")
            
            # Log del esquema si está presente
            if "schema" in config:
                logger.debug(f"Esquema configurado para SQL Server: {config['schema']}")
        
        return config
    
    @staticmethod
    def get_db_service_from_config(config: Dict[str, Any]) -> CRUDOperations:
        """
        Crea un servicio de BD desde un diccionario de configuración.
        Normaliza automáticamente la configuración para mantener compatibilidad.
        
        Args:
            config: Diccionario con configuración. Debe incluir 'db_type' y parámetros específicos.
        
        Returns:
            Instancia de CRUDOperations
        
        Example:
            config = {
                "db_type": "sqlite",
                "database": "test.db"
            }
            crud = DatabaseServiceFactory.get_db_service_from_config(config)
            
            # SQL Server con host y port (se normaliza automáticamente)
            config = {
                "db_type": "sqlserver",
                "host": "localhost",
                "port": 1433,
                "database": "mydb",
                "user": "SA",
                "password": "pass"
            }
            crud = DatabaseServiceFactory.get_db_service_from_config(config)
        """
        try:
            # Normalizar configuración para compatibilidad
            normalized_config = DatabaseServiceFactory.normalize_db_config(config)
            logger.info(f"Configuración normalizada. Campos: {list(normalized_config.keys())}")
            logger.info(f"Valores normalizados: server={normalized_config.get('server')}, database={normalized_config.get('database')}, user={normalized_config.get('user')}")
            
            db_type = normalized_config.pop("db_type", "sqlite")
            logger.info(f"Tipo de BD: {db_type}, Parámetros restantes: {list(normalized_config.keys())}")
            
            # Validar que los parámetros requeridos estén presentes
            if db_type in ["sqlserver", "mssql"]:
                if "server" not in normalized_config and "host" not in normalized_config:
                    error_msg = f"SQL Server requiere 'server' o 'host' en la configuración. Campos disponibles: {list(normalized_config.keys())}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if "database" not in normalized_config:
                    error_msg = f"SQL Server requiere 'database' en la configuración. Campos disponibles: {list(normalized_config.keys())}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                logger.debug(f"Validación SQL Server OK: server={normalized_config.get('server', normalized_config.get('host'))}, database={normalized_config.get('database')}")
            
            return DatabaseServiceFactory.get_db_service(db_type, **normalized_config)
        except Exception as e:
            logger.error(f"Error al crear servicio de BD desde configuración: {e}")
            logger.error(f"Configuración recibida: {config}")
            raise
    
    @staticmethod
    def get_db_service_from_string(config_string: str) -> CRUDOperations:
        """
        Crea un servicio de BD desde un string JSON.
        
        Args:
            config_string: String JSON con la configuración
        
        Returns:
            Instancia de CRUDOperations
        
        Example:
            config = '{"db_type": "sqlite", "database": "test.db"}'
            crud = DatabaseServiceFactory.get_db_service_from_string(config)
        """
        try:
            import json
            config = json.loads(config_string)
            return DatabaseServiceFactory.get_db_service_from_config(config)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear configuración JSON: {e}, configuración: {config_string}")
            raise ValueError(f"Configuración JSON inválida: {e}, configuración: {config_string}")
        except Exception as e:
            logger.error(f"Error al crear servicio de BD desde string: {e}")
            raise

