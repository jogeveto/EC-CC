# coding: utf-8
"""
Modelo de datos para PQRS de Dynamics CRM.
Mapea los campos del JSON de respuesta de Dynamics CRM a la estructura de base de datos.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from shared.database.models import BaseModel


class PqrsModel(BaseModel):
    """Modelo de datos para PQRS de Dynamics CRM."""
    
    def __init__(self, **kwargs):
        """Inicializa el modelo con los datos proporcionados."""
        # Campos del CRM (del JSON)
        self.sp_documentoid = kwargs.get('sp_documentoid')
        self.sp_name = kwargs.get('sp_name')
        self.sp_titulopqrs = kwargs.get('sp_titulopqrs')
        self.sp_descripcion = kwargs.get('sp_descripcion')
        self.sp_descripciondelasolucion = kwargs.get('sp_descripciondelasolucion')
        self.sp_resolvercaso = kwargs.get('sp_resolvercaso', False)
        
        # Campos de referencia (lookups)
        self._sp_tipodecasopqrs_value = kwargs.get('_sp_tipodecasopqrs_value')
        self._sp_serviciopqrs_value = kwargs.get('_sp_serviciopqrs_value')
        self._sp_categoriapqrs_value = kwargs.get('_sp_categoriapqrs_value')
        self._sp_subcategoriapqrs_value = kwargs.get('_sp_subcategoriapqrs_value')
        self._sp_contactopqrs_value = kwargs.get('_sp_contactopqrs_value')
        self._sp_contacto_value = kwargs.get('_sp_contacto_value')
        self._sp_cliente_value = kwargs.get('_sp_cliente_value')
        self._sp_departamento_value = kwargs.get('_sp_departamento_value')
        self._sp_ciudad_value = kwargs.get('_sp_ciudad_value')
        self._sp_pais_value = kwargs.get('_sp_pais_value')
        self._sp_sedepqrs_value = kwargs.get('_sp_sedepqrs_value')
        self._sp_sederesponsable_value = kwargs.get('_sp_sederesponsable_value')
        self._sp_motivopqrs_value = kwargs.get('_sp_motivopqrs_value')
        self._sp_casooriginal_value = kwargs.get('_sp_casooriginal_value')
        self._sp_responsable_value = kwargs.get('_sp_responsable_value')
        self._sp_responsabledelbackoffice_value = kwargs.get('_sp_responsabledelbackoffice_value')
        self._sp_responsabledevolucionyreingreso_value = kwargs.get('_sp_responsabledevolucionyreingreso_value')
        self._sp_abogadoresponsable_value = kwargs.get('_sp_abogadoresponsable_value')
        self._sp_agentedecallcenterasignado_value = kwargs.get('_sp_agentedecallcenterasignado_value')
        self._sp_agentedebackofficeasignado_value = kwargs.get('_sp_agentedebackofficeasignado_value')
        self._invt_especificacion_value = kwargs.get('_invt_especificacion_value')
        self._invt_tipodeatencion_value = kwargs.get('_invt_tipodeatencion_value')
        self._ownerid_value = kwargs.get('_ownerid_value')
        self._owninguser_value = kwargs.get('_owninguser_value')
        self._owningteam_value = kwargs.get('_owningteam_value')
        self._owningbusinessunit_value = kwargs.get('_owningbusinessunit_value')
        self._createdby_value = kwargs.get('_createdby_value')
        self._createdonbehalfby_value = kwargs.get('_createdonbehalfby_value')
        self._modifiedby_value = kwargs.get('_modifiedby_value')
        self._modifiedonbehalfby_value = kwargs.get('_modifiedonbehalfby_value')
        
        # Campos de datos
        self.sp_fechadecierre = kwargs.get('sp_fechadecierre')
        self.versionnumber = kwargs.get('versionnumber')
        self.sp_aceptaciondeterminos = kwargs.get('sp_aceptaciondeterminos', False)
        self.sp_nombredelaempresa = kwargs.get('sp_nombredelaempresa')
        self.invt_ansajustado = kwargs.get('invt_ansajustado', False)
        self.sp_fechadevolucioncompleja = kwargs.get('sp_fechadevolucioncompleja')
        self.invt_correoelectronico = kwargs.get('invt_correoelectronico')
        self.invt_referenciadocumento = kwargs.get('invt_referenciadocumento')
        self.sp_matriculainscripcion = kwargs.get('sp_matriculainscripcion')
        self.sp_correoelectronico = kwargs.get('sp_correoelectronico')
        self.sp_turno = kwargs.get('sp_turno')
        self.sp_fechadecreacinreal = kwargs.get('sp_fechadecreacinreal')
        self.sp_celular = kwargs.get('sp_celular')
        self.invt_matriculasrequeridas = kwargs.get('invt_matriculasrequeridas')
        self.utcconversiontimezonecode = kwargs.get('utcconversiontimezonecode')
        self.sp_numerodedocumentodelcontacto = kwargs.get('sp_numerodedocumentodelcontacto')
        self.sp_nombres = kwargs.get('sp_nombres')
        self.sp_direccionip = kwargs.get('sp_direccionip')
        self.sp_pqrsclonada = kwargs.get('sp_pqrsclonada', False)
        self.sp_url_seguimiento = kwargs.get('sp_url_seguimiento')
        self.sp_numerodedocumento = kwargs.get('sp_numerodedocumento')
        self.sp_guid = kwargs.get('sp_guid')
        self.overriddencreatedon = kwargs.get('overriddencreatedon')
        self.sp_clienteescontacto = kwargs.get('sp_clienteescontacto', False)
        self.modifiedon = kwargs.get('modifiedon')
        self.sp_fechalimitederespuestacnx = kwargs.get('sp_fechalimitederespuestacnx')
        self.emailaddress = kwargs.get('emailaddress')
        self.sp_numerodecaso = kwargs.get('sp_numerodecaso')
        self.sp_mensajesdecorreoelecrtrnico = kwargs.get('sp_mensajesdecorreoelecrtrnico', False)
        self.sp_requiereactualizaciondelabel = kwargs.get('sp_requiereactualizaciondelabel', False)
        self.sp_tipopnc = kwargs.get('sp_tipopnc')
        self.sp_estadomigracion = kwargs.get('sp_estadomigracion')
        self.sp_medioderespuesta = kwargs.get('sp_medioderespuesta')
        self.sp_direccion = kwargs.get('sp_direccion')
        self.sp_tipodedocumento = kwargs.get('sp_tipodedocumento')
        self.timezoneruleversionnumber = kwargs.get('timezoneruleversionnumber')
        self.sp_apellidos = kwargs.get('sp_apellidos')
        self.sp_devolucioncompleja = kwargs.get('sp_devolucioncompleja', False)
        self.sp_reingresoaprobado = kwargs.get('sp_reingresoaprobado', False)
        self.sp_fechadevencimiento = kwargs.get('sp_fechadevencimiento')
        self.sp_solucionenprimercontacto = kwargs.get('sp_solucionenprimercontacto', False)
        self.sp_usuarioresponsablelocalizador = kwargs.get('sp_usuarioresponsablelocalizador')
        self.sp_ans = kwargs.get('sp_ans')
        self.sp_anomina = kwargs.get('sp_anomina', False)
        self.sp_origen = kwargs.get('sp_origen')
        self.sp_nmerodedocumentocliente = kwargs.get('sp_nmerodedocumentocliente')
        self.importsequencenumber = kwargs.get('importsequencenumber')
        self.sp_url_callcenter = kwargs.get('sp_url_callcenter')
        self.sp_telefonofijo = kwargs.get('sp_telefonofijo')
        self.statecode = kwargs.get('statecode')
        self.sp_nombredeagentequecrea = kwargs.get('sp_nombredeagentequecrea')
        self.sp_fechalimitederespuesta = kwargs.get('sp_fechalimitederespuesta')
        self.sp_clienteescuenta = kwargs.get('sp_clienteescuenta', False)
        self.sp_mensajesdetextoalcelular = kwargs.get('sp_mensajesdetextoalcelular', False)
        self.sp_nit = kwargs.get('sp_nit')
        self.statuscode = kwargs.get('statuscode')
        self.sp_consecutivo = kwargs.get('sp_consecutivo')
        self.sp_fechadiligenciamientodeinformacion = kwargs.get('sp_fechadiligenciamientodeinformacion')
        self.createdon = kwargs.get('createdon')
        self.sp_callid = kwargs.get('sp_callid')
        self.sp_nroderadicado = kwargs.get('sp_nroderadicado')
        self.sp_fechacierrecnx = kwargs.get('sp_fechacierrecnx')
        self.sp_requiereactualizaciondeboletn = kwargs.get('sp_requiereactualizaciondeboletn')
        self.sp_razonparaelestadomigracion = kwargs.get('sp_razonparaelestadomigracion')
        self.sp_clonarcaso = kwargs.get('sp_clonarcaso', False)
        
        # Campos extra (proceso de expedición)
        self.subcategoriaName = kwargs.get('subcategoriaName')
        self.BusquedaDocumentos = kwargs.get('BusquedaDocumentos', False)
        self.CantDocumentos = kwargs.get('CantDocumentos', 0)
        self.UnionDocumentos = kwargs.get('UnionDocumentos', False)
        self.alamcenadoDocumentos = kwargs.get('alamcenadoDocumentos', False)
        self.envioCorreo = kwargs.get('envioCorreo', False)
        self.cuerpoCorreo = kwargs.get('cuerpoCorreo')
        self.actualizadoCRM = kwargs.get('actualizadoCRM', False)
        
        # Campos de auditoría
        self.fecha_creacion = kwargs.get('fecha_creacion')
        self.fecha_edicion = kwargs.get('fecha_edicion')
        
        # Campo @odata.etag (no se persiste, solo para actualizaciones)
        self._odata_etag = kwargs.get('@odata.etag')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PqrsModel':
        """
        Crea una instancia del modelo desde un diccionario (respuesta de Dynamics CRM).
        
        Args:
            data: Diccionario con los datos del JSON de Dynamics CRM
            
        Returns:
            Instancia del modelo
        """
        return cls(**data)
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario para inserción en base de datos.
        Excluye campos que no se persisten en BD.
        
        Returns:
            Diccionario con los atributos para BD
        """
        result = {}
        for key, value in self.__dict__.items():
            # Excluir campos que no van a BD
            if key.startswith('_') and key != '_sp_' and not key.startswith('_sp_') and not key.startswith('_invt_') and not key.startswith('_owning') and not key.startswith('_created') and not key.startswith('_modified') and not key.startswith('_owner'):
                continue
            # Convertir None a NULL para campos opcionales
            if value is None:
                result[key] = None
            else:
                result[key] = value
        return result
    
    def get_crm_update_payload(self) -> Dict[str, Any]:
        """
        Obtiene el payload para actualizar en Dynamics CRM.
        
        Returns:
            Diccionario con los campos a actualizar en CRM
        """
        return {
            "sp_descripciondelasolucion": self.sp_descripciondelasolucion,
            "sp_resolvercaso": True
        }
