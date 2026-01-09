"""Enumeraciones para el módulo ExpedicionCopias."""
from enum import Enum


class TipoProceso(str, Enum):
    """Tipos de proceso de expedición."""
    PARTICULARES = "PARTICULARES"
    OFICIALES = "OFICIALES"
    COPIAS = "Copias"
    COPIAS_OFICIALES = "CopiasOficiales"


class EstadoProceso(str, Enum):
    """Estados posibles de un proceso."""
    EXITOSO = "Exitoso"
    NO_EXITOSO = "No Exitoso"
    PENDIENTE = "Pendiente"


class TipoContenidoEmail(str, Enum):
    """Tipos de contenido para emails."""
    HTML = "HTML"
    TEXT = "Text"


class PermisoOneDrive(str, Enum):
    """Permisos disponibles para OneDrive."""
    READ = "read"
    VIEW = "view"
    WRITE = "write"


class TipoEnlace(str, Enum):
    """Tipos de enlace para compartir."""
    VIEW = "view"
    EDIT = "edit"


class ScopeEnlace(str, Enum):
    """Scopes para enlaces compartidos."""
    ANONYMOUS = "anonymous"
    ORGANIZATION = "organization"
