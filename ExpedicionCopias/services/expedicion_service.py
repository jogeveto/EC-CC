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
        self.logger.info("[INICIO] Procesamiento de copias particulares")
        
        # Cargar configuración específica de Copias
        copias_config = self.config.get("ReglasNegocio", {}).get("Copias", {})
        
        # Actualizar validadores con configuración específica
        franjas_horarias = copias_config.get("FranjasHorarias", [])
        self.time_validator = TimeValidator(franjas_horarias=franjas_horarias)
        excepciones = copias_config.get("ExcepcionesDescarga", [])
        self.excepciones_validator = ExcepcionesValidator(excepciones)
        self.docuware_client.rules_validator = self.excepciones_validator
        
        self.logger.info(f"Configuración cargada - Franjas horarias: {len(franjas_horarias)}, Excepciones: {len(excepciones)}")
        
        if not self.time_validator.debe_ejecutar():
            raise ValueError("Fuera de franja horaria o día no hábil")
        
        self.logger.info("Autenticando con DocuWare...")
        self.docuware_client.autenticar()
        self.logger.info("Autenticación con DocuWare exitosa")
        
        subcategorias = copias_config.get("Subcategorias", [])
        especificaciones = copias_config.get("Especificaciones", [])
        
        filtro = self._construir_filtro_crm(subcategorias, especificaciones)
        self.logger.info(f"Filtro CRM construido: {filtro}")
        
        casos = self.crm_client.consultar_casos(filtro)
        
        self.logger.info(f"Casos encontrados para procesar: {len(casos)}")
        
        for caso in casos:
            if not self.time_validator.debe_ejecutar():
                self.logger.warning("Fuera de franja horaria, deteniendo procesamiento")
                break
            
            case_id = caso.get('sp_documentoid', 'N/A')
            ticket_number = caso.get('sp_ticketnumber', 'N/A')
            matriculas_str = caso.get("invt_matriculasrequeridas", "") or ""
            matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
            self.logger.info(f"Procesando caso ID: {case_id}, Radicado: {ticket_number}, Matrículas: {', '.join(matriculas) if matriculas else 'N/A'}")
            
            try:
                self._procesar_caso_particular(caso)
                self.casos_procesados.append({"caso": caso, "estado": "exitoso"})
                self.logger.info(f"Caso {case_id} procesado exitosamente")
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error procesando caso {case_id}: {error_msg}")
                self.casos_error.append({"caso": caso, "estado": "error", "mensaje": error_msg})
                self._manejar_error_caso(caso, error_msg)
        
        reporte_path = self._generar_reporte_excel()
        self.logger.info(f"Reporte generado en: {reporte_path}")
        
        return {
            "casos_procesados": len(self.casos_procesados),
            "casos_error": len(self.casos_error),
            "reporte_path": reporte_path
        }

    def _procesar_caso_particular(self, caso: Dict[str, Any]) -> None:
        """Procesa un caso individual de particulares."""
        case_id = caso.get("sp_documentoid", "")
        matriculas_str = caso.get("invt_matriculasrequeridas", "") or ""
        matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
        
        self.logger.info(f"[CASO {case_id}] Iniciando procesamiento - Matrículas: {', '.join(matriculas) if matriculas else 'N/A'}")
        
        if not matriculas:
            raise ValueError("No se encontraron matrículas en el caso")
        
        ruta_temporal = tempfile.mkdtemp()
        self.logger.info(f"[CASO {case_id}] Ruta temporal creada: {ruta_temporal}")
        
        try:
            resultado_procesamiento = self._procesar_documentos_matricula(matriculas, ruta_temporal)
            documentos_descargados = resultado_procesamiento["documentos_descargados"]
            total_encontrados_docuware = resultado_procesamiento["total_encontrados_docuware"]
            total_disponibles = resultado_procesamiento["total_disponibles"]
            
            self.logger.info(f"[CASO {case_id}] Documentos descargados: {len(documentos_descargados)}")
            
            if not documentos_descargados:
                # Distinguir entre "no hay documentos" vs "todos excluidos"
                if total_encontrados_docuware == 0:
                    # No hay documentos en DocuWare - esto es un error
                    self.logger.error(f"[CASO {case_id}] No se encontraron documentos en DocuWare para las matrículas {', '.join(matriculas)}")
                    raise ValueError("No se encontraron documentos en DocuWare")
                elif total_disponibles == 0:
                    # Todos los documentos fueron excluidos por excepciones - esto NO es un error
                    self.logger.info(f"[CASO {case_id}] Todos los documentos fueron excluidos por excepciones. No se descargaron documentos (comportamiento esperado según reglas de negocio)")
                    # No generar error, simplemente terminar el procesamiento sin descargar
                    return
                else:
                    # Hay documentos disponibles pero las descargas fallaron
                    self.logger.error(f"[CASO {case_id}] No se descargaron documentos aunque había {total_disponibles} disponible(s). Todas las descargas fallaron.")
                    raise ValueError("Todas las descargas fallaron")
            
            pdf_unificado = os.path.join(ruta_temporal, f"unificado_{case_id}.pdf")
            self.logger.info(f"[CASO {case_id}] Unificando {len(documentos_descargados)} documentos en PDF: {pdf_unificado}")
            self.pdf_merger.merge_pdfs(documentos_descargados, pdf_unificado)
            
            tamanio_mb = os.path.getsize(pdf_unificado) / (1024 * 1024)
            self.logger.info(f"[CASO {case_id}] PDF unificado creado - Tamaño: {tamanio_mb:.2f} MB")
            
            subcategoria_id = caso.get("_sp_subcategoriapqrs_value", "")
            email_destino = self._obtener_email_caso(caso)
            self.logger.info(f"[CASO {case_id}] Email destino: {email_destino}, Subcategoría: {subcategoria_id}")
            
            if tamanio_mb < 28:
                self.logger.info(f"[CASO {case_id}] PDF pequeño ({tamanio_mb:.2f} MB < 28 MB) - Enviando como adjunto por email")
                cuerpo_enviado = self._enviar_pdf_pequeno(pdf_unificado, subcategoria_id, email_destino)
                self.logger.info(f"[CASO {case_id}] Email enviado exitosamente con adjunto")
            else:
                self.logger.info(f"[CASO {case_id}] PDF grande ({tamanio_mb:.2f} MB >= 28 MB) - Subiendo a OneDrive y enviando link")
                cuerpo_enviado = self._enviar_pdf_grande(pdf_unificado, case_id, subcategoria_id, email_destino)
                self.logger.info(f"[CASO {case_id}] PDF subido a OneDrive y email con link enviado exitosamente")
            
            self.logger.info(f"[CASO {case_id}] Actualizando caso en CRM...")
            self.crm_client.actualizar_caso(case_id, {
                "sp_descripciondelasolucion": cuerpo_enviado,
                "sp_resolvercaso": True
            })
            self.logger.info(f"[CASO {case_id}] Caso actualizado en CRM exitosamente")
            
            self._auditar_caso(case_id, "exitoso", "Caso procesado correctamente")
            
        finally:
            import shutil
            if os.path.exists(ruta_temporal):
                self.logger.info(f"[CASO {case_id}] Limpiando ruta temporal: {ruta_temporal}")
                shutil.rmtree(ruta_temporal, ignore_errors=True)

    def _procesar_documentos_matricula(
        self, matriculas: List[str], ruta_temporal: str
    ) -> Dict[str, Any]:
        """
        Procesa y descarga documentos para una lista de matrículas.

        Args:
            matriculas: Lista de matrículas
            ruta_temporal: Ruta temporal para descargas

        Returns:
            Diccionario con:
            - 'documentos_descargados': Lista de rutas de documentos descargados
            - 'total_encontrados_docuware': Total de documentos encontrados en DocuWare (antes del filtro)
            - 'total_disponibles': Total de documentos disponibles después del filtro
        """
        documentos_descargados = []
        total_matriculas = len(matriculas)
        total_encontrados_acumulado = 0
        total_disponibles_acumulado = 0
        
        self.logger.info(f"[DESCARGAS] Iniciando procesamiento de {total_matriculas} matrícula(s)")
        
        for idx, matricula in enumerate(matriculas, 1):
            self.logger.info(f"[DESCARGAS] Procesando matrícula {idx}/{total_matriculas}: {matricula}")
            
            resultado_busqueda = self.docuware_client.buscar_documentos(matricula)
            documentos = resultado_busqueda["documentos"]
            total_encontrados_docuware = resultado_busqueda["total_encontrados"]
            total_disponibles = resultado_busqueda["total_disponibles"]
            
            total_encontrados_acumulado += total_encontrados_docuware
            total_disponibles_acumulado += total_disponibles
            
            self.logger.info(f"[DESCARGAS] Matrícula {matricula}: {total_encontrados_docuware} documento(s) encontrado(s) en DocuWare, {total_disponibles} disponible(s) después de aplicar filtros")
            
            if total_encontrados_docuware == 0:
                self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: No se encontraron documentos en DocuWare")
            elif total_disponibles == 0:
                self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Todos los documentos fueron excluidos por excepciones (comportamiento esperado según reglas de negocio)")
            
            descargas_exitosas = 0
            descargas_fallidas = 0
            
            for doc in documentos:
                doc_id = doc.get("Id", "")
                if not doc_id:
                    self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: Documento sin ID, omitiendo")
                    continue
                
                try:
                    self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Descargando documento ID {doc_id}")
                    ruta_descarga = self.docuware_client.descargar_documento(doc_id, doc, ruta_temporal)
                    documentos_descargados.append(ruta_descarga)
                    descargas_exitosas += 1
                    self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Documento {doc_id} descargado exitosamente en {ruta_descarga}")
                except Exception as e:
                    descargas_fallidas += 1
                    self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: Error descargando documento {doc_id}: {e}")
            
            self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Resumen - Encontrados en DocuWare: {total_encontrados_docuware}, Disponibles: {total_disponibles}, Exitosos: {descargas_exitosas}, Fallidos: {descargas_fallidas}")
        
        self.logger.info(f"[DESCARGAS] Resumen general - Total matrículas: {total_matriculas}, Total documentos descargados: {len(documentos_descargados)}")
        
        return {
            "documentos_descargados": documentos_descargados,
            "total_encontrados_docuware": total_encontrados_acumulado,
            "total_disponibles": total_disponibles_acumulado
        }

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
            destinatarios=self._obtener_destinatarios_por_modo([email_destino]),
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
            destinatarios=self._obtener_destinatarios_por_modo([email_destino])
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
        self.logger.info("[INICIO] Procesamiento de copias oficiales")
        
        # Cargar configuración específica de CopiasOficiales
        copias_oficiales_config = self.config.get("ReglasNegocio", {}).get("CopiasOficiales", {})
        
        # Actualizar validadores con configuración específica
        franjas_horarias = copias_oficiales_config.get("FranjasHorarias", [])
        self.time_validator = TimeValidator(franjas_horarias=franjas_horarias)
        excepciones = copias_oficiales_config.get("ExcepcionesDescarga", [])
        self.excepciones_validator = ExcepcionesValidator(excepciones)
        self.docuware_client.rules_validator = self.excepciones_validator
        
        self.logger.info(f"Configuración cargada - Franjas horarias: {len(franjas_horarias)}, Excepciones: {len(excepciones)}")
        
        if not self.time_validator.debe_ejecutar():
            raise ValueError("Fuera de franja horaria o día no hábil")
        
        self.logger.info("Autenticando con DocuWare...")
        self.docuware_client.autenticar()
        self.logger.info("Autenticación con DocuWare exitosa")
        
        subcategorias = copias_oficiales_config.get("Subcategorias", [])
        especificaciones = copias_oficiales_config.get("Especificaciones", [])
        
        filtro = self._construir_filtro_crm(subcategorias, especificaciones)
        self.logger.info(f"Filtro CRM construido: {filtro}")
        
        casos = self.crm_client.consultar_casos(filtro)
        
        self.logger.info(f"Casos encontrados para procesar: {len(casos)}")
        
        for caso in casos:
            if not self.time_validator.debe_ejecutar():
                self.logger.warning("Fuera de franja horaria, deteniendo procesamiento")
                break
            
            case_id = caso.get('sp_documentoid', 'N/A')
            ticket_number = caso.get('sp_ticketnumber', 'N/A')
            matriculas_str = caso.get("invt_matriculasrequeridas", "") or ""
            matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
            self.logger.info(f"Procesando caso ID: {case_id}, Radicado: {ticket_number}, Matrículas: {', '.join(matriculas) if matriculas else 'N/A'}")
            
            try:
                self._procesar_caso_oficial(caso)
                self.casos_procesados.append({"caso": caso, "estado": "exitoso"})
                self.logger.info(f"Caso {case_id} procesado exitosamente")
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Error procesando caso {case_id}: {error_msg}")
                self.casos_error.append({"caso": caso, "estado": "error", "mensaje": error_msg})
                self._manejar_error_caso_oficial(caso, error_msg)
        
        reporte_path = self._generar_reporte_excel()
        self.logger.info(f"Reporte generado en: {reporte_path}")
        
        return {
            "casos_procesados": len(self.casos_procesados),
            "casos_error": len(self.casos_error),
            "reporte_path": reporte_path
        }

    def _procesar_caso_oficial(self, caso: Dict[str, Any]) -> None:
        """Procesa un caso individual de entidades oficiales."""
        case_id = caso.get("sp_documentoid", "")
        radicado = caso.get("sp_ticketnumber", "") or case_id
        matriculas_str = caso.get("invt_matriculasrequeridas", "") or ""
        matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
        
        self.logger.info(f"[CASO {case_id}] Iniciando procesamiento - Radicado: {radicado}, Matrículas: {', '.join(matriculas) if matriculas else 'N/A'}")
        
        if not matriculas:
            raise ValueError("No se encontraron matrículas en el caso")
        
        ruta_temporal = tempfile.mkdtemp()
        self.logger.info(f"[CASO {case_id}] Ruta temporal creada: {ruta_temporal}")
        
        try:
            resultado_procesamiento = self._procesar_documentos_oficiales(matriculas, ruta_temporal)
            documentos_info = resultado_procesamiento["documentos_info"]
            total_encontrados_docuware = resultado_procesamiento["total_encontrados_docuware"]
            total_disponibles = resultado_procesamiento["total_disponibles"]
            
            self.logger.info(f"[CASO {case_id}] Documentos descargados: {len(documentos_info)}")
            
            if not documentos_info:
                # Distinguir entre "no hay documentos" vs "todos excluidos"
                if total_encontrados_docuware == 0:
                    # No hay documentos en DocuWare - esto es un error
                    self.logger.error(f"[CASO {case_id}] No se encontraron documentos en DocuWare para las matrículas {', '.join(matriculas)}")
                    raise ValueError("No se encontraron documentos en DocuWare")
                elif total_disponibles == 0:
                    # Todos los documentos fueron excluidos por excepciones - esto NO es un error
                    self.logger.info(f"[CASO {case_id}] Todos los documentos fueron excluidos por excepciones. No se descargaron documentos (comportamiento esperado según reglas de negocio)")
                    # No generar error, simplemente terminar el procesamiento sin descargar
                    return
                else:
                    # Hay documentos disponibles pero las descargas fallaron
                    self.logger.error(f"[CASO {case_id}] No se descargaron documentos aunque había {total_disponibles} disponible(s). Todas las descargas fallaron.")
                    raise ValueError("Todas las descargas fallaron")
            
            self.logger.info(f"[CASO {case_id}] Organizando archivos por matrícula...")
            estructura = self.file_organizer.organizar_archivos(
                archivos=documentos_info,
                radicado=radicado,
                matriculas=matriculas,
                ruta_base=ruta_temporal
            )
            
            carpeta_organizada = estructura["ruta_base"]
            self.logger.info(f"[CASO {case_id}] Archivos organizados en: {carpeta_organizada}")
            
            self.logger.info(f"[CASO {case_id}] Subiendo carpeta a OneDrive y enviando email...")
            cuerpo_con_link = self._subir_y_enviar_carpeta_oficial(carpeta_organizada, caso)
            self.logger.info(f"[CASO {case_id}] Carpeta subida a OneDrive y email con link enviado exitosamente")
            
            self.logger.info(f"[CASO {case_id}] Actualizando caso en CRM...")
            self.crm_client.actualizar_caso(case_id, {
                "sp_descripciondelasolucion": cuerpo_con_link,
                "sp_resolvercaso": True
            })
            self.logger.info(f"[CASO {case_id}] Caso actualizado en CRM exitosamente")
            
            self._auditar_caso(case_id, "exitoso", "Caso procesado correctamente")
            
        finally:
            import shutil
            if os.path.exists(ruta_temporal):
                self.logger.info(f"[CASO {case_id}] Limpiando ruta temporal: {ruta_temporal}")
                shutil.rmtree(ruta_temporal, ignore_errors=True)

    def _procesar_documentos_oficiales(
        self, matriculas: List[str], ruta_temporal: str
    ) -> Dict[str, Any]:
        """
        Procesa y descarga documentos para entidades oficiales.

        Args:
            matriculas: Lista de matrículas
            ruta_temporal: Ruta temporal para descargas

        Returns:
            Diccionario con:
            - 'documentos_info': Lista de diccionarios con información de documentos descargados
            - 'total_encontrados_docuware': Total de documentos encontrados en DocuWare (antes del filtro)
            - 'total_disponibles': Total de documentos disponibles después del filtro
        """
        documentos_info = []
        total_matriculas = len(matriculas)
        total_encontrados_acumulado = 0
        total_disponibles_acumulado = 0
        
        self.logger.info(f"[DESCARGAS] Iniciando procesamiento de {total_matriculas} matrícula(s)")
        
        for idx, matricula in enumerate(matriculas, 1):
            self.logger.info(f"[DESCARGAS] Procesando matrícula {idx}/{total_matriculas}: {matricula}")
            
            resultado_busqueda = self.docuware_client.buscar_documentos(matricula)
            documentos = resultado_busqueda["documentos"]
            total_encontrados_docuware = resultado_busqueda["total_encontrados"]
            total_disponibles = resultado_busqueda["total_disponibles"]
            
            total_encontrados_acumulado += total_encontrados_docuware
            total_disponibles_acumulado += total_disponibles
            
            self.logger.info(f"[DESCARGAS] Matrícula {matricula}: {total_encontrados_docuware} documento(s) encontrado(s) en DocuWare, {total_disponibles} disponible(s) después de aplicar filtros")
            
            if total_encontrados_docuware == 0:
                self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: No se encontraron documentos en DocuWare")
            elif total_disponibles == 0:
                self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Todos los documentos fueron excluidos por excepciones (comportamiento esperado según reglas de negocio)")
            
            descargas_exitosas = 0
            descargas_fallidas = 0
            
            for doc in documentos:
                doc_id = doc.get("Id", "")
                if not doc_id:
                    self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: Documento sin ID, omitiendo")
                    continue
                
                try:
                    self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Descargando documento ID {doc_id}")
                    ruta_descarga = self.docuware_client.descargar_documento(doc_id, doc, ruta_temporal)
                    tipo_doc = self._obtener_tipo_documento(doc)
                    documentos_info.append({
                        "ruta": ruta_descarga,
                        "tipoDocumento": tipo_doc,
                        "documento": doc
                    })
                    descargas_exitosas += 1
                    self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Documento {doc_id} (tipo: {tipo_doc}) descargado exitosamente en {ruta_descarga}")
                except Exception as e:
                    descargas_fallidas += 1
                    self.logger.warning(f"[DESCARGAS] Matrícula {matricula}: Error descargando documento {doc_id}: {e}")
            
            self.logger.info(f"[DESCARGAS] Matrícula {matricula}: Resumen - Encontrados en DocuWare: {total_encontrados_docuware}, Disponibles: {total_disponibles}, Exitosos: {descargas_exitosas}, Fallidos: {descargas_fallidas}")
        
        self.logger.info(f"[DESCARGAS] Resumen general - Total matrículas: {total_matriculas}, Total documentos descargados: {len(documentos_info)}")
        
        return {
            "documentos_info": documentos_info,
            "total_encontrados_docuware": total_encontrados_acumulado,
            "total_disponibles": total_disponibles_acumulado
        }

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
            destinatarios=self._obtener_destinatarios_por_modo([email_creador])
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

    def _obtener_destinatarios_por_modo(self, destinatarios_originales: List[str]) -> List[str]:
        """
        Determina los destinatarios según el modo configurado (QA/PROD).
        
        Args:
            destinatarios_originales: Lista de emails destinatarios originales
            
        Returns:
            Lista de emails destinatarios (emailQa si modo es QA, originales si es PROD)
            
        Raises:
            ValueError: Si modo es QA y emailQa no está configurado
        """
        globales_config = self.config.get("Globales", {})
        modo = globales_config.get("modo", "PROD")
        
        # Validar modo
        modo_upper = modo.upper() if isinstance(modo, str) else "PROD"
        if modo_upper not in ["QA", "PROD"]:
            self.logger.warning(f"Modo inválido '{modo}', usando PROD por defecto")
            modo_upper = "PROD"
        
        # Si es PROD, retornar destinatarios originales
        if modo_upper == "PROD":
            return destinatarios_originales
        
        # Si es QA, validar y usar emailQa
        email_qa = globales_config.get("emailQa", "")
        if not email_qa:
            error_msg = "Modo QA configurado pero 'emailQa' no está definido en la sección Globales"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log cuando se redirige a QA
        destinatarios_str = ", ".join(destinatarios_originales) if destinatarios_originales else "N/A"
        self.logger.info(f"[MODO QA] Redirigiendo correo de destinatarios originales ({destinatarios_str}) a {email_qa}")
        
        return [email_qa]

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
                destinatarios=self._obtener_destinatarios_por_modo([email])
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
