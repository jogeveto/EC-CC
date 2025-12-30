# coding: utf-8
"""
Servicio de negocio para operaciones con PQRS de Dynamics CRM.
Adaptado de pruebas-azure-connections para usar variables de Rocketbot.
"""

import json
import urllib.parse
from typing import List, Dict, Any, Optional
from shared.utils.logger import get_logger

from ..core.dynamics_client import Dynamics365Client
from ..models.pqrs_model import PqrsModel
from .db_service import PqrsDbService

logger = get_logger("PqrsService")


class PqrsService:
    """Servicio para operaciones relacionadas con PQRS (sp_documentos) en Dynamics 365."""

    ENTITY_NAME = "sp_documentos"
    ID_FIELD = "sp_documentoid"
    NAME_FIELD = "sp_name"
    TITLE_FIELD = "sp_titulopqrs"

    def __init__(self, dynamics_client: Dynamics365Client, db_service: PqrsDbService) -> None:
        """
        Inicializa el servicio con un cliente Dynamics 365 y servicio de BD.

        Args:
            dynamics_client: Instancia de Dynamics365Client
            db_service: Instancia de PqrsDbService
        """
        self.client = dynamics_client
        self.db_service = db_service

    def _parse_json_string(self, json_string: str) -> List[str]:
        """
        Parsea un string JSON a una lista de strings.
        
        Args:
            json_string: String JSON (puede ser array o objeto con clave)
            
        Returns:
            Lista de strings
        """
        try:
            parsed = json.loads(json_string)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # Buscar la primera lista en el diccionario
                for value in parsed.values():
                    if isinstance(value, list):
                        return value
                # Si no hay lista, retornar lista vacía
                return []
            else:
                logger.warning(f"JSON parseado no es lista ni diccionario: {type(parsed)}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON string: {str(e)}")
            raise ValueError(f"JSON inválido: {str(e)}")

    def consultar_por_filtros(
        self,
        subcategorias_ids: str,
        invt_especificacion: Optional[str],
        subcategoria_name: str
    ) -> Dict[str, Any]:
        """
        Consulta PQRS por filtros y persiste en base de datos.
        
        Args:
            subcategorias_ids: String JSON con array de IDs de subcategorías
            invt_especificacion: String JSON opcional con array de IDs de especificaciones
            subcategoria_name: Nombre de la subcategoría (para almacenar en BD)
            
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            logger.info(f"[INICIO] Consulta por filtros - Subcategoría: {subcategoria_name}")
            
            # Parsear JSON strings
            ids_subcategorias = self._parse_json_string(subcategorias_ids)
            ids_especificaciones = []
            if invt_especificacion:
                ids_especificaciones = self._parse_json_string(invt_especificacion)
            
            if not ids_subcategorias:
                error_msg = "No se proporcionaron IDs de subcategorías válidos"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg, "registros_encontrados": 0, "registros_guardados": 0}
            
            logger.info(f"Buscando PQRS para {len(ids_subcategorias)} subcategorías y {len(ids_especificaciones)} especificaciones")
            
            # Buscar PQRS en CRM
            registros_crm = self._buscar_pqrs_por_subcategorias_recursivo(ids_subcategorias, ids_especificaciones)
            
            if not registros_crm:
                logger.info("No se encontraron registros en CRM")
                return {"status": "success", "message": "No se encontraron registros", "registros_encontrados": 0, "registros_guardados": 0}
            
            logger.info(f"Encontrados {len(registros_crm)} registros en CRM")
            
            # Mapear a modelos y agregar subcategoriaName
            pqrs_models = []
            for registro in registros_crm:
                registro['subcategoriaName'] = subcategoria_name
                pqrs_model = PqrsModel.from_dict(registro)
                pqrs_models.append(pqrs_model)
            
            # Persistir en BD
            registros_guardados = self.db_service.guardar_multiples_pqrs(pqrs_models)
            
            logger.info(f"[FIN] Consulta completada - Encontrados: {len(registros_crm)}, Guardados: {registros_guardados}")
            
            return {
                "status": "success",
                "message": f"Consulta completada exitosamente",
                "registros_encontrados": len(registros_crm),
                "registros_guardados": registros_guardados,
                "subcategoria_name": subcategoria_name
            }
            
        except Exception as e:
            error_msg = f"Error en consulta por filtros: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "message": error_msg, "registros_encontrados": 0, "registros_guardados": 0}

    def _buscar_pqrs_por_subcategorias_recursivo(
        self, ids_subcategorias: List[str], ids_especificaciones: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Busca TODAS las PQRS relacionadas con los IDs especificados.
        Implementa paginación recursiva completa.
        
        Args:
            ids_subcategorias: Lista de IDs de subcategorías (GUIDs)
            ids_especificaciones: Lista de IDs de especificaciones (GUIDs)
            
        Returns:
            Lista completa de todas las PQRS encontradas
        """
        # Construir condición OR para subcategorías
        subcat_conditions = " or ".join([f"_sp_subcategoriapqrs_value eq '{subcat_id}'" for subcat_id in ids_subcategorias])
        subcat_filter = f"({subcat_conditions})" if ids_subcategorias else ""
        
        # Construir condición OR para especificaciones
        espec_conditions = " or ".join([f"_invt_especificacion_value eq '{espec_id}'" for espec_id in ids_especificaciones])
        espec_filter = f"({espec_conditions})" if ids_especificaciones else ""
        
        # Combinar filtros con AND
        if subcat_filter and espec_filter:
            filter_query = f"{subcat_filter} and {espec_filter} and sp_resolvercaso eq false"
        elif subcat_filter:
            filter_query = f"{subcat_filter} and sp_resolvercaso eq false"
        elif espec_filter:
            filter_query = f"{espec_filter} and sp_resolvercaso eq false"
        else:
            logger.warning("No se proporcionaron filtros válidos")
            return []
        
        logger.debug(f"Filtro OData: {filter_query}")
        
        # Búsqueda recursiva con paginación
        return self._ejecutar_busqueda_recursiva(filter_query)

    def _ejecutar_busqueda_recursiva(self, filter_query: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una búsqueda con paginación recursiva completa.
        
        Args:
            filter_query: Filtro OData completo
            
        Returns:
            Lista completa de todos los registros encontrados
        """
        all_records = []
        page = 1
        max_pages = 10000  # Límite de seguridad
        
        # Lista completa de campos
        all_fields = [
            "_createdby_value", "_createdonbehalfby_value", "_invt_especificacion_value",
            "_invt_tipodeatencion_value", "_modifiedby_value", "_modifiedonbehalfby_value", "_ownerid_value",
            "_owningbusinessunit_value", "_owningteam_value", "_owninguser_value", "_sp_abogadoresponsable_value",
            "_sp_agentedebackofficeasignado_value", "_sp_agentedecallcenterasignado_value", "_sp_casooriginal_value",
            "_sp_categoriapqrs_value", "_sp_ciudad_value", "_sp_cliente_value", "_sp_contacto_value",
            "_sp_contactopqrs_value", "_sp_departamento_value", "_sp_motivopqrs_value", "_sp_pais_value",
            "_sp_responsable_value", "_sp_responsabledelbackoffice_value", "_sp_responsabledevolucionyreingreso_value",
            "_sp_sedepqrs_value", "_sp_sederesponsable_value", "_sp_serviciopqrs_value", "_sp_subcategoriapqrs_value",
            "_sp_tipodecasopqrs_value", "createdon", "emailaddress", "importsequencenumber", "invt_ansajustado",
            "invt_correoelectronico", "invt_matriculasrequeridas", "invt_referenciadocumento", "modifiedon",
            "overriddencreatedon", "sp_aceptaciondeterminos", "sp_anomina", "sp_ans", "sp_apellidos", "sp_callid",
            "sp_celular", "sp_clienteescontacto", "sp_clienteescuenta", "sp_clonarcaso", "sp_consecutivo",
            "sp_correoelectronico", "sp_descripcion", "sp_descripciondelasolucion", "sp_devolucioncompleja",
            "sp_direccion", "sp_direccionip", "sp_documentoid", "sp_estadomigracion", "sp_fechacierrecnx",
            "sp_fechadecierre", "sp_fechadecreacinreal", "sp_fechadevencimiento", "sp_fechadevolucioncompleja",
            "sp_fechadiligenciamientodeinformacion", "sp_fechalimitederespuesta", "sp_fechalimitederespuestacnx",
            "sp_guid", "sp_matriculainscripcion", "sp_medioderespuesta", "sp_mensajesdecorreoelecrtrnico",
            "sp_mensajesdetextoalcelular", "sp_name", "sp_nit", "sp_nmerodedocumentocliente", "sp_nombredeagentequecrea",
            "sp_nombredelaempresa", "sp_nombres", "sp_nroderadicado", "sp_numerodecaso", "sp_numerodedocumento",
            "sp_numerodedocumentodelcontacto", "sp_origen", "sp_pqrsclonada", "sp_razonparaelestadomigracion",
            "sp_reingresoaprobado", "sp_requiereactualizaciondeboletn", "sp_requiereactualizaciondelabel",
            "sp_resolvercaso", "sp_solucionenprimercontacto", "sp_telefonofijo", "sp_tipodedocumento", "sp_tipopnc",
            "sp_titulopqrs", "sp_turno", "sp_url_callcenter", "sp_url_seguimiento", "sp_usuarioresponsablelocalizador",
            "statecode", "statuscode", "timezoneruleversionnumber", "utcconversiontimezonecode", "versionnumber"
        ]
        
        select_fields = ",".join(all_fields)
        
        params = {
            "$filter": filter_query,
            "$select": select_fields,
            "$top": 5000,
            "$orderby": "createdon desc"
        }
        
        while page <= max_pages:
            try:
                endpoint = f"/{self.ENTITY_NAME}"
                response = self.client.get(endpoint, params=params)
                records = response.get("value", []) if isinstance(response, dict) else []
                
                if records:
                    all_records.extend(records)
                    logger.debug(f"Página {page}: {len(records)} registros (Total: {len(all_records)})")
                else:
                    logger.debug(f"Página {page}: Sin registros")
                    break
                
                # Verificar si hay más páginas
                next_link = response.get("@odata.nextLink")
                if not next_link:
                    logger.debug("No hay más páginas")
                    break
                
                # Extraer parámetros del nextLink
                if next_link.startswith("http"):
                    if "/api/data/v9.2" in next_link:
                        path_and_query = next_link.split("/api/data/v9.2", 1)[1]
                    else:
                        base_url_path = self.client.base_url.replace("/api/data/v9.2", "")
                        if base_url_path in next_link:
                            path_and_query = next_link.split(base_url_path + "/api/data/v9.2", 1)[1]
                        else:
                            logger.warning(f"No se pudo parsear nextLink: {next_link[:100]}")
                            break
                else:
                    path_and_query = next_link
                
                # Extraer parámetros de la URL
                parsed = urllib.parse.urlparse(path_and_query)
                query_params = urllib.parse.parse_qs(parsed.query)
                
                params = {}
                for key, value_list in query_params.items():
                    if value_list:
                        params[key] = value_list[0] if len(value_list) == 1 else value_list
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error en página {page}: {str(e)[:200]}", exc_info=True)
                break
        
        if page >= max_pages:
            logger.warning(f"Se alcanzó el límite de páginas ({max_pages})")
        
        return all_records

    def actualizar_pqrs(self, subcategoria_name: str) -> Dict[str, Any]:
        """
        Actualiza PQRS pendientes en Dynamics CRM desde la base de datos local.
        
        Args:
            subcategoria_name: Nombre de la subcategoría a filtrar
            
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            logger.info(f"[INICIO] Actualización de PQRS - Subcategoría: {subcategoria_name}")
            
            # Obtener registros pendientes desde BD
            registros_pendientes = self.db_service.obtener_pendientes_actualizacion(subcategoria_name)
            
            if not registros_pendientes:
                logger.info("No hay registros pendientes de actualización")
                return {
                    "status": "success",
                    "message": "No hay registros pendientes de actualización",
                    "registros_procesados": 0,
                    "registros_actualizados": 0
                }
            
            logger.info(f"Encontrados {len(registros_pendientes)} registros pendientes")
            
            actualizados_exitosos = 0
            errores = []
            
            for registro in registros_pendientes:
                sp_documentoid = registro.get('sp_documentoid')
                cuerpo_correo = registro.get('cuerpoCorreo')
                
                if not sp_documentoid:
                    logger.warning("Registro sin sp_documentoid, omitiendo")
                    continue
                
                try:
                    # Actualizar en CRM
                    payload = {
                        "sp_descripciondelasolucion": cuerpo_correo or "",
                        "sp_resolvercaso": True
                    }
                    
                    endpoint = f"/{self.ENTITY_NAME}({sp_documentoid})"
                    self.client.patch(endpoint, data=payload)
                    
                    # Marcar como actualizado en BD
                    if self.db_service.marcar_actualizado(sp_documentoid):
                        actualizados_exitosos += 1
                        logger.debug(f"PQRS actualizado exitosamente: {sp_documentoid}")
                    else:
                        logger.warning(f"PQRS actualizado en CRM pero no se pudo marcar en BD: {sp_documentoid}")
                        errores.append(f"No se pudo marcar en BD: {sp_documentoid}")
                    
                except Exception as e:
                    error_msg = f"Error actualizando {sp_documentoid}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errores.append(error_msg)
            
            logger.info(f"[FIN] Actualización completada - Procesados: {len(registros_pendientes)}, Exitosos: {actualizados_exitosos}")
            
            return {
                "status": "success" if not errores else "partial",
                "message": f"Actualización completada",
                "registros_procesados": len(registros_pendientes),
                "registros_actualizados": actualizados_exitosos,
                "errores": errores if errores else None
            }
            
        except Exception as e:
            error_msg = f"Error en actualización de PQRS: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "message": error_msg,
                "registros_procesados": 0,
                "registros_actualizados": 0
            }
