# coding: utf-8
"""
Servicio de base de datos para ExpedicionCopias.
Maneja la conexión y operaciones de base de datos para almacenar reportes.
"""

from typing import Any, Dict, Optional
from shared.database.db_factory import DatabaseServiceFactory
from shared.utils.logger import get_logger

logger = get_logger("ExpedicionCopiasDB")


class ExpedicionCopiasDB:
    """
    Servicio de base de datos para ExpedicionCopias.
    Maneja la conexión a SQL Server y operaciones de almacenamiento de reportes.
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Inicializa el servicio de base de datos.
        
        Args:
            config: Diccionario de configuración que debe contener:
                - Database: Configuración de base de datos con server, database, username, password, schema
                - O puede recibir credenciales_dict como en MedidasCautelaresDB para compatibilidad
        """
        # Soportar dos formatos: config directo o credenciales_dict
        if "Database" in config:
            db_config = config.get("Database", {}).copy()
        elif "database" in config:
            db_config = config.get("database", {}).copy()
        else:
            # Formato de MedidasCautelaresDB (credenciales_dict)
            cred = config
            cfg = cred.get("database", {})
            db_config = {
                "server": cfg.get("server", cred.get("DB_HOST", "localhost")),
                "database": cfg.get("database") or cred.get("DB_NAME", "RPA_Automatizacion"),
                "user": cfg.get("user") or cfg.get("username") or cred.get("DB_USERNAME", "SA"),
                "password": cfg.get("password") or cred.get("DB_PASSWORD"),
                "schema": cfg.get("Esquema") or cfg.get("schema") or cfg.get("esquema"),
                "db_type": cfg.get("db_type", "sqlserver")
            }
            # Manejar server con puerto
            server = db_config.get("server", "localhost")
            if "," in str(server):
                host_part, port_part = str(server).split(",", 1)
                db_config["server"] = host_part.strip()
                db_config["port"] = int(port_part.strip())
            else:
                db_config["port"] = int(cfg.get("port") or cred.get("DB_PORT", 1433))
        
        # Validar configuración mínima
        if not db_config.get("server") and not db_config.get("host"):
            raise ValueError("Configuración de BD requiere 'server' o 'host'")
        if not db_config.get("database"):
            raise ValueError("Configuración de BD requiere 'database'")
        if not db_config.get("username") and not db_config.get("user"):
            raise ValueError("Configuración de BD requiere 'username' o 'user'")
        if not db_config.get("password"):
            raise ValueError("Configuración de BD requiere 'password' (debe obtenerse desde rocketbot)")
        
        # Normalizar nombres: DatabaseServiceFactory espera 'user', no 'username'
        if "user" not in db_config and "username" in db_config:
            db_config["user"] = db_config.pop("username")
        
        # Obtener schema
        self.schema = db_config.get("schema") or db_config.get("Esquema") or "ExpedicionCopiasDbo"
        db_config["schema"] = self.schema
        
        # Asegurar db_type
        if "db_type" not in db_config:
            db_config["db_type"] = "sqlserver"
        
        logger.info(f"Inicializando ExpedicionCopiasDB con schema: {self.schema}")
        logger.info(f"Configuración BD: server={db_config.get('server')}, database={db_config.get('database')}, user={db_config.get('user')}")
        
        # Crear servicio de BD usando DatabaseServiceFactory
        try:
            self.crud = DatabaseServiceFactory.get_db_service_from_config(db_config)
            logger.info("Servicio de BD creado exitosamente")
        except Exception as e:
            logger.error(f"Error creando servicio de BD: {e}")
            raise
    
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
    
    def insert_reporte_expedicion(
        self,
        codigo_asistente: str,
        codigo_bot: str,
        usuario_red_bot_runner: str,
        nombre_estacion_bot_runner: str,
        id_proceso: int,
        no_radicado: str,
        matriculas: str,
        estado_proceso: str,
        observacion: str,
        fecha_inicio_ejecucion: str,
        hora_inicio_ejecucion: str,
        fecha_fin_ejecucion: str,
        hora_fin_ejecucion: str
    ) -> bool:
        """
        Inserta un registro en la tabla reporte_expedicion.
        
        Args:
            codigo_asistente: Código del asistente
            codigo_bot: Código del bot
            usuario_red_bot_runner: Usuario de red del bot runner
            nombre_estacion_bot_runner: Nombre de la estación del bot runner
            id_proceso: ID del proceso (PID)
            no_radicado: Número de radicado
            matriculas: Matrículas separadas por comas
            estado_proceso: Estado del proceso (Exitoso, No Exitoso, Pendiente)
            observacion: Observación del proceso
            fecha_inicio_ejecucion: Fecha de inicio (formato YYYY-MM-DD)
            hora_inicio_ejecucion: Hora de inicio (formato HH:MM:SS)
            fecha_fin_ejecucion: Fecha de fin (formato YYYY-MM-DD)
            hora_fin_ejecucion: Hora de fin (formato HH:MM:SS)
        
        Returns:
            True si se insertó correctamente, False en caso contrario
        """
        try:
            self.crud._ensure_connected()
            table_name = self._format_table_name("reporte_expedicion")
            
            query = f"""
                INSERT INTO {table_name} (
                    codigo_asistente,
                    codigo_bot,
                    usuario_red_bot_runner,
                    nombre_estacion_bot_runner,
                    id_proceso,
                    no_radicado,
                    matriculas,
                    estado_proceso,
                    observacion,
                    fecha_inicio_ejecucion,
                    hora_inicio_ejecucion,
                    fecha_fin_ejecucion,
                    hora_fin_ejecucion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                codigo_asistente,
                codigo_bot,
                usuario_red_bot_runner,
                nombre_estacion_bot_runner,
                id_proceso,
                no_radicado,
                matriculas,
                estado_proceso,
                observacion,
                fecha_inicio_ejecucion if fecha_inicio_ejecucion else None,
                hora_inicio_ejecucion if hora_inicio_ejecucion else None,
                fecha_fin_ejecucion if fecha_fin_ejecucion else None,
                hora_fin_ejecucion if hora_fin_ejecucion else None
            )
            
            cursor = self.crud.connection.execute(query, params)
            self.crud.connection.commit()
            cursor.close()
            
            logger.debug(f"Registro insertado en reporte_expedicion: {no_radicado} - {estado_proceso}")
            return True
            
        except Exception as e:
            logger.error(f"Error insertando registro en reporte_expedicion: {e}")
            try:
                self.crud.connection.rollback()
            except Exception:
                pass
            return False
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        try:
            if hasattr(self.crud, 'connection') and self.crud.connection:
                # Usar disconnect() que es el método estándar de DatabaseConnection
                if hasattr(self.crud.connection, 'disconnect'):
                    self.crud.connection.disconnect()
                logger.info("Conexión a BD cerrada")
        except Exception as e:
            logger.warning(f"Error cerrando conexión: {e}")
