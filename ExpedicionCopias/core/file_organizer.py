"""Organizador de archivos por estructura Radicado/Matricula/TipoDocumento."""
from pathlib import Path
from typing import Dict, Any, List
import shutil


class FileOrganizer:
    """Organizador de archivos en estructura de carpetas por matrícula y tipo."""

    def organizar_archivos(
        self,
        archivos: List[Dict[str, Any]],
        radicado: str,
        matriculas: List[str],
        ruta_base: str,
    ) -> Dict[str, Any]:
        """
        Organiza archivos en estructura Radicado/Matricula/TipoDocumento/.

        Args:
            archivos: Lista de diccionarios con información de archivos (ruta, tipoDocumento, etc.)
            radicado: Número de radicado del CRM
            matriculas: Lista de matrículas (separadas por comas en el campo del CRM)
            ruta_base: Ruta base donde se creará la estructura

        Returns:
            Diccionario con información de la estructura creada y rutas organizadas
        """
        ruta_base_path = Path(ruta_base)
        ruta_radicado = ruta_base_path / self._sanitizar_nombre(radicado)
        ruta_radicado.mkdir(parents=True, exist_ok=True)
        
        estructura_creada: Dict[str, Any] = {
            "ruta_base": str(ruta_radicado),
            "matriculas": {}
        }
        
        for matricula in matriculas:
            matricula_clean = matricula.strip()
            if not matricula_clean:
                continue
            
            estructura_matricula = self._organizar_por_matricula(
                archivos, matricula_clean, ruta_radicado
            )
            estructura_creada["matriculas"][matricula_clean] = estructura_matricula
        
        return estructura_creada

    def _organizar_por_matricula(
        self,
        archivos: List[Dict[str, Any]],
        matricula_clean: str,
        ruta_radicado: Path
    ) -> Dict[str, Any]:
        """
        Organiza archivos para una matrícula específica.

        Args:
            archivos: Lista de archivos a organizar
            matricula_clean: Matrícula limpia
            ruta_radicado: Ruta base del radicado

        Returns:
            Diccionario con estructura de la matrícula
        """
        ruta_matricula = ruta_radicado / self._sanitizar_nombre(matricula_clean)
        ruta_matricula.mkdir(parents=True, exist_ok=True)
        
        # Filtrar archivos que pertenecen a esta matrícula
        archivos_matricula = [
            archivo for archivo in archivos 
            if archivo.get("matricula", "").strip() == matricula_clean
        ]
        
        tipos_documento = self._agrupar_por_tipo_documento(archivos_matricula)
        
        estructura_matricula: Dict[str, Any] = {
            "ruta": str(ruta_matricula),
            "tipos": {}
        }
        
        for tipo_doc, archivos_tipo in tipos_documento.items():
            estructura_tipo = self._procesar_tipo_documento(
                archivos_tipo, tipo_doc, ruta_matricula
            )
            estructura_matricula["tipos"][tipo_doc] = estructura_tipo
        
        return estructura_matricula

    def _agrupar_por_tipo_documento(
        self, archivos: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupa archivos por tipo de documento.

        Args:
            archivos: Lista de archivos a agrupar

        Returns:
            Diccionario con tipos de documento como clave y lista de archivos como valor
        """
        tipos_documento: Dict[str, List[Dict[str, Any]]] = {}
        
        for archivo in archivos:
            tipo_doc = self._obtener_tipo_documento(archivo)
            if tipo_doc not in tipos_documento:
                tipos_documento[tipo_doc] = []
            tipos_documento[tipo_doc].append(archivo)
        
        return tipos_documento

    def _procesar_tipo_documento(
        self,
        archivos_tipo: List[Dict[str, Any]],
        tipo_doc: str,
        ruta_matricula: Path
    ) -> Dict[str, Any]:
        """
        Procesa archivos de un tipo de documento específico.

        Args:
            archivos_tipo: Lista de archivos del tipo
            tipo_doc: Tipo de documento
            ruta_matricula: Ruta de la matrícula

        Returns:
            Diccionario con información del tipo procesado
        """
        ruta_tipo = ruta_matricula / self._sanitizar_nombre(tipo_doc)
        ruta_tipo.mkdir(parents=True, exist_ok=True)
        
        archivos_ordenados = self._ordenar_por_fecha(archivos_tipo)
        archivos_renombrados = []
        
        for idx, archivo in enumerate(archivos_ordenados, start=1):
            archivo_info = self._copiar_archivo_renombrado(archivo, tipo_doc, idx, ruta_tipo)
            if archivo_info:
                archivos_renombrados.append(archivo_info)
        
        return {
            "ruta": str(ruta_tipo),
            "archivos": archivos_renombrados
        }

    def _copiar_archivo_renombrado(
        self,
        archivo: Dict[str, Any],
        tipo_doc: str,
        idx: int,
        ruta_tipo: Path
    ) -> Dict[str, Any] | None:
        """
        Copia y renombra un archivo.

        Args:
            archivo: Diccionario con información del archivo
            tipo_doc: Tipo de documento
            idx: Índice del archivo
            ruta_tipo: Ruta del tipo de documento

        Returns:
            Diccionario con información del archivo copiado o None si no existe
        """
        nombre_nuevo = f"{tipo_doc} {idx}"
        extension = Path(archivo.get("ruta", "")).suffix
        if not extension:
            extension = ".pdf"
        
        ruta_archivo_origen = Path(archivo.get("ruta", ""))
        if not ruta_archivo_origen.exists():
            return None
        
        ruta_archivo_destino = ruta_tipo / f"{nombre_nuevo}{extension}"
        shutil.copy2(ruta_archivo_origen, ruta_archivo_destino)
        
        return {
            "original": str(ruta_archivo_origen),
            "nuevo": str(ruta_archivo_destino),
            "nombre": f"{nombre_nuevo}{extension}"
        }

    def _sanitizar_nombre(self, nombre: str) -> str:
        """
        Sanitiza un nombre para usarlo como nombre de carpeta/archivo.

        Args:
            nombre: Nombre a sanitizar

        Returns:
            Nombre sanitizado
        """
        nombre_limpio = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in nombre
        )
        while "__" in nombre_limpio:
            nombre_limpio = nombre_limpio.replace("__", "_")
        return nombre_limpio.strip("_")

    def _obtener_tipo_documento(self, archivo: Dict[str, Any]) -> str:
        """
        Obtiene el tipo de documento de los metadatos.

        Args:
            archivo: Diccionario con información del archivo

        Returns:
            Tipo de documento o "SinTipo" si no se encuentra
        """
        tipo_doc = archivo.get("tipoDocumento") or archivo.get("TRDNOMBREDOCUMENTO", "")
        if not tipo_doc:
            tipo_doc = "SinTipo"
        return str(tipo_doc).strip()

    def _ordenar_por_fecha(self, archivos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ordena archivos por fecha (más antiguo primero).

        Args:
            archivos: Lista de diccionarios con información de archivos

        Returns:
            Lista de archivos ordenados por fecha
        """
        def obtener_fecha(archivo: Dict[str, Any]) -> float:
            ruta = archivo.get("ruta", "")
            if ruta and Path(ruta).exists():
                return Path(ruta).stat().st_mtime
            return 0.0
        
        return sorted(archivos, key=obtener_fecha)
