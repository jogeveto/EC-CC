"""Motor de reglas para validación de excepciones de descarga."""
from typing import Dict, Any, List


class ExcepcionesValidator:
    """Validador de documentos contra tabla de excepciones."""

    def __init__(self, tabla_excepciones: List[Dict[str, str]]) -> None:
        """
        Inicializa el validador con la tabla de excepciones.

        Args:
            tabla_excepciones: Lista de diccionarios con 'tipoDocumento' y 'actoRegistro'
        """
        self.tabla_excepciones = tabla_excepciones or []

    def debe_descargar(self, documento: Dict[str, Any]) -> bool:
        """
        Determina si un documento debe ser descargado (no está en excepciones).

        Args:
            documento: Diccionario con los metadatos del documento de DocuWare

        Returns:
            True si debe descargarse, False si debe excluirse
        """
        tipo_documento = self._obtener_campo(documento, "TRDNOMBREDOCUMENTO")
        acto_registro = self._obtener_campo(documento, "ACTOREGISTRADO")
        
        if not tipo_documento:
            return True
        
        for excepcion in self.tabla_excepciones:
            excepcion_tipo = excepcion.get("tipoDocumento", "").strip()
            excepcion_acto = excepcion.get("actoRegistro", "").strip()
            
            # Verificar si el tipo de documento coincide
            tipo_coincide = excepcion_tipo.lower() == tipo_documento.lower()
            
            # Verificar si el acto de registro coincide:
            # - Si excepcion_acto está vacío: excluir TODOS los documentos de ese tipo (acto_coincide = True)
            # - Si excepcion_acto tiene valor: excluir solo si coincide con acto_registro del documento
            acto_coincide = (
                not excepcion_acto or 
                excepcion_acto.lower() == acto_registro.lower()
            )
            
            # Si ambos coinciden, el documento debe ser excluido
            if tipo_coincide and acto_coincide:
                return False
        
        return True

    def _obtener_campo(self, documento: Dict[str, Any], nombre_campo: str) -> str:
        """
        Obtiene el valor de un campo de los metadatos del documento.

        Args:
            documento: Diccionario con metadatos del documento
            nombre_campo: Nombre del campo a buscar

        Returns:
            Valor del campo como string, o cadena vacía si no se encuentra
        """
        fields = documento.get("Fields", [])
        for field in fields:
            if field.get("FieldName") == nombre_campo:
                item = field.get("Item")
                if item is not None:
                    return str(item).strip()
        return ""
