"""Cliente HTTP base para Dynamics 365 Web API con manejo de errores."""
import requests
from typing import Any

from ExpedicionCopias.core.auth import Dynamics365Authenticator


class CRMClient:
    """Cliente HTTP para realizar peticiones a Dynamics 365 Web API."""

    ENTITY_NAME = "sp_documentos"
    ID_FIELD = "sp_documentoid"
    
    # Lista completa de campos para $select (misma lista que DynamicsCrmApi/services/pqrs_service.py)
    ALL_FIELDS = [
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

    def __init__(
        self, authenticator: Dynamics365Authenticator, base_url: str
    ) -> None:
        """
        Inicializa el cliente con un autenticador y URL base.

        Args:
            authenticator: Instancia de Dynamics365Authenticator
            base_url: URL base de Dynamics 365 (ej: https://ccmadev.crm2.dynamics.com/api/data/v9.2)
        """
        self.authenticator = authenticator
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None

    def _get_token(self) -> str:
        """
        Obtiene un token válido para Dynamics 365.

        Returns:
            Token de acceso
        """
        if self._token is None:
            resource_url = self.base_url.split('/api/')[0]
            scope = f"{resource_url}/.default"
            
            if not scope.startswith("https://"):
                raise ValueError(f"Scope inválido generado: {scope}")
            
            try:
                self._token = self.authenticator.get_token(scope=scope)
            except Exception as e:
                error_msg = str(e)
                if "AADSTS7000215" in error_msg or "Invalid client secret" in error_msg:
                    raise ValueError(
                        f"Error de autenticación con Dynamics 365:\n"
                        f"  - Verifica que el secret no haya expirado\n"
                        f"  - Verifica que estés usando el Secret VALUE (no el Secret ID)\n"
                        f"  - El secret debe estar activo en Azure Portal\n"
                        f"  - Scope usado: {scope}\n"
                        f"  - Error original: {error_msg[:200]}"
                    ) from e
                raise
        return self._token

    def _get_headers(self) -> dict[str, str]:
        """
        Genera los headers necesarios para las peticiones.

        Returns:
            Diccionario con headers de autorización y contenido
        """
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Prefer": "return=representation",
        }

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Realiza una petición GET a Dynamics 365 API.

        Args:
            endpoint: Endpoint relativo (ej: "/sp_documentos")
            params: Parámetros de consulta OData opcionales

        Returns:
            Respuesta JSON como diccionario o lista

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=30,
        )

        if not response.ok:
            error_detail = self._extraer_detalle_error(response)
            if response.status_code == 403:
                error_detail = self._procesar_error_403(response, error_detail)
            raise requests.HTTPError(
                f"{response.status_code} Client Error: {response.reason} for url: {url}{error_detail}",
                response=response,
            )

        return response.json()

    def patch(self, endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Realiza una petición PATCH a Dynamics 365 API.

        Args:
            endpoint: Endpoint relativo (ej: "/sp_documentos(guid)")
            data: Datos JSON a enviar

        Returns:
            Respuesta JSON como diccionario

        Raises:
            requests.HTTPError: Si la petición falla
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.patch(
            url,
            headers=self._get_headers(),
            json=data,
            timeout=30,
        )

        if not response.ok:
            error_detail = ""
            try:
                error_json = response.json()
                error_detail = f" - {error_json.get('error', {}).get('message', '')}"
            except ValueError:
                error_detail = f" - {response.text[:200]}"
            raise requests.HTTPError(
                f"{response.status_code} Client Error: {response.reason} for url: {url}{error_detail}",
                response=response,
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def _extraer_detalle_error(self, response: requests.Response) -> str:
        """
        Extrae el detalle del error de la respuesta.

        Args:
            response: Respuesta HTTP con error

        Returns:
            String con el detalle del error
        """
        try:
            error_json = response.json()
            error_obj = error_json.get('error', {})
            error_message = error_obj.get('message', '')
            return f" - {error_message}"
        except ValueError:
            return f" - {response.text[:200]}"

    def _procesar_error_403(self, response: requests.Response, error_detail: str) -> str:
        """
        Procesa errores 403 específicos de Dynamics 365.

        Args:
            response: Respuesta HTTP con error 403
            error_detail: Detalle del error base

        Returns:
            String con el detalle del error procesado
        """
        try:
            error_json = response.json()
            error_obj = error_json.get('error', {})
            error_message = error_obj.get('message', '')
            
            if "not a member of the organization" in error_message:
                return (
                    "\n  ⚠️  La aplicación no tiene acceso al ambiente de Dynamics 365.\n"
                    "  Soluciones:\n"
                    "  1. Verifica que la aplicación tenga permisos API configurados en Azure AD\n"
                    "  2. Verifica que se hayan otorgado permisos de aplicación (Application permissions)\n"
                    "  3. Verifica que el admin haya dado consentimiento para la aplicación\n"
                    "  4. La aplicación necesita permisos en Dynamics 365 (no solo en Azure AD)\n"
                    f"  Error original: {error_message}"
                )
        except (ValueError, KeyError):
            pass
        
        return error_detail

    def consultar_casos(self, filtro: str) -> list[dict[str, Any]]:
        """
        Consulta casos en Dynamics 365 usando un filtro OData.

        Args:
            filtro: Filtro OData (ej: "sp_resolvercaso eq false and _sp_subcategoriapqrs_value eq 'guid'")

        Returns:
            Lista de casos encontrados
        """
        all_records = []
        select_fields = ",".join(self.ALL_FIELDS)
        params = {
            "$filter": filtro,
            "$select": select_fields,
            "$top": 5000,
            "$orderby": "createdon desc"
        }
        
        page = 1
        max_pages = 100
        
        while page <= max_pages:
            response = self._procesar_pagina(params)
            if not response:
                break
            
            records, next_link = response
            if not records:
                break
            
            all_records.extend(records)
            
            if not next_link:
                break
            
            params = self._parsear_next_link(next_link)
            page += 1
        
        return all_records

    def _procesar_pagina(self, params: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None] | None:
        """
        Procesa una página de resultados de la consulta.

        Args:
            params: Parámetros de consulta OData

        Returns:
            Tupla con (records, next_link) o None si hay error
        """
        endpoint = f"/{self.ENTITY_NAME}"
        response = self.get(endpoint, params=params)
        
        records = response.get("value", []) if isinstance(response, dict) else []
        next_link = response.get("@odata.nextLink")
        
        return (records, next_link)

    def _parsear_next_link(self, next_link: str) -> dict[str, Any]:
        """
        Parsea el nextLink de OData para extraer parámetros de paginación.

        Args:
            next_link: URL del nextLink de OData

        Returns:
            Diccionario con parámetros de consulta
        """
        import urllib.parse
        parsed = urllib.parse.urlparse(next_link)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        params = {}
        for key, value_list in query_params.items():
            if value_list:
                params[key] = value_list[0] if len(value_list) == 1 else value_list
        
        return params

    def obtener_caso(self, case_id: str) -> dict[str, Any]:
        """
        Obtiene un caso por su ID.

        Args:
            case_id: ID del caso (GUID)

        Returns:
            Información completa del caso
        """
        endpoint = f"/{self.ENTITY_NAME}({case_id})"
        return self.get(endpoint)

    def actualizar_caso(self, case_id: str, datos: dict[str, Any]) -> dict[str, Any]:
        """
        Actualiza un caso en Dynamics 365.

        Args:
            case_id: ID del caso (GUID)
            datos: Diccionario con los campos a actualizar

        Returns:
            Respuesta de la actualización
        """
        endpoint = f"/{self.ENTITY_NAME}({case_id})"
        return self.patch(endpoint, data=datos)
