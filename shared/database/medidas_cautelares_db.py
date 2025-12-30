"""Fachada mínima de BD para proceso batch de Notificaciones Certificadas.

Solo incluye operaciones necesarias: conexión simple, select_one, reset de
transacciones PROCESANDO antiguas, obtención de pendientes, marcar PROCESANDO
y actualizar estado final. Todo código legacy eliminado.
"""

import re
from typing import Any, Dict, List, Optional
from shared.database.connection import create_connection, SQLServerConnection
from shared.utils.logger import get_logger

logger = get_logger(__name__)


class MedidasCautelaresDB:
    def __init__(self, credenciales_dict: Optional[dict] = None) -> None:
        cred = credenciales_dict or {}
        cfg = cred.get("database", {})
        server = cfg.get("server", cred.get("DB_HOST", "localhost"))
        if "," in str(server):
            host_part, port_part = str(server).split(",", 1)
            self.host = host_part.strip()
            self.port = int(port_part.strip())
        else:
            self.host = str(server).strip()
            self.port = int(cfg.get("port") or cred.get("DB_PORT", 1433))
        self.user = cfg.get("user") or cred.get("DB_USERNAME", "SA")
        self.password = cfg.get("password") or cred.get("DB_PASSWORD")
        self.database = (
            cfg.get("database") or cred.get("DB_NAME", "MedidasCautelares")
        )
        # Obtener esquema de la configuración (puede venir como 'Esquema' o 'schema')
        self.schema = cfg.get("Esquema") or cfg.get("schema") or cfg.get("esquema")
        self.conn: Optional[SQLServerConnection] = None
    
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

    # -------------------------------------------------- Conexión
    def connect(self) -> None:
        if self.conn and self.conn.connection:
            return
        self.conn = create_connection(
            db_type="sqlserver",
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            schema=self.schema,
        )
        self.conn.connect()
        logger.info("DB conectada")

    # -------------------------------------------------- Utilidad simple
    def select_one(self, query: str) -> Optional[Any]:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error en select_one: {e}")
            return None

    # -------------------------------------------------- Reset transacciones
    def reset_stale_processing_transactions(self, minutos: int = 30) -> int:
        """Devuelve a PENDIENTE transacciones en PROCESANDO muy antiguas."""
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            query = (
                f"UPDATE {transacciones_table} SET "
                "estado_envio_notificacion_certificada='PENDIENTE' "
                "WHERE estado_envio_notificacion_certificada='PROCESANDO' "
                "AND fecha_actualizacion < DATEADD(MINUTE, -?, GETDATE())"
            )
            cur.execute(query, (minutos,))
            self.conn.connection.commit()
            afectados = cur.rowcount
            cur.close()
            if afectados:
                logger.info(f"Reset de transacciones obsoletas: {afectados}")
            return afectados
        except Exception as e:
            logger.error(f"Error reseteando transacciones: {e}")
            return 0

    # -------------------------------------------------- Pendientes
    def get_pending_transactions(self, limite: int) -> List[Dict[str, Any]]:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            medidas_cautelares_table = self._format_table_name("medidas_cautelares")
            emails_table = self._format_table_name("emails")
            documentos_table = self._format_table_name("documentos")
            query = (
                "SELECT TOP (?) "
                "t.id AS transaccion_id, "
                "t.email_id, "
                "mc.radicado, "
                "mc.nombre_entidad, "
                "mc.email_entidad, "
                "mc.radicados_anexos, "
                "em.destinatarios, "
                "doc.ruta_documento, "
                "doc.nombre_original, "
                "doc.documento_id "
                f"FROM {transacciones_table} AS t "
                f"LEFT JOIN {medidas_cautelares_table} AS mc "
                "ON mc.email_id = t.email_id "
                f"LEFT JOIN {emails_table} AS em "
                "ON em.id = t.email_id "
                "OUTER APPLY ( "
                f"    SELECT TOP 1 d.ruta_documento, d.nombre_original, "
                "d.id AS documento_id "
                f"    FROM {documentos_table} AS d "
                "    WHERE d.email_id = t.email_id "
                "    AND d.tipo_documento = 'CONSTANCIA' "
                "    ORDER BY d.fecha_creacion DESC "
                ") AS doc "
                "WHERE (t.estado_envio_notificacion_certificada IS NULL "
                "OR UPPER(t.estado_envio_notificacion_certificada) = "
                "'PENDIENTE' ) "
                "AND t.estado_captura_informacion = 'PROCESADO' "
                "ORDER BY t.fecha_creacion ASC"
            )
            cur.execute(query, (limite,))
            rows = cur.fetchall()
            cur.close()
            resultados: List[Dict[str, Any]] = []
            for r in rows:
                resultados.append(
                    {
                        "transaccion_id": r.transaccion_id,
                        "email_id": r.email_id,
                        "radicado": r.radicado,
                        "nombre_entidad": r.nombre_entidad,
                        "email_entidad": r.email_entidad,
                        "ruta_documento": r.ruta_documento,
                        "radicados_anexos": r.radicados_anexos,
                        "destinatarios": r.destinatarios,
                        "documento_nombre": r.nombre_original,
                        "documento_id": r.documento_id,
                    }
                )
            return resultados
        except Exception as e:
            logger.error(f"Error obteniendo pendientes: {e}")
            return []

    # -------------------------------------------------- Marcar PROCESANDO
    def update_transaction_processing(self, transaccion_id: int) -> bool:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            query = (
                f"UPDATE {transacciones_table} SET "
                "estado_envio_notificacion_certificada='PROCESANDO', "
                "fecha_actualizacion=GETDATE() WHERE id=?"
            )
            cur.execute(query, (transaccion_id,))
            self.conn.connection.commit()
            ok = cur.rowcount > 0
            cur.close()
            return ok
        except Exception as e:
            logger.error(f"Error marcando PROCESANDO {transaccion_id}: {e}")
            return False

    # -------------------------------------------------- Estado final
    def update_transaction_status(
        self, transaccion_id: int, estado: str, observacion: str
    ) -> bool:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            query = (
                f"UPDATE {transacciones_table} SET "
                "estado_envio_notificacion_certificada=?, "
                "observaciones_envio_notificacion_certificada=?, "
                "fecha_envio_notificacion_certificada=GETDATE(), "
                "fecha_actualizacion=GETDATE() WHERE id=?"
            )
            cur.execute(query, (estado, observacion, transaccion_id))
            self.conn.connection.commit()
            ok = cur.rowcount > 0
            cur.close()
            return ok
        except Exception as e:
            logger.error(f"Error actualizando estado {transaccion_id}: {e}")
            return False

    # -------------------------------------------------- Pendientes para Testigo
    def get_pending_transactions_for_witness(self, limite: int) -> List[Dict[str, Any]]:
        """Obtiene transacciones con envío PROCESADO y sin descarga de testigo."""
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            medidas_cautelares_table = self._format_table_name("medidas_cautelares")
            emails_table = self._format_table_name("emails")
            query = (
                "SELECT TOP (?) "
                "t.id AS transaccion_id, "
                "t.email_id, "
                "mc.radicado, "
                "mc.nombre_entidad, "
                "mc.email_entidad, "
                "em.asunto, "
                "em.fecha_recepcion "
                f"FROM {transacciones_table} AS t "
                f"LEFT JOIN {medidas_cautelares_table} AS mc ON mc.email_id = t.email_id "
                f"LEFT JOIN {emails_table} AS em ON em.id = t.email_id "
                "WHERE UPPER(t.estado_envio_notificacion_certificada) = 'PROCESADO' "
                "AND (t.estado_descarga_testigo IS NULL "
                "OR UPPER(t.estado_descarga_testigo) = 'PENDIENTE') "
                "ORDER BY em.fecha_recepcion ASC"
            )
            logger.info(f"Ejecutando query de pendientes testigo: {query} con limite={limite}")
            print(f"[LDT] Ejecutando query de pendientes testigo: {query} con limite={limite}")
            cur.execute(query, (limite,))
            rows = cur.fetchall()
            cur.close()
            resultados: List[Dict[str, Any]] = []
            for r in rows:
                resultados.append(
                    {
                        "transaccion_id": r.transaccion_id,
                        "email_id": r.email_id,
                        "radicado": r.radicado,
                        "nombre_entidad": r.nombre_entidad,
                        "email_entidad": r.email_entidad,
                        "asunto": r.asunto,
                        "fecha_recepcion": r.fecha_recepcion,
                    }
                )
            return resultados
        except Exception as e:
            logger.error(f"Error obteniendo pendientes testigo: {e}")
            return []

    # -------------------------------------------------- Marcar PROCESANDO testigo
    def update_transaction_witness_processing(self, transaccion_id: int) -> bool:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            query = (
                f"UPDATE {transacciones_table} SET "
                "estado_descarga_testigo='PROCESANDO', "
                "fecha_actualizacion=GETDATE() WHERE id=?"
            )
            cur.execute(query, (transaccion_id,))
            self.conn.connection.commit()
            ok = cur.rowcount > 0
            cur.close()
            return ok
        except Exception as e:
            logger.error(
                f"Error marcando PROCESANDO testigo {transaccion_id}: {e}"
            )
            return False

    # -------------------------------------------------- Estado final testigo
    def update_transaction_witness_status(
        self, transaccion_id: int, estado: str, observaciones: str
    ) -> bool:
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            transacciones_table = self._format_table_name("transacciones")
            
            # If estado is "PROCESADO", also update fecha_descarga_testigo and set estado_carga_docuware to PENDIENTE
            if estado.upper() == "PROCESADO":
                query = (
                    f"UPDATE {transacciones_table} SET "
                    "estado_descarga_testigo=?, "
                    "observaciones_descarga_testigo=?, "
                    "fecha_descarga_testigo=GETDATE(), "
                    "estado_carga_docuware='PENDIENTE', "
                    "fecha_actualizacion=GETDATE() WHERE id=?"
                )
            else:
                query = (
                    f"UPDATE {transacciones_table} SET "
                    "estado_descarga_testigo=?, "
                    "observaciones_descarga_testigo=?, "
                    "fecha_actualizacion=GETDATE() WHERE id=?"
                )
            
            cur.execute(query, (estado, observaciones, transaccion_id))
            self.conn.connection.commit()
            ok = cur.rowcount > 0
            cur.close()
            return ok
        except Exception as e:
            logger.error(
                f"Error actualizando estado testigo {transaccion_id}: {e}"
            )
            return False

    # -------------------------------------------------- Insert documento
    def insert_documento(
        self,
        email_id: int,
        tipo_documento: str,
        nombre_original: str,
        ruta_documento: str,
        hash_documento: str,
    ) -> bool:
        """Inserta registro en documentos. Asume índice único por hash para idempotencia."""
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            documentos_table = self._format_table_name("documentos")
            query = (
                f"INSERT INTO {documentos_table} (email_id, tipo_documento, nombre_original, "
                "ruta_documento, hash_documento) VALUES (?, ?, ?, ?, ?)"
            )
            cur.execute(
                query,
                (email_id, tipo_documento, nombre_original, ruta_documento, hash_documento),
            )
            self.conn.connection.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"Error insertando documento ({tipo_documento}) email_id={email_id}: {e}")
            return False

    # -------------------------------------------------- Validar testigo por ID
    def testigo_existe_por_id(self, testigo_id: str, email_id: int) -> bool:
        """Valida si un testigo ya existe en BD por su ID extraído del nombre_original."""
        try:
            self.connect()
            cur = self.conn.connection.cursor()
            documentos_table = self._format_table_name("documentos")
            query = (
                f"SELECT nombre_original FROM {documentos_table} "
                "WHERE email_id = ? AND tipo_documento = 'TESTIGO'"
            )
            cur.execute(query, (email_id,))
            rows = cur.fetchall()
            cur.close()
            
            # Extraer ID del nombre_original y comparar
            pattern = r'^(\d+)_'
            for row in rows:
                nombre_original = row.nombre_original
                match = re.match(pattern, nombre_original)
                if match:
                    id_extraido = match.group(1)
                    if id_extraido == testigo_id:
                        return True
            return False
        except Exception as e:
            logger.error(f"Error validando testigo por ID {testigo_id} email_id={email_id}: {e}")
            return False

    # -------------------------------------------------- Cierre
    def close(self) -> None:
        if self.conn:
            try:
                self.conn.disconnect()
            except Exception as e:
                logger.error(f"Error cerrando conexión: {e}")
            finally:
                self.conn = None

    def close_all_connections(self) -> None:  # compatibilidad
        self.close()
