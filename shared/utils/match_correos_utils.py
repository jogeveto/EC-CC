# coding: utf-8
"""
Utilidad para matching de entidades con fuzzy matching.

Inspirado en MathCorreos.py, implementa:
- Normalización de texto (números escritos a dígitos, sin acentos)
- Fuzzy matching con rapidfuzz
- Extracción de números de juzgados
- Búsqueda probabilística de entidades
"""

import re
from typing import Dict, List, Tuple
from rapidfuzz import fuzz, process
from shared.utils.logger import get_logger

logger = get_logger(__name__)


# Diccionario completo de números escritos (ordinales y cardinales)
NUMEROS_LETRAS = {
    # Ordinales
    "PRIMERO": "1",
    "SEGUNDO": "2",
    "TERCERO": "3",
    "CUARTO": "4",
    "QUINTO": "5",
    "SEXTO": "6",
    "SEPTIMO": "7",
    "OCTAVO": "8",
    "NOVENO": "9",
    "DECIMO": "10",
    "UNDECIMO": "11",
    "DUODECIMO": "12",
    "DECIMOTERCERO": "13",
    "DECIMOCUARTO": "14",
    "DECIMOQUINTO": "15",
    "DECIMOSEXTO": "16",
    "DECIMOSEPTIMO": "17",
    "DECIMOOCTAVO": "18",
    "DECIMONOVENO": "19",
    "VIGESIMO": "20",
    "VIGESIMOPRIMERO": "21",
    "VIGESIMOSEGUNDO": "22",
    "VIGESIMOTERCERO": "23",
    "VIGESIMOCUARTO": "24",
    "VIGESIMOQUINTO": "25",
    "VIGESIMOSEXTO": "26",
    "VIGESIMOSEPTIMO": "27",
    "VIGESIMOOCTAVO": "28",
    "VIGESIMONOVENO": "29",
    "TRIGESIMO": "30",
    "TRIGESIMOPRIMERO": "31",
    "TRIGESIMOSEGUNDO": "32",
    "TRIGESIMOTERCERO": "33",
    "TRIGESIMOCUARTO": "34",
    "TRIGESIMOQUINTO": "35",
    "TRIGESIMOSEXTO": "36",
    "TRIGESIMOSEPTIMO": "37",
    "TRIGESIMOOCTAVO": "38",
    "TRIGESIMONOVENO": "39",
    "CUADRAGESIMO": "40",
    "CUADRAGESIMOPRIMERO": "41",
    "CUADRAGESIMOSEGUNDO": "42",
    "CUADRAGESIMOTERCERO": "43",
    "CUADRAGESIMOCUARTO": "44",
    "CUADRAGESIMOQUINTO": "45",
    "CUADRAGESIMOSEXTO": "46",
    "CUADRAGESIMOSEPTIMO": "47",
    "CUADRAGESIMOOCTAVO": "48",
    "CUADRAGESIMONOVENO": "49",
    "QUINCUAGESIMO": "50",
    # Cardinales
    "UNO": "1",
    "DOS": "2",
    "TRES": "3",
    "CUATRO": "4",
    "CINCO": "5",
    "SEIS": "6",
    "SIETE": "7",
    "OCHO": "8",
    "NUEVE": "9",
    "DIEZ": "10",
    "ONCE": "11",
    "DOCE": "12",
    "TRECE": "13",
    "CATORCE": "14",
    "QUINCE": "15",
    "DIECISEIS": "16",
    "DIECISIETE": "17",
    "DIECIOCHO": "18",
    "DIECINUEVE": "19",
    "VEINTE": "20",
    "VEINTIUNO": "21",
    "VEINTIDOS": "22",
    "VEINTITRES": "23",
    "VEINTICUATRO": "24",
    "VEINTICINCO": "25",
    "VEINTISEIS": "26",
    "VEINTISIETE": "27",
    "VEINTIOCHO": "28",
    "VEINTINUEVE": "29",
    "TREINTA": "30",
}


class EntityMatcher:
    """
    Clase para realizar matching de entidades con fuzzy matching.

    Compara nombres de entidades entre MedidasCautelares y DirectorioCorreos.
    El nombre_entidad actúa como ID para obtener los correos electrónicos.

    Funcionalidades:
    - Normalizar nombres de entidades (números escritos a dígitos, sin acentos)
    - Comparar entidades por probabilidad usando fuzzy matching
    - Extraer correos de entidades matcheadas
    - Parsear múltiples correos en formato CSV
    """

    def __init__(self):
        """Inicializa el matcher de entidades."""
        pass

    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparación.

        - Convierte a mayúsculas
        - Elimina acentos y caracteres especiales
        - Reemplaza números escritos por dígitos
        - Elimina espacios múltiples

        Args:
            text: Texto a normalizar.

        Returns:
            Texto normalizado.
        """
        if not isinstance(text, str):
            return ""

        # Mayúsculas
        text = text.upper()

        # Eliminar acentos
        replacements = {
            "Á": "A",
            "É": "E",
            "Í": "I",
            "Ó": "O",
            "Ú": "U",
            "Ñ": "N",
            "À": "A",
            "È": "E",
            "Ì": "I",
            "Ò": "O",
            "Ù": "U",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Reemplazar números escritos por dígitos (ordenar por longitud desc)
        for palabra, numero in sorted(
            NUMEROS_LETRAS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            text = re.sub(rf"\b{palabra}\b", numero, text)

        # Eliminar duplicados de números consecutivos (ej: "2 2" -> "2")
        text = re.sub(r"\b(\d+)(\s+\1)+\b", r"\1", text)

        # Eliminar espacios múltiples
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def buscar_mejor_coincidencia(
        self,
        nombre_consulta: str,
        lista_entidades: List[str],
        threshold: float = 0.75,
        top_n: int = 3,
    ) -> Dict:
        """
        Busca la mejor coincidencia de una entidad en una lista.

        Compara el nombre completo de la entidad usando fuzzy matching.
        El nombre de la entidad actúa como ID para obtener los correos.

        Args:
            nombre_consulta: Nombre de la entidad a buscar.
            lista_entidades: Lista de nombres de entidades en BD.
            threshold: Umbral de similitud (0.0 a 1.0).
            top_n: Número de mejores coincidencias a considerar.

        Returns:
            Dict con:
                - success: bool
                - entity_matched: str (nombre encontrado)
                - similarity_score: float (0.0 a 1.0)
                - normalized_query: str
                - normalized_match: str
                - error: str (si falla)
        """
        try:
            if not nombre_consulta or not lista_entidades:
                return {
                    "success": False,
                    "entity_matched": None,
                    "similarity_score": 0.0,
                    "error": "Consulta o lista vacía",
                }

            # Normalizar consulta
            nombre_norm = self.normalize_text(nombre_consulta)

            # Normalizar lista de entidades
            entidades_norm = [self.normalize_text(e) for e in lista_entidades]

            # Buscar coincidencias usando rapidfuzz
            matches = process.extract(
                nombre_norm, entidades_norm, scorer=fuzz.token_sort_ratio, limit=top_n
            )

            if not matches:
                logger.warning(
                    f"No se encontraron coincidencias para: {nombre_consulta}"
                )
                return {
                    "success": False,
                    "entity_matched": None,
                    "similarity_score": 0.0,
                    "normalized_query": nombre_norm,
                    "error": "No se encontraron coincidencias",
                }

            # Obtener la mejor coincidencia
            mejor_match_norm, score, index = matches[0]
            score_normalized = score / 100.0

            # Validar contra el threshold
            if score_normalized < threshold:
                logger.warning(
                    f"Score {score_normalized:.2f} < threshold {threshold} "
                    f"para {nombre_consulta}"
                )
                return {
                    "success": False,
                    "entity_matched": lista_entidades[index],
                    "similarity_score": score_normalized,
                    "normalized_query": nombre_norm,
                    "normalized_match": mejor_match_norm,
                    "error": f"Score bajo: {score_normalized:.2%}",
                }

            logger.info(
                f"Coincidencia encontrada: '{nombre_consulta}' -> "
                f"'{lista_entidades[index]}' (score: {score_normalized:.2%})"
            )

            return {
                "success": True,
                "entity_matched": lista_entidades[index],
                "similarity_score": score_normalized,
                "normalized_query": nombre_norm,
                "normalized_match": mejor_match_norm,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error en búsqueda de coincidencia: {str(e)}")
            return {
                "success": False,
                "entity_matched": None,
                "similarity_score": 0.0,
                "error": str(e),
            }

    def parsear_correos(self, correos_str: str) -> List[str]:
        """
        Parsea string de correos separados por comas.

        Args:
            correos_str: String con correos separados por comas.

        Returns:
            Lista de correos limpios.
        """
        if not correos_str or not isinstance(correos_str, str):
            return []

        # Separar por comas y limpiar espacios
        correos = [email.strip() for email in correos_str.split(",")]

        # Filtrar correos vacíos y validar formato básico
        correos_validos = []
        email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

        for email in correos:
            if email and email_pattern.match(email):
                correos_validos.append(email)
            elif email:
                logger.warning(f"Correo inválido detectado: {email}")

        return correos_validos

    def comparar_entidades_con_probabilidad(
        self,
        entidad_consulta: str,
        entidades_bd: List[Tuple[str, str]],
        threshold: float = 0.75,
    ) -> Dict:
        """
        Compara una entidad contra la BD y retorna correos.

        Flujo completo:
        1. Normaliza la consulta
        2. Busca mejor coincidencia por probabilidad
        3. Extrae correos de la entidad encontrada
        4. Disponibiliza la información

        Args:
            entidad_consulta: Nombre de entidad a buscar.
            entidades_bd: Lista de tuplas (nombre_entidad, correo_electronico).
            threshold: Umbral de similitud.

        Returns:
            Dict con:
                - success: bool
                - entity_matched: str
                - emails: List[str]
                - similarity_score: float
                - metadata: Dict con info adicional
                - error: str (si falla)
        """
        try:
            # Extraer solo los nombres para matching
            nombres = [tupla[0] for tupla in entidades_bd]

            # Buscar mejor coincidencia
            resultado = self.buscar_mejor_coincidencia(
                entidad_consulta, nombres, threshold
            )

            if not resultado["success"]:
                return {
                    "success": False,
                    "entity_matched": resultado.get("entity_matched"),
                    "emails": [],
                    "similarity_score": resultado["similarity_score"],
                    "metadata": resultado,
                    "error": resultado["error"],
                }

            # Encontrar los correos de la entidad coincidente
            entity_matched = resultado["entity_matched"]
            correos_encontrados = []

            for nombre, correos_str in entidades_bd:
                if nombre == entity_matched:
                    correos = self.parsear_correos(correos_str)
                    correos_encontrados.extend(correos)

            # Eliminar duplicados manteniendo orden
            correos_unicos = list(dict.fromkeys(correos_encontrados))

            logger.info(
                f"Entidad '{entidad_consulta}' -> '{entity_matched}': "
                f"{len(correos_unicos)} correo(s) encontrado(s)"
            )

            return {
                "success": True,
                "entity_matched": entity_matched,
                "emails": correos_unicos,
                "similarity_score": resultado["similarity_score"],
                "metadata": {
                    "normalized_query": resultado["normalized_query"],
                    "normalized_match": resultado["normalized_match"],
                },
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error comparando entidades: {str(e)}")
            return {
                "success": False,
                "entity_matched": None,
                "emails": [],
                "similarity_score": 0.0,
                "metadata": {},
                "error": str(e),
            }
