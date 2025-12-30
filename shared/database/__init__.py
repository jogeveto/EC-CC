# coding: utf-8
"""
Módulo de base de datos compartido.
Proporciona operaciones CRUD genéricas y gestión de conexiones.
"""

from .connection import DatabaseConnection
from .crud import CRUDOperations
from .models import BaseModel
from .medidas_cautelares_db import MedidasCautelaresDB

__all__ = ["DatabaseConnection", "CRUDOperations", "BaseModel", "MedidasCautelaresDB"]
