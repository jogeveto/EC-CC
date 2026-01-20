"""Validador de reglas no críticas para expedición de copias."""
import re
from typing import Dict, Any, Optional, Tuple
from ExpedicionCopias.core.constants import (
    CAMPO_RADICADO_PRINCIPAL, CAMPO_EMAIL_PARTICULARES, CAMPO_MATRICULAS,
    MSG_EMAIL_VACIO, MSG_EMAIL_INVALIDO, MSG_RADICADO_NO_EXTRAIDO,
    MSG_MATRICULAS_NO_EXTRAIDAS, MSG_MATRICULAS_NO_VALIDAS
)


class NonCriticalRulesValidator:
    """Validador de reglas no críticas que no detienen el bot pero generan notificaciones."""

    # Regex estándar para validar formato de email
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Inicializa el validador con la configuración.

        Args:
            config: Diccionario con toda la configuración del sistema
        """
        self.config = config

    def validar_reglas_no_criticas(
        self, caso: Dict[str, Any], tipo: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida las reglas no críticas para un caso.

        Las reglas validadas son:
        1. Formato de email válido en sp_correoelectronico (solo en modo PROD)
        2. Presencia de número de radicado (sp_name)
        3. Presencia de matrículas (invt_matriculasrequeridas)

        Args:
            caso: Diccionario con información del caso del CRM
            tipo: Tipo de proceso ("Copias" o "CopiasOficiales")

        Returns:
            Tupla (es_valido, mensaje_error):
            - es_valido: True si pasa todas las validaciones, False si alguna falla
            - mensaje_error: Mensaje descriptivo del error si es_valido=False, None si es_valido=True
        """
        case_id = caso.get("sp_documentoid", "N/A")
        
        # Regla 1: Validar formato de email (solo en modo PROD)
        modo = self.config.get("Globales", {}).get("modo", "PROD")
        if modo.upper() == "PROD":
            email = caso.get(CAMPO_EMAIL_PARTICULARES, "").strip()
            if not email:
                return (False, MSG_EMAIL_VACIO)
            if not self._validar_formato_email(email):
                return (False, MSG_EMAIL_INVALIDO.format(email=email))

        # Regla 2: Validar presencia de número de radicado (sp_name)
        sp_name = caso.get(CAMPO_RADICADO_PRINCIPAL, "").strip()
        if not sp_name:
            return (False, MSG_RADICADO_NO_EXTRAIDO)

        # Regla 3: Validar presencia de matrículas
        matriculas_str = caso.get(CAMPO_MATRICULAS, "").strip()
        if not matriculas_str:
            return (False, MSG_MATRICULAS_NO_EXTRAIDAS)
        
        # Verificar que al menos haya una matrícula válida después de split
        matriculas = [m.strip() for m in matriculas_str.split(",") if m.strip()]
        if not matriculas:
            return (False, MSG_MATRICULAS_NO_VALIDAS)

        # Todas las validaciones pasaron
        return (True, None)

    def _validar_formato_email(self, email: str) -> bool:
        """
        Valida el formato de un email usando regex.

        Args:
            email: Dirección de email a validar

        Returns:
            True si el formato es válido, False en caso contrario
        """
        if not email or not isinstance(email, str):
            return False
        return bool(self.EMAIL_REGEX.match(email.strip()))
