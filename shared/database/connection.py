# coding: utf-8
"""
Gestión de conexiones a base de datos.
Soporta múltiples tipos de BD: SQLite, PostgreSQL, MySQL, SQL Server.
"""

import sqlite3
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection(ABC):
    """Clase abstracta para conexiones de base de datos."""
    
    @abstractmethod
    def connect(self) -> Any:
        """Establece la conexión a la base de datos."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Cierra la conexión a la base de datos."""
        pass
    
    @abstractmethod
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Ejecuta una consulta SQL."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Confirma una transacción."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Revierte una transacción."""
        pass


class SQLiteConnection(DatabaseConnection):
    """Implementación para SQLite."""
    
    def __init__(self, database: str):
        """
        Inicializa la conexión a SQLite.
        
        Args:
            database: Ruta al archivo de base de datos SQLite
        """
        self.database = database
        self.connection: Optional[sqlite3.Connection] = None
    
    def connect(self) -> sqlite3.Connection:
        """Establece la conexión a SQLite."""
        try:
            self.connection = sqlite3.connect(self.database)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"Conectado a SQLite: {self.database}")
            return self.connection
        except Exception as e:
            logger.error(f"Error al conectar a SQLite: {e}")
            raise
    
    def disconnect(self) -> None:
        """Cierra la conexión a SQLite."""
        if self.connection:
            self.connection.close()
            logger.info("Desconectado de SQLite")
    
    def execute(self, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """Ejecuta una consulta SQL."""
        if not self.connection:
            self.connect()
        return self.connection.execute(query, params or ())
    
    def commit(self) -> None:
        """Confirma una transacción."""
        if self.connection:
            self.connection.commit()
    
    def rollback(self) -> None:
        """Revierte una transacción."""
        if self.connection:
            self.connection.rollback()


class PostgreSQLConnection(DatabaseConnection):
    """Implementación para PostgreSQL."""
    
    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5432):
        """
        Inicializa la conexión a PostgreSQL.
        
        Args:
            host: Host de la base de datos
            database: Nombre de la base de datos
            user: Usuario
            password: Contraseña
            port: Puerto (default: 5432)
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None
    
    def connect(self):
        """Establece la conexión a PostgreSQL."""
        try:
            import psycopg2
            self.connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            logger.info(f"Conectado a PostgreSQL: {self.database}")
            return self.connection
        except ImportError:
            logger.error("psycopg2 no está instalado. Instala con: pip install psycopg2-binary")
            raise
        except Exception as e:
            logger.error(f"Error al conectar a PostgreSQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Cierra la conexión a PostgreSQL."""
        if self.connection:
            self.connection.close()
            logger.info("Desconectado de PostgreSQL")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        """Ejecuta una consulta SQL."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        return cursor
    
    def commit(self) -> None:
        """Confirma una transacción."""
        if self.connection:
            self.connection.commit()
    
    def rollback(self) -> None:
        """Revierte una transacción."""
        if self.connection:
            self.connection.rollback()


class MySQLConnection(DatabaseConnection):
    """Implementación para MySQL."""
    
    def __init__(self, host: str, database: str, user: str, password: str, port: int = 3306):
        """
        Inicializa la conexión a MySQL.
        
        Args:
            host: Host de la base de datos
            database: Nombre de la base de datos
            user: Usuario
            password: Contraseña
            port: Puerto (default: 3306)
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None
    
    def connect(self):
        """Establece la conexión a MySQL."""
        try:
            import pymysql
            self.connection = pymysql.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            logger.info(f"Conectado a MySQL: {self.database}")
            return self.connection
        except ImportError:
            logger.error("pymysql no está instalado. Instala con: pip install pymysql")
            raise
        except Exception as e:
            logger.error(f"Error al conectar a MySQL: {e}")
            raise
    
    def disconnect(self) -> None:
        """Cierra la conexión a MySQL."""
        if self.connection:
            self.connection.close()
            logger.info("Desconectado de MySQL")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        """Ejecuta una consulta SQL."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        return cursor
    
    def commit(self) -> None:
        """Confirma una transacción."""
        if self.connection:
            self.connection.commit()
    
    def rollback(self) -> None:
        """Revierte una transacción."""
        if self.connection:
            self.connection.rollback()


class SQLServerConnection(DatabaseConnection):
    """
    Implementación para SQL Server.
    
    Requiere que un ODBC Driver for SQL Server esté instalado en el sistema.
    Por defecto intenta usar "ODBC Driver 17 for SQL Server", y si no está disponible,
    intenta con "ODBC Driver 18 for SQL Server".
    Para instrucciones de instalación, consulta: shared/database/README_ODBC_SETUP.md
    """
    
    @staticmethod
    def _get_available_driver() -> str:
        """
        Detecta automáticamente qué driver ODBC está disponible.
        
        Returns:
            Nombre del driver disponible, o "ODBC Driver 17 for SQL Server" como fallback
        """
        try:
            import pyodbc
            available_drivers = pyodbc.drivers()
            
            # Intentar primero con Driver 17 (más común)
            driver_17 = "ODBC Driver 17 for SQL Server"
            driver_18 = "ODBC Driver 18 for SQL Server"
            
            if driver_17 in available_drivers:
                logger.info(f"Driver detectado: {driver_17}")
                return driver_17
            elif driver_18 in available_drivers:
                logger.info(f"Driver detectado: {driver_18}")
                return driver_18
            else:
                # Buscar cualquier driver que contenga "SQL Server"
                for driver in available_drivers:
                    if "SQL Server" in driver:
                        logger.info(f"Driver detectado: {driver}")
                        return driver
                
                # Si no se encuentra ninguno, usar 17 como fallback
                logger.warning(f"No se encontró ningún driver ODBC para SQL Server. Drivers disponibles: {available_drivers}")
                logger.warning(f"Usando '{driver_17}' como fallback. Si falla, instala un driver ODBC para SQL Server.")
                return driver_17
        except ImportError:
            logger.warning("pyodbc no está disponible para detectar drivers. Usando 'ODBC Driver 17 for SQL Server' como fallback.")
            return "ODBC Driver 17 for SQL Server"
    
    def __init__(self, server: str, database: str, user: str, password: str, driver: Optional[str] = None, schema: Optional[str] = None):
        """
        Inicializa la conexión a SQL Server.
        
        Args:
            server: Servidor de la base de datos (formato: 'hostname,puerto' o 'hostname')
            database: Nombre de la base de datos
            user: Usuario
            password: Contraseña
            driver: Driver ODBC (default: None, detecta automáticamente el driver disponible)
            schema: Nombre del esquema (default: None, usa esquema por defecto)
            
        Note:
            Si encuentras errores de conexión relacionados con el driver ODBC,
            consulta shared/database/README_ODBC_SETUP.md para instrucciones
            de instalación y solución de problemas.
        """
        # Si no se especifica driver, detectar automáticamente
        if driver is None:
            driver = SQLServerConnection._get_available_driver()
        # Validar parámetros requeridos con logging detallado
        logger.info(f"SQLServerConnection.__init__ llamado con: server={server}, database={database}, user={user}, password={'***' if password else None}, driver={driver}, schema={schema}")
        
        if server is None or not server:
            error_msg = f"SQL Server 'server' parameter is required but got None. Verifica que la configuración tenga 'server' o 'Server'."
            logger.error(error_msg)
            raise ValueError(error_msg)
        if database is None or not database:
            error_msg = f"SQL Server 'database' parameter is required but got None. Verifica que la configuración tenga 'database' o 'BaseDatos'."
            logger.error(error_msg)
            raise ValueError(error_msg)
        if user is None or not user:
            error_msg = f"SQL Server 'user' parameter is required but got None."
            logger.error(error_msg)
            raise ValueError(error_msg)
        if password is None or not password:
            error_msg = f"SQL Server 'password' parameter is required but got None."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Asignar valores después de validación
        self.server = str(server)  # Asegurar que sea string
        self.database = str(database)  # Asegurar que sea string
        self.user = str(user)  # Asegurar que sea string
        self.password = str(password)  # Asegurar que sea string
        self.driver = driver
        self.schema = schema
        self.connection = None
        
        logger.info(f"SQLServerConnection inicializado correctamente: server={self.server}, database={self.database}, user={self.user}")
    
    def _format_table_name(self, table: str) -> str:
        """
        Formatea el nombre de la tabla con el esquema si está configurado.
        
        Args:
            table: Nombre de la tabla
            
        Returns:
            Nombre de tabla formateado: [schema].[table] si hay esquema, [table] si no
        """
        if self.schema:
            return f"[{self.schema}].[{table}]"
        return f"[{table}]"

    def connect(self):
        """
        Establece la conexión a SQL Server.
        """
        try:
            import pyodbc
            
            # Construir connection string
            connection_string = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.user};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=15;"
                f"Command Timeout=30;"
            )
            
            logger.info(f"Conectando a SQL Server: {self.server}/{self.database} con driver: {self.driver}")
            self.connection = pyodbc.connect(connection_string, timeout=15, autocommit=False)
            
            if hasattr(self.connection, 'autocommit'):
                self.connection.autocommit = False
                logger.debug("Autocommit deshabilitado - usando commits manuales")
            if hasattr(self.connection, 'timeout'):
                self.connection.timeout = 30
                logger.debug("Timeout de comandos configurado: 30 segundos")
            
            logger.info(f"Conectado exitosamente a SQL Server: {self.database}")
            return self.connection
            
        except ImportError:
            logger.error("pyodbc no está instalado. Instala con: pip install pyodbc")
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error al conectar a SQL Server: {error_msg}")
            logger.error(f"SERVER={self.server}, DATABASE={self.database}, DRIVER={self.driver}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            
            # Mensajes de ayuda según el tipo de error
            if "11001" in error_msg or "Host desconocido" in error_msg or "08001" in error_msg:
                logger.error("SOLUCIÓN: El hostname no se puede resolver. Verifica:")
                if self.server:
                    try:
                        server_host = self.server.split(',')[0] if ',' in str(self.server) else str(self.server)
                        logger.error(f"  1. Que el hostname sea correcto: {server_host}")
                    except (AttributeError, TypeError) as split_error:
                        logger.error(f"  1. Error al procesar server: {self.server} (tipo: {type(self.server)}). Error: {split_error}")
                else:
                    logger.error("  1. Que la configuración de 'server' esté presente en la configuración de BD")
                logger.error(f"  2. Que SQL Server esté corriendo en ese servidor")
            elif "IM002" in error_msg:
                logger.error("SOLUCIÓN: El driver ODBC no se encuentra. Verifica:")
                logger.error(f"  1. Que el driver '{self.driver}' esté instalado")
                try:
                    import pyodbc
                    available_drivers = pyodbc.drivers()
                    logger.error(f"  2. Drivers ODBC disponibles en el sistema: {available_drivers}")
                    logger.error("  3. Instala un driver ODBC para SQL Server desde:")
                    logger.error("     https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
                except ImportError:
                    logger.error("  2. pyodbc no está disponible. Instala con: pip install pyodbc")
            elif "timeout" in error_msg.lower():
                logger.error("SOLUCIÓN: Timeout de conexión. Verifica:")
                logger.error(f"  1. Que SQL Server esté corriendo y accesible")
                logger.error(f"  2. Que el puerto sea correcto: {self.server}")
                logger.error("  3. Que el firewall permita conexiones")
            
            raise
    
    def disconnect(self) -> None:
        """Cierra la conexión a SQL Server."""
        if self.connection:
            self.connection.close()
            logger.info("Desconectado de SQL Server")
    
    def execute(self, query: str, params: Optional[tuple] = None):
        """Ejecuta una consulta SQL."""
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        return cursor
    
    def commit(self) -> None:
        """Confirma una transacción."""
        if self.connection:
            self.connection.commit()
    
    def rollback(self) -> None:
        """Revierte una transacción."""
        if self.connection:
            self.connection.rollback()


def create_connection(db_type: str, **kwargs) -> DatabaseConnection:
    """
    Factory para crear conexiones de base de datos.
    
    Args:
        db_type: Tipo de BD ('sqlite', 'postgresql', 'mysql', 'sqlserver')
        **kwargs: Parámetros específicos de cada tipo de BD
    
    Returns:
        Instancia de DatabaseConnection
    
    Example:
        # SQLite
        conn = create_connection('sqlite', database='mydb.db')
        
        # PostgreSQL
        conn = create_connection('postgresql', host='localhost',
                                 database='mydb', user='user', password='pass')
        
        # SQL Server (usando host y port)
        conn = create_connection('sqlserver', host='localhost', port=1433,
                                 database='mydb', user='SA', password='pass')
        
        # SQL Server (usando server)
        conn = create_connection('sqlserver', server='localhost,1433',
                                 database='mydb', user='SA', password='pass')
    """
    db_type = db_type.lower()
    
    if db_type == 'sqlite':
        return SQLiteConnection(kwargs.get('database'))
    elif db_type == 'postgresql':
        return PostgreSQLConnection(
            host=kwargs.get('host'),
            database=kwargs.get('database'),
            user=kwargs.get('user'),
            password=kwargs.get('password'),
            port=kwargs.get('port', 5432)
        )
    elif db_type == 'mysql':
        return MySQLConnection(
            host=kwargs.get('host'),
            database=kwargs.get('database'),
            user=kwargs.get('user'),
            password=kwargs.get('password'),
            port=kwargs.get('port', 3306)
        )
    elif db_type in ["sqlserver", "mssql"]:
        # Log de depuración
        logger.info(f"Creando conexión SQL Server con kwargs: {list(kwargs.keys())}")
        logger.info(f"Valores en kwargs: server={kwargs.get('server')}, database={kwargs.get('database')}, user={kwargs.get('user')}")
        
        # Handle both 'server' format and 'host' + 'port' format
        server = kwargs.get("server")
        if not server:
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 1433)
            server = f"{host},{port}" if port else host
            logger.info(f"Server construido desde host/port: {server}")
        else:
            logger.info(f"Server obtenido de kwargs: {server}")
        
        database = kwargs.get("database")
        if not database:
            logger.error(f"Parámetros recibidos en create_connection: {list(kwargs.keys())}")
            logger.error(f"Valores de kwargs: {kwargs}")
            raise ValueError(f"SQL Server connection requires 'database' parameter. Parámetros disponibles: {list(kwargs.keys())}")
        
        user = kwargs.get("user")
        password = kwargs.get("password")
        
        # Validar que user y password no sean None
        if not user:
            logger.error(f"SQL Server 'user' parameter is None. Parámetros disponibles: {list(kwargs.keys())}")
            raise ValueError(f"SQL Server connection requires 'user' parameter. Parámetros disponibles: {list(kwargs.keys())}")
        if not password:
            logger.error(f"SQL Server 'password' parameter is None. Parámetros disponibles: {list(kwargs.keys())}")
            raise ValueError(f"SQL Server connection requires 'password' parameter. Parámetros disponibles: {list(kwargs.keys())}")
        
        logger.info(f"Database obtenido: {database}")
        logger.info(f"User obtenido: {user}")
        logger.info(f"Server final: {server}")
        
        # Obtener esquema de kwargs (puede venir como 'schema' o 'esquema')
        schema = kwargs.get("schema") or kwargs.get("esquema")
        logger.info(f"Schema obtenido: {schema}")
        
        # Validación final antes de crear la conexión
        logger.info(f"Validación final antes de crear SQLServerConnection:")
        logger.info(f"  server={server} (tipo: {type(server)})")
        logger.info(f"  database={database} (tipo: {type(database)})")
        logger.info(f"  user={user} (tipo: {type(user)})")
        logger.info(f"  password={'***' if password else None} (tipo: {type(password)})")
        logger.info(f"  schema={schema} (tipo: {type(schema)})")
        
        if not server or server is None:
            error_msg = f"Server no puede ser None. kwargs recibidos: {list(kwargs.keys())}, valores: {kwargs}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if not database or database is None:
            error_msg = f"Database no puede ser None. kwargs recibidos: {list(kwargs.keys())}, valores: {kwargs}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if not user or user is None:
            error_msg = f"User no puede ser None. kwargs recibidos: {list(kwargs.keys())}, valores: {kwargs}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if not password or password is None:
            error_msg = f"Password no puede ser None. kwargs recibidos: {list(kwargs.keys())}, valores: {kwargs}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Todos los parámetros validados correctamente. Creando SQLServerConnection...")
        
        try:
            connection = SQLServerConnection(
                server=server,
                database=database,
                user=user,
                password=password,
                driver=kwargs.get("driver"),  # None = detección automática
                schema=schema,
            )
            logger.info("SQLServerConnection creado exitosamente")
            return connection
        except Exception as e:
            logger.error(f"Error al crear SQLServerConnection: {e}")
            logger.error(f"Parámetros que se intentaron pasar: server={server}, database={database}, user={user}, password={'***' if password else None}")
            raise
    else:
        raise ValueError(f"Tipo de BD no soportado: {db_type}")

