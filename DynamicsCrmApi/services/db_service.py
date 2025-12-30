# coding: utf-8
"""
Servicio de persistencia en SQL Server para PQRS.
"""

from typing import List, Dict, Any, Optional
from shared.database.db_factory import DatabaseServiceFactory
from shared.database.crud import CRUDOperations
from shared.utils.logger import get_logger
from ..models.pqrs_model import PqrsModel

logger = get_logger("PqrsDbService")


class PqrsDbService:
    """Servicio para operaciones de base de datos relacionadas con PQRS."""
    
    TABLE_NAME = "ExpedicionCopiasDbo.expedicion_copias_pqrs"
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Inicializa el servicio con configuración de base de datos.
        
        Args:
            db_config: Configuración de base de datos (db_type, server, database, user, password, etc.)
        """
        self.db_config = db_config
        self.crud: Optional[CRUDOperations] = None
    
    def _get_crud(self) -> CRUDOperations:
        """Obtiene o crea la instancia de CRUDOperations."""
        if self.crud is None:
            self.crud = DatabaseServiceFactory.get_db_service_from_config(self.db_config.copy())
        return self.crud
    
    def guardar_pqrs(self, pqrs_model: PqrsModel) -> bool:
        """
        Guarda un registro de PQRS en la base de datos.
        Si el registro ya existe (por sp_documentoid), lo actualiza.
        
        Args:
            pqrs_model: Instancia de PqrsModel con los datos
            
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        try:
            crud = self._get_crud()
            db_dict = pqrs_model.to_db_dict()
            
            # Verificar si el registro ya existe
            check_query = f"SELECT sp_documentoid FROM {self.TABLE_NAME} WHERE sp_documentoid = ?"
            existing = crud.execute_query(check_query, (pqrs_model.sp_documentoid,))
            
            if existing:
                # Actualizar registro existente
                logger.debug(f"Actualizando PQRS existente: {pqrs_model.sp_documentoid}")
                update_fields = []
                update_values = []
                
                for key, value in db_dict.items():
                    if key != 'sp_documentoid' and key != 'fecha_creacion':
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                update_values.append(pqrs_model.sp_documentoid)
                update_query = f"""
                    UPDATE {self.TABLE_NAME}
                    SET {', '.join(update_fields)}
                    WHERE sp_documentoid = ?
                """
                crud.execute_non_query(update_query, tuple(update_values))
                logger.info(f"PQRS actualizado: {pqrs_model.sp_documentoid}")
            else:
                # Insertar nuevo registro
                logger.debug(f"Insertando nuevo PQRS: {pqrs_model.sp_documentoid}")
                fields = list(db_dict.keys())
                placeholders = ', '.join(['?' for _ in fields])
                values = tuple(db_dict.values())
                
                insert_query = f"""
                    INSERT INTO {self.TABLE_NAME} ({', '.join(fields)})
                    VALUES ({placeholders})
                """
                crud.execute_non_query(insert_query, values)
                logger.info(f"PQRS insertado: {pqrs_model.sp_documentoid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar PQRS {pqrs_model.sp_documentoid}: {str(e)}", exc_info=True)
            return False
    
    def guardar_multiples_pqrs(self, pqrs_models: List[PqrsModel]) -> int:
        """
        Guarda múltiples registros de PQRS en la base de datos.
        
        Args:
            pqrs_models: Lista de instancias de PqrsModel
            
        Returns:
            Número de registros guardados exitosamente
        """
        count = 0
        for pqrs_model in pqrs_models:
            if self.guardar_pqrs(pqrs_model):
                count += 1
        logger.info(f"Guardados {count} de {len(pqrs_models)} registros PQRS")
        return count
    
    def obtener_pendientes_actualizacion(self, subcategoria_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene registros pendientes de actualización en CRM.
        
        Args:
            subcategoria_name: Nombre de la subcategoría a filtrar
            
        Returns:
            Lista de diccionarios con los registros pendientes
        """
        try:
            crud = self._get_crud()
            query = f"""
                SELECT *
                FROM {self.TABLE_NAME}
                WHERE actualizadoCRM = 0
                  AND subcategoriaName = ?
            """
            results = crud.execute_query(query, (subcategoria_name,))
            logger.info(f"Encontrados {len(results)} registros pendientes para subcategoría: {subcategoria_name}")
            return results
            
        except Exception as e:
            logger.error(f"Error al obtener registros pendientes: {str(e)}", exc_info=True)
            return []
    
    def marcar_actualizado(self, sp_documentoid: str) -> bool:
        """
        Marca un registro como actualizado en CRM.
        
        Args:
            sp_documentoid: ID del documento (GUID)
            
        Returns:
            True si se actualizó exitosamente, False en caso contrario
        """
        try:
            crud = self._get_crud()
            query = f"""
                UPDATE {self.TABLE_NAME}
                SET actualizadoCRM = 1
                WHERE sp_documentoid = ?
            """
            crud.execute_non_query(query, (sp_documentoid,))
            logger.debug(f"Registro marcado como actualizado: {sp_documentoid}")
            return True
            
        except Exception as e:
            logger.error(f"Error al marcar registro como actualizado {sp_documentoid}: {str(e)}", exc_info=True)
            return False
