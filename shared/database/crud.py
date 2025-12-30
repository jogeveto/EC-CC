# coding: utf-8
"""
Operaciones CRUD genéricas para base de datos.
Implementa el patrón Repository para abstraer las operaciones de BD.
"""

from typing import List, Dict, Any, Optional
import logging
from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class CRUDOperations:
    """Clase para operaciones CRUD genéricas."""

    def __init__(self, connection: DatabaseConnection):
        """
        Inicializa las operaciones CRUD.

        Args:
            connection: Instancia de DatabaseConnection
        """
        self.connection = connection
        # Obtener esquema de la conexión si está disponible
        self.schema = getattr(connection, 'schema', None)
        # No conectar automáticamente - se conectará cuando sea necesario (lazy connection)
        # Esto evita que se quede bloqueado si hay problemas de conexión
    
    def _format_table_name(self, table: str) -> str:
        """
        Formatea el nombre de la tabla con el esquema si está configurado.
        
        Args:
            table: Nombre de la tabla (puede incluir esquema: "schema.table" o "[schema].[table]")
            
        Returns:
            Nombre de tabla formateado según el tipo de BD
        """
        # Si la tabla ya tiene esquema (contiene punto o corchetes), usarla tal cual
        if "." in table or ("[" in table and "]" in table):
            logger.debug(f"Tabla ya tiene esquema: {table}")
            return table
        
        if not self.schema:
            return table
        
        # Para SQL Server usar formato [schema].[table]
        if self.connection.__class__.__name__ == "SQLServerConnection":
            return f"[{self.schema}].[{table}]"
        # Para PostgreSQL y MySQL usar formato schema.table
        elif self.connection.__class__.__name__ in ["PostgreSQLConnection", "MySQLConnection"]:
            return f"{self.schema}.{table}"
        # Para otros tipos, retornar sin modificar
        return table
    
    def _ensure_connected(self):
        """Asegura que la conexión esté establecida."""
        if not self.connection.connection:
            self.connection.connect()
    
    def _verificar_y_resolver_bloqueos(self, timeout_ms: int = 5000):
        """
        Verifica si la conexión actual está bloqueada y espera un tiempo máximo.
        Si hay bloqueo prolongado, intenta resolverlo.
        
        Args:
            timeout_ms: Tiempo máximo de espera en milisegundos antes de considerar bloqueo
        """
        try:
            # Verificar si hay bloqueos en la sesión actual
            query = """
            SELECT 
                r.blocking_session_id,
                r.wait_time,
                r.wait_type
            FROM sys.dm_exec_requests r
            INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
            WHERE s.session_id = @@SPID
              AND r.blocking_session_id > 0
              AND r.wait_time > ?
            """
            
            result = self.connection.execute(query, (timeout_ms,))
            if hasattr(result, 'fetchone'):
                row = result.fetchone()
                if row:
                    blocking_id = row[0]
                    wait_time = row[1]
                    wait_type = row[2]
                    logger.warning(
                        f"[BLOQUEO DETECTADO] Sesion bloqueada por {blocking_id}, "
                        f"tiempo de espera: {wait_time}ms, tipo: {wait_type}"
                    )
                    logger.warning(
                        f"[SOLUCION] Cierra herramientas de BD (DBeaver, SSMS) o ejecuta: KILL {blocking_id}"
                    )
        except Exception as e:
            # Si no se puede verificar, continuar (no es crítico)
            logger.debug(f"No se pudo verificar bloqueos: {e}")

    def create(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Inserta un nuevo registro en la tabla.

        Args:
            table: Nombre de la tabla
            data: Diccionario con los datos a insertar

        Returns:
            ID del registro insertado (si aplica)

        Example:
            crud.create("users", {"name": "John", "email": "john@example.com"})
        """
        try:
            self._ensure_connected()
            columns = ", ".join(data.keys())
            # Param style: '?' para sqlite, sqlserver, postgresql (psycopg2 usa %s pero aquí simplificado), '%s' para mysql
            driver_name = self.connection.__class__.__name__
            use_qmark = driver_name in [
                "SQLiteConnection",
                "SQLServerConnection",
                "PostgreSQLConnection",
            ]
            placeholders = ", ".join(["?" if use_qmark else "%s" for _ in data])
            values = tuple(data.values())

            # Formatear nombre de tabla con esquema
            formatted_table = self._format_table_name(table)
            
            # Para SQL Server devolver ID inmediatamente usando SCOPE_IDENTITY()
            if driver_name == "SQLServerConnection":
                query = f"INSERT INTO {formatted_table} ({columns}) VALUES ({placeholders}); SELECT SCOPE_IDENTITY() AS new_id;"
                logger.info(f"Ejecutando consulta SQL Server: {query} con valores {values}")
                cursor = self.connection.execute(query, values)
                self.connection.commit()
                try:
                    row = cursor.fetchone()
                    if row:
                        # pyodbc row puede ser tuple o Row object
                        id_value = row[0] if isinstance(row, tuple) else row.new_id
                        # Convertir Decimal a int si es necesario
                        return int(id_value) if id_value is not None else None
                except Exception as e:
                    logger.warning(f"Error obteniendo ID insertado: {e}")
                    return None
            else:
                query = f"INSERT INTO {formatted_table} ({columns}) VALUES ({placeholders})"
                logger.info(f"Ejecutando consulta: {query} con valores {values}")
                cursor = self.connection.execute(query, values)
                self.connection.commit()
                # Intentar lastrowid si disponible
                if hasattr(cursor, "lastrowid"):
                    return cursor.lastrowid

            logger.info(f"Registro insertado en {table}")
            return None
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error al insertar en {table}: {e}")
            raise

    def read(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lee registros de la tabla.

        Args:
            table: Nombre de la tabla
            filters: Diccionario con filtros WHERE
            limit: Límite de registros a retornar
            order_by: Campo para ordenar (ej: "id DESC")

        Returns:
            Lista de diccionarios con los registros

        Example:
            results = crud.read("users", {"status": "active"}, limit=10, order_by="id DESC")
        """
        try:
            self._ensure_connected()
            # Detectar SQL Server por clase
            is_sqlserver = self.connection.__class__.__name__ == "SQLServerConnection"
            
            # Formatear nombre de tabla con esquema
            formatted_table = self._format_table_name(table)

            if is_sqlserver and limit:
                query = f"SELECT TOP {limit} * FROM {formatted_table}"
            else:
                query = f"SELECT * FROM {formatted_table}"
            params = []

            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                query += " WHERE " + " AND ".join(conditions)

            if order_by:
                query += f" ORDER BY {order_by}"

            # Agregar LIMIT solo para motores que lo soportan (no SQL Server)
            if limit and not is_sqlserver:
                query += f" LIMIT {limit}"

            cursor = self.connection.execute(query, tuple(params) if params else None)

            # Convertir resultados a diccionarios
            if hasattr(cursor, "fetchall"):
                rows = cursor.fetchall()
                if rows and hasattr(rows[0], "keys"):
                    return [dict(row) for row in rows]
                return [
                    dict(zip([desc[0] for desc in cursor.description], row))
                    for row in rows
                ]
            else:
                return []
        except Exception as e:
            logger.error(f"Error al leer de {table}: {e}")
            raise

    def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        Actualiza registros en la tabla.

        Args:
            table: Nombre de la tabla
            filters: Diccionario con filtros WHERE
            data: Diccionario con los datos a actualizar

        Returns:
            Número de registros actualizados

        Example:
            crud.update("users", {"id": 1}, {"status": "inactive"})
        """
        try:
            self._ensure_connected()
            
            # Verificar bloqueos antes de ejecutar (solo para UPDATE, puede ser costoso)
            # self._verificar_y_resolver_bloqueos(timeout_ms=5000)
            
            set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
            where_clause = " AND ".join([f"{key} = ?" for key in filters.keys()])
            
            # Formatear nombre de tabla con esquema
            formatted_table = self._format_table_name(table)

            values = tuple(list(data.values()) + list(filters.values()))
            query = f"UPDATE {formatted_table} SET {set_clause} WHERE {where_clause}"

            logger.debug(f"[CRUD UPDATE] Query: {query}")
            logger.debug(f"[CRUD UPDATE] Valores: {values}")
            
            # Ejecutar con timeout para evitar bloqueos prolongados
            cursor = self.connection.execute(query, values)
            
            # Obtener rowcount antes del commit
            rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0
            
            # Hacer commit explícitamente con manejo de errores
            try:
                self.connection.commit()
                logger.debug(f"[CRUD UPDATE] Commit exitoso para {table}")
            except Exception as commit_error:
                logger.error(f"[CRUD UPDATE] Error en commit para {table}: {commit_error}")
                self.connection.rollback()
                raise
            
            logger.info(f"[CRUD UPDATE] {rows_affected} registro(s) actualizado(s) en {table}")
            logger.debug(f"[CRUD UPDATE] Filtros usados: {filters}, Datos actualizados: {data}")
            return rows_affected
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[CRUD UPDATE] Error al actualizar en {table}: {error_msg}")
            logger.error(f"[CRUD UPDATE] Tipo de error: {type(e).__name__}")
            
            # Verificar si es un error de constraint
            if "CHECK constraint" in error_msg or "constraint" in error_msg.lower():
                logger.error(f"[CRUD UPDATE] ⚠ Error de constraint - verifica que los valores cumplan con las restricciones")
                logger.error(f"[CRUD UPDATE] Datos que causaron el error: {data}")
            
            # Intentar rollback si hay error
            try:
                self.connection.rollback()
                logger.debug(f"[CRUD UPDATE] Rollback ejecutado")
            except Exception as rollback_error:
                logger.error(f"[CRUD UPDATE] Error en rollback: {rollback_error}")
            
            raise

    def delete(self, table: str, filters: Dict[str, Any]) -> int:
        """
        Elimina registros de la tabla.

        Args:
            table: Nombre de la tabla
            filters: Diccionario con filtros WHERE

        Returns:
            Número de registros eliminados

        Example:
            crud.delete("users", {"id": 1})
        """
        try:
            self._ensure_connected()
            where_clause = " AND ".join([f"{key} = ?" for key in filters.keys()])
            values = tuple(filters.values())
            
            # Formatear nombre de tabla con esquema
            formatted_table = self._format_table_name(table)

            query = f"DELETE FROM {formatted_table} WHERE {where_clause}"

            cursor = self.connection.execute(query, values)
            self.connection.commit()

            rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0
            logger.info(f"{rows_affected} registro(s) eliminado(s) de {table}")
            return rows_affected
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error al eliminar de {table}: {e}")
            raise

    def execute_query(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Ejecuta una consulta SQL personalizada.

        Args:
            query: Consulta SQL
            params: Parámetros para la consulta

        Returns:
            Resultado de la consulta

        Example:
            results = crud.execute_query("SELECT COUNT(*) FROM users WHERE status = ?", ("active",))
        """
        try:
            self._ensure_connected()
            cursor = self.connection.execute(query, params)
            if hasattr(cursor, "fetchall"):
                return cursor.fetchall()
            return cursor
        except Exception as e:
            logger.error(f"Error al ejecutar consulta: {e}")
            raise
