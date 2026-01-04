"""Procesador de PDFs para merge y ordenamiento."""
from pathlib import Path
from typing import List
from pypdf import PdfReader, PdfWriter
import re


class PDFMerger:
    """Clase para unificar múltiples PDFs en uno solo."""

    def merge_pdfs(
        self, rutas_pdfs: List[str], ruta_salida: str
    ) -> str:
        """
        Une múltiples PDFs en uno solo, ordenados por fecha (más antiguo primero).

        Args:
            rutas_pdfs: Lista de rutas a archivos PDF
            ruta_salida: Ruta donde se guardará el PDF unificado

        Returns:
            Ruta del archivo PDF unificado creado

        Raises:
            FileNotFoundError: Si algún archivo PDF no existe
            ValueError: Si no hay PDFs para unificar
        """
        if not rutas_pdfs:
            raise ValueError("No hay archivos PDF para unificar")
        
        rutas_validas = [Path(ruta) for ruta in rutas_pdfs if Path(ruta).exists()]
        if not rutas_validas:
            raise ValueError("No se encontraron archivos PDF válidos")
        
        rutas_ordenadas = self._ordenar_por_fecha(rutas_validas)
        
        writer = PdfWriter()
        
        for ruta_pdf in rutas_ordenadas:
            try:
                reader = PdfReader(str(ruta_pdf))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                raise ValueError(f"Error procesando PDF {ruta_pdf}: {e}") from e
        
        ruta_salida_path = Path(ruta_salida)
        ruta_salida_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_salida_path, "wb") as output_file:
            writer.write(output_file)
        
        return ruta_salida

    def _ordenar_por_fecha(self, rutas: List[Path]) -> List[Path]:
        """
        Ordena las rutas de PDFs por fecha (más antiguo primero).

        Args:
            rutas: Lista de rutas a archivos PDF

        Returns:
            Lista de rutas ordenadas por fecha de modificación
        """
        return sorted(rutas, key=lambda p: p.stat().st_mtime)
