"""Servicio de orquestación para expedición de copias."""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from shared.utils.logger import get_logger
from ExpedicionCopias.core.crm_client import CRMClient
from ExpedicionCopias.core.docuware_client import DocuWareClient
from ExpedicionCopias.core.graph_client import GraphClient
from ExpedicionCopias.core.pdf_processor import PDFMerger
from ExpedicionCopias.core.file_organizer import FileOrganizer
from ExpedicionCopias.core.rules_engine import ExcepcionesValidator
from ExpedicionCopias.core.time_validator import TimeValidator
from ExpedicionCopias.core.auth import Dynamics365Authenticator, AzureAuthenticator


class ExpedicionService:
    """Servicio principal para orquestar el proceso de expedición de copias."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Inicializa el servicio con configuración.

        Args:
            config: Diccionario con toda la configuración
        """
        self.config = config
        self.logger = get_logger("ExpedicionService")
        
        self.casos_procesados: List[Dict[str, Any]] = []
        self.casos_error: List[Dict[str, Any]] = []
        
        self._inicializar_clientes()
        self._inicializar_validadores()

    def _inicializar_clientes(self) -> None:
        """Inicializa los clientes de CRM, DocuWare y Graph."""
        dynamics_config = self.config.get("Dynamics365", {})
        graph_config = self.config.get("GraphAPI", {})
        
        dynamics_client_secret = self.config.get("dynamics_client_secret", "")
        graph_client_secret = self.config.get("graph_client_secret", "")
        
        if not dynamics_client_secret:
            raise ValueError("dynamics_client_secret no está configurado")
        if not graph_client_secret:
            raise ValueError("graph_client_secret no está configurado")
        
        dynamics_auth = Dynamics365Authenticator(
            tenant_id=dynamics_config.get("tenant_id", ""),
            client_id=dynamics_config.get("client_id", ""),
            client_secret=dynamics_client_secret
        )
        
        graph_auth = AzureAuthenticator(
            tenant_id=graph_config.get("tenant_id", ""),
            client_id=graph_config.get("client_id", ""),
            client_secret=graph_client_secret
        )
        
        self.crm_client = CRMClient(
            authenticator=dynamics_auth,
            base_url=dynamics_config.get("base_url", "")
        )
        
        self.graph_client = GraphClient(authenticator=graph_auth)
        
        # Las excepciones se cargarán desde la sección específica, inicializar con lista vacía
        rules_validator = ExcepcionesValidator([])
        
        self.docuware_client = DocuWareClient(
            config=self.config,
            rules_validator=rules_validator
        )

    def _inicializar_validadores(self) -> None:
        """Inicializa validadores de tiempo y reglas."""
        # Las franjas horarias y excepciones se cargarán desde la sección específica (Copias o CopiasOficiales)
        # Se inicializan con valores por defecto, se actualizarán en procesar_particulares/procesar_oficiales
        self.time_validator = TimeValidator(franjas_horarias=[])
        self.excepciones_validator = ExcepcionesValidator([])
        
        self.pdf_merger = PDFMerger()
        self.file_organizer = FileOrganizer()

    def procesar_particulares(self) -> Dict[str, Any]:
        """
        Procesa casos de COPIAS (particulares).

        Returns:
            Diccionario con resultados del proceso
        """
        # Cargar configuración específica de Copias
        copias_config = self.config.get("ReglasNegocio", {}).get("Copias", {})
        
        # Actualizar validadores con configuración específica
        franjas_horarias = copias_config.get("FranjasHorarias", [])
        self.time_validator = TimeValidator(franjas_horarias=franjas_horarias)
        excepciones = copias_config.get("ExcepcionesDescarga", [])
        self.excepciones_validator = ExcepcionesValidator(excepciones)
        self.docuware_client.rules_validator = self.excepciones_validator
        
        if not self.time_validator.debe_ejecutar():
            raise ValueError("Fuera de franja horaria o día no hábil")
        
        self.docuware_client.autenticar()
        
        subcategorias = copias_config.get("Subcategorias", [])
        especificaciones = copias_config.get("Especificaciones", [])
        
        filtro = self._construir_filtro_crm(subcategorias, especificaciones)
        casos = self.crm_client.consultar_casos(filtro)
        
        self.logger.info(f"Casos encontrados para procesar: {len(casos)}")
        
        for caso in casos:
            if not self.time_validator.debe_ejecutar():
                self.logger.warning("Fuera de franja horaria, deteniendo procesamiento")
                break
            
            try:
                self._procesar_caso_particular(caso)
                self.casos_procesados.append({"caso": caso, "estado": "exitoso"})
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error procesando caso {caso.get('sp_documentoid', 'N/A')}: {error_msg}")
                self.casos_error.append({"caso": caso, "estado": "error", "mensaje": error_msg})
                self._manejar_error_caso(caso, error_msg)
        
        reporte_path = self._generar_reporte_excel()
        
        return {
            "casos_procesados": len(self.casos_procesados),
            "casos_error": len(self.casos_error),
            "reporte_path": reporte_path
        }

    def _procesar_caso_particular(self, caso: Dict[str, Any]) -> None:
        """Procesa un caso individual de particulares."""
        case_id = caso.get("sp_documentoid", "")
        matriculas_str = caso.get("sp_matricula", "") or ""
        matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
        
        if not matriculas:
            raise ValueError("No se encontraron matrículas en el caso")
        
        ruta_temporal = tempfile.mkdtemp()
        
        try:
            documentos_descargados = self._procesar_documentos_matricula(matriculas, ruta_temporal)
            
            if not documentos_descargados:
                raise ValueError("No se descargaron documentos")
            
            pdf_unificado = os.path.join(ruta_temporal, f"unificado_{case_id}.pdf")
            self.pdf_merger.merge_pdfs(documentos_descargados, pdf_unificado)
            
            tamanio_mb = os.path.getsize(pdf_unificado) / (1024 * 1024)
            subcategoria_id = caso.get("_sp_subcategoriapqrs_value", "")
            email_destino = self._obtener_email_caso(caso)
            
            if tamanio_mb < 28:
                cuerpo_enviado = self._enviar_pdf_pequeno(pdf_unificado, subcategoria_id, email_destino)
            else:
                cuerpo_enviado = self._enviar_pdf_grande(pdf_unificado, case_id, subcategoria_id, email_destino)
            
            self.crm_client.actualizar_caso(case_id, {
                "sp_descripciondelasolucion": cuerpo_enviado,
                "sp_resolvercaso": True
            })
            
            self._auditar_caso(case_id, "exitoso", "Caso procesado correctamente")
            
        finally:
            import shutil
            if os.path.exists(ruta_temporal):
                shutil.rmtree(ruta_temporal, ignore_errors=True)

    def _procesar_documentos_matricula(
        self, matriculas: List[str], ruta_temporal: str
    ) -> List[str]:
        """
        Procesa y descarga documentos para una lista de matrículas.

        Args:
            matriculas: Lista de matrículas
            ruta_temporal: Ruta temporal para descargas

        Returns:
            Lista de rutas de documentos descargados
        """
        documentos_descargados = []
        
        for matricula in matriculas:
            documentos = self.docuware_client.buscar_documentos(matricula)
            
            for doc in documentos:
                doc_id = doc.get("Id", "")
                if not doc_id:
                    continue
                
                try:
                    ruta_descarga = self.docuware_client.descargar_documento(doc_id, doc, ruta_temporal)
                    documentos_descargados.append(ruta_descarga)
                except Exception as e:
                    self.logger.warning(f"Error descargando documento {doc_id}: {e}")
        
        return documentos_descargados

    def _enviar_pdf_pequeno(
        self, pdf_unificado: str, subcategoria_id: str, email_destino: str
    ) -> str:
        """
        Envía PDF pequeño (< 28MB) como adjunto por email.

        Args:
            pdf_unificado: Ruta del PDF unificado
            subcategoria_id: ID de la subcategoría
            email_destino: Email del destinatario

        Returns:
            Cuerpo del email enviado
        """
        plantilla = self._obtener_plantilla_email("Copias", subcategoria_id, "adjunto")
        self.graph_client.enviar_email(
            usuario_id=self.config.get("GraphAPI", {}).get("user_email", ""),
            asunto=plantilla["asunto"],
            cuerpo=plantilla["cuerpo"],
            destinatarios=[email_destino],
            adjuntos=[pdf_unificado]
        )
        return plantilla["cuerpo"]

    def _enviar_pdf_grande(
        self, pdf_unificado: str, case_id: str, subcategoria_id: str, email_destino: str
    ) -> str:
        """
        Envía PDF grande (>= 28MB) subiéndolo a OneDrive y compartiendo link.

        Args:
            pdf_unificado: Ruta del PDF unificado
            case_id: ID del caso
            subcategoria_id: ID de la subcategoría
            email_destino: Email del destinatario

        Returns:
            Cuerpo del email enviado con link
        """
        carpeta_base = self.config.get("OneDrive", {}).get("carpetaBase", "/ExpedicionCopias")
        usuario_email = self.config.get("GraphAPI", {}).get("user_email", "")
        
        self.graph_client.subir_a_onedrive(
            ruta_local=pdf_unificado,
            carpeta_destino=f"{carpeta_base}/Particulares/{case_id}",
            usuario_id=usuario_email
        )
        
        info_item = self.graph_client._obtener_info_carpeta(
            f"{carpeta_base}/Particulares/{case_id}/{Path(pdf_unificado).name}",
            usuario_email
        )
        item_id = info_item.get("id", "")
        
        link_info = self.graph_client.compartir_carpeta(item_id, usuario_email)
        link = link_info.get("link", "")
        
        plantilla = self._obtener_plantilla_email("Copias", subcategoria_id, "onedrive")
        cuerpo_con_link = plantilla["cuerpo"].replace("{link}", link)
        
        self.graph_client.enviar_email(
            usuario_id=usuario_email,
            asunto=plantilla["asunto"],
            cuerpo=cuerpo_con_link,
            destinatarios=[email_destino]
        )
        
        return cuerpo_con_link

    def _manejar_error_caso(self, caso: Dict[str, Any], error_msg: str) -> None:
        """
        Maneja el error de un caso enviando email si es posible.

        Args:
            caso: Diccionario con información del caso
            error_msg: Mensaje de error
        """
        try:
            email_destino = self._obtener_email_caso(caso)
            if email_destino:
                self._enviar_email_error_caso(email_destino, caso, error_msg)
        except Exception as email_error:
            self.logger.error(f"Error enviando email de error: {email_error}")

    def procesar_oficiales(self) -> Dict[str, Any]:
        """
        Procesa casos de COPIAS ENTIDADES OFICIALES.

        Returns:
            Diccionario con resultados del proceso
        """
        # Cargar configuración específica de CopiasOficiales
        copias_oficiales_config = self.config.get("ReglasNegocio", {}).get("CopiasOficiales", {})
        
        # Actualizar validadores con configuración específica
        franjas_horarias = copias_oficiales_config.get("FranjasHorarias", [])
        self.time_validator = TimeValidator(franjas_horarias=franjas_horarias)
        excepciones = copias_oficiales_config.get("ExcepcionesDescarga", [])
        self.excepciones_validator = ExcepcionesValidator(excepciones)
        self.docuware_client.rules_validator = self.excepciones_validator
        
        if not self.time_validator.debe_ejecutar():
            raise ValueError("Fuera de franja horaria o día no hábil")
        
        self.docuware_client.autenticar()
        
        subcategorias = copias_oficiales_config.get("Subcategorias", [])
        especificaciones = copias_oficiales_config.get("Especificaciones", [])
        
        filtro = self._construir_filtro_crm(subcategorias, especificaciones)
        casos = self.crm_client.consultar_casos(filtro)
        
        self.logger.info(f"Casos encontrados para procesar: {len(casos)}")
        
        for caso in casos:
            if not self.time_validator.debe_ejecutar():
                self.logger.warning("Fuera de franja horaria, deteniendo procesamiento")
                break
            
            try:
                self._procesar_caso_oficial(caso)
                self.casos_procesados.append({"caso": caso, "estado": "exitoso"})
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error procesando caso {caso.get('sp_documentoid', 'N/A')}: {error_msg}")
                self.casos_error.append({"caso": caso, "estado": "error", "mensaje": error_msg})
                self._manejar_error_caso_oficial(caso, error_msg)
        
        reporte_path = self._generar_reporte_excel()
        
        return {
            "casos_procesados": len(self.casos_procesados),
            "casos_error": len(self.casos_error),
            "reporte_path": reporte_path
        }

    def _procesar_caso_oficial(self, caso: Dict[str, Any]) -> None:
        """Procesa un caso individual de entidades oficiales."""
        case_id = caso.get("sp_documentoid", "")
        radicado = caso.get("sp_ticketnumber", "") or case_id
        matriculas_str = caso.get("sp_matricula", "") or ""
        matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
        
        if not matriculas:
            raise ValueError("No se encontraron matrículas en el caso")
        
        ruta_temporal = tempfile.mkdtemp()
        
        try:
            documentos_info = self._procesar_documentos_oficiales(matriculas, ruta_temporal)
            
            if not documentos_info:
                raise ValueError("No se descargaron documentos")
            
            estructura = self.file_organizer.organizar_archivos(
                archivos=documentos_info,
                radicado=radicado,
                matriculas=matriculas,
                ruta_base=ruta_temporal
            )
            
            carpeta_organizada = estructura["ruta_base"]
            cuerpo_con_link = self._subir_y_enviar_carpeta_oficial(carpeta_organizada, caso)
            
            self.crm_client.actualizar_caso(case_id, {
                "sp_descripciondelasolucion": cuerpo_con_link,
                "sp_resolvercaso": True
            })
            
            self._auditar_caso(case_id, "exitoso", "Caso procesado correctamente")
            
        finally:
            import shutil
            if os.path.exists(ruta_temporal):
                shutil.rmtree(ruta_temporal, ignore_errors=True)

    def _procesar_documentos_oficiales(
        self, matriculas: List[str], ruta_temporal: str
    ) -> List[Dict[str, Any]]:
        """
        Procesa y descarga documentos para entidades oficiales.

        Args:
            matriculas: Lista de matrículas
            ruta_temporal: Ruta temporal para descargas

        Returns:
            Lista de diccionarios con información de documentos descargados
        """
        documentos_info = []
        
        for matricula in matriculas:
            documentos = self.docuware_client.buscar_documentos(matricula)
            
            for doc in documentos:
                doc_id = doc.get("Id", "")
                if not doc_id:
                    continue
                
                try:
                    ruta_descarga = self.docuware_client.descargar_documento(doc_id, doc, ruta_temporal)
                    tipo_doc = self._obtener_tipo_documento(doc)
                    documentos_info.append({
                        "ruta": ruta_descarga,
                        "tipoDocumento": tipo_doc,
                        "documento": doc
                    })
                except Exception as e:
                    self.logger.warning(f"Error descargando documento {doc_id}: {e}")
        
        return documentos_info

    def _subir_y_enviar_carpeta_oficial(
        self, carpeta_organizada: str, caso: Dict[str, Any]
    ) -> str:
        """
        Sube carpeta a OneDrive y envía email con link.

        Args:
            carpeta_organizada: Ruta de la carpeta organizada
            caso: Diccionario con información del caso

        Returns:
            Cuerpo del email enviado con link
        """
        carpeta_base = self.config.get("OneDrive", {}).get("carpetaBase", "/ExpedicionCopias")
        usuario_email = self.config.get("GraphAPI", {}).get("user_email", "")
        
        info_carpeta = self.graph_client.subir_carpeta_completa(
            ruta_carpeta_local=carpeta_organizada,
            carpeta_destino=f"{carpeta_base}/Oficiales",
            usuario_id=usuario_email
        )
        
        carpeta_id = info_carpeta.get("id", "")
        link_info = self.graph_client.compartir_carpeta(carpeta_id, usuario_email)
        link = link_info.get("link", "")
        
        plantilla = self._obtener_plantilla_email("CopiasOficiales")
        cuerpo_con_link = plantilla["cuerpo"].replace("{link}", link)
        email_creador = self._obtener_email_creador(caso)
        
        self.graph_client.enviar_email(
            usuario_id=usuario_email,
            asunto=plantilla["asunto"],
            cuerpo=cuerpo_con_link,
            destinatarios=[email_creador]
        )
        
        return cuerpo_con_link

    def _manejar_error_caso_oficial(self, caso: Dict[str, Any], error_msg: str) -> None:
        """
        Maneja el error de un caso oficial enviando email si es posible.

        Args:
            caso: Diccionario con información del caso
            error_msg: Mensaje de error
        """
        try:
            email_destino = self._obtener_email_creador(caso)
            if email_destino:
                self._enviar_email_error_caso(email_destino, caso, error_msg)
        except Exception as email_error:
            self.logger.error(f"Error enviando email de error: {email_error}")

    def _construir_filtro_crm(self, subcategorias: List[str], especificaciones: List[str]) -> str:
        """Construye el filtro OData para consultar casos en CRM."""
        condiciones_subcat = " or ".join([
            f"_sp_subcategoriapqrs_value eq '{subcat_id}'" for subcat_id in subcategorias
        ])
        filtro_subcat = f"({condiciones_subcat})" if subcategorias else ""
        
        condiciones_espec = " or ".join([
            f"_invt_especificacion_value eq '{espec_id}'" for espec_id in especificaciones
        ])
        filtro_espec = f"({condiciones_espec})" if especificaciones else ""
        
        partes = []
        if filtro_subcat:
            partes.append(filtro_subcat)
        if filtro_espec:
            partes.append(filtro_espec)
        
        partes.append("sp_resolvercaso eq false")
        
        return " and ".join(partes)

    def _obtener_plantilla_email(
        self, tipo: str, subcategoria_id: str = "", variante: str = ""
    ) -> Dict[str, str]:
        """Obtiene la plantilla de email según el tipo y variante."""
        if tipo == "CopiasOficiales":
            copias_oficiales_config = self.config.get("ReglasNegocio", {}).get("CopiasOficiales", {})
            plantillas = copias_oficiales_config.get("PlantillasEmail", {})
            return plantillas.get("default", {"asunto": "", "cuerpo": ""})
        
        if tipo == "Copias":
            copias_config = self.config.get("ReglasNegocio", {}).get("Copias", {})
            plantillas = copias_config.get("PlantillasEmail", {})
            plantilla_subcat = plantillas.get(subcategoria_id, {})
            return plantilla_subcat.get(variante, {"asunto": "", "cuerpo": ""})
        
        return {"asunto": "", "cuerpo": ""}

    def _obtener_email_caso(self, caso: Dict[str, Any]) -> str:
        """Obtiene el email del caso desde los campos del CRM."""
        # Prioridad: sp_correoelectronico, emailaddress, emailaddress1
        return (
            caso.get("sp_correoelectronico", "") 
            or caso.get("emailaddress", "") 
            or caso.get("emailaddress1", "") 
            or ""
        )

    def _obtener_email_creador(self, caso: Dict[str, Any]) -> str:
        """Obtiene el email del creador/dueño del caso desde el CRM."""
        # Para entidades oficiales, se usa el ownerid (dueño del caso)
        owner_id = caso.get("_ownerid_value", "") or caso.get("_createdby_value", "")
        if not owner_id:
            return ""
        
        # En una implementación real, habría que consultar el CRM para obtener el email del usuario
        # Por ahora retornamos el ID como placeholder
        return owner_id

    def _obtener_tipo_documento(self, documento: Dict[str, Any]) -> str:
        """Obtiene el tipo de documento de los metadatos."""
        fields = documento.get("Fields", [])
        for field in fields:
            if field.get("FieldName") == "TRDNOMBREDOCUMENTO":
                item = field.get("Item")
                if item:
                    return str(item)
        return "SinTipo"

    def _enviar_email_error_caso(self, email: str, caso: Dict[str, Any], mensaje: str) -> None:
        """Envía email de error para un caso individual."""
        try:
            asunto = f"Error en procesamiento de caso {caso.get('sp_ticketnumber', 'N/A')}"
            cuerpo = f"<html><body><p>Estimado/a,</p><p>Se presentó un error al procesar su caso:</p><p>{mensaje}</p><p>Por favor contacte al administrador.</p></body></html>"
            
            self.graph_client.enviar_email(
                usuario_id=self.config.get("GraphAPI", {}).get("user_email", ""),
                asunto=asunto,
                cuerpo=cuerpo,
                destinatarios=[email]
            )
        except Exception as e:
            self.logger.error(f"Error enviando email de error: {e}")

    def _auditar_caso(self, case_id: str, estado: str, mensaje: str) -> None:
        """Stub para auditoría (no implementado por ahora)."""
        self.logger.info(f"Auditoría (stub): Caso {case_id} - {estado} - {mensaje}")

    def _generar_reporte_excel(self) -> str:
        """Genera reporte Excel con los casos procesados."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte Expedición Copias"
        
        headers = ["ID Caso", "Radicado", "Estado", "Fecha Procesamiento", "Observaciones"]
        ws.append(headers)
        
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        for item in self.casos_procesados:
            caso = item.get("caso", {})
            ws.append([
                caso.get("sp_documentoid", ""),
                caso.get("sp_ticketnumber", ""),
                "Exitoso",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Procesado correctamente"
            ])
        
        for item in self.casos_error:
            caso = item.get("caso", {})
            ws.append([
                caso.get("sp_documentoid", ""),
                caso.get("sp_ticketnumber", ""),
                "Error",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                item.get("mensaje", "")
            ])
        
        self._ajustar_ancho_columnas(ws)
        
        ruta_base = self.config.get("Globales", {}).get("RutaBaseProyecto", ".")
        reportes_dir = Path(ruta_base) / "reportes"
        reportes_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte_path = reportes_dir / f"reporte_expedicion_{timestamp}.xlsx"
        wb.save(str(reporte_path))
        
        return str(reporte_path)

    def _ajustar_ancho_columnas(self, ws: Any) -> None:
        """
        Ajusta el ancho de las columnas del worksheet según su contenido.

        Args:
            ws: Worksheet de openpyxl a ajustar
        """
        for col in ws.columns:
            max_length = self._calcular_ancho_maximo_columna(col)
            column = col[0].column_letter
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width

    def _calcular_ancho_maximo_columna(self, col: Any) -> int:
        """
        Calcula el ancho máximo necesario para una columna.

        Args:
            col: Columna del worksheet

        Returns:
            Ancho máximo encontrado en la columna
        """
        max_length = 0
        for cell in col:
            try:
                cell_length = len(str(cell.value))
                if cell_length > max_length:
                    max_length = cell_length
            except Exception:
                pass
        return max_length
