# coding: utf-8
"""
Modelos base para las entidades de base de datos.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseModel(ABC):
    """Clase base para modelos de datos."""
    
    def __init__(self, **kwargs):
        """Inicializa el modelo con los datos proporcionados."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario.
        
        Returns:
            Diccionario con los atributos del modelo
        """
        return {key: value for key, value in self.__dict__.items() 
                if not key.startswith('_')}
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Crea una instancia del modelo desde un diccionario.
        
        Args:
            data: Diccionario con los datos
        
        Returns:
            Instancia del modelo
        """
        pass
    
    def __repr__(self) -> str:
        """Representación string del modelo."""
        attrs = ', '.join([f"{k}={v}" for k, v in self.to_dict().items()])
        return f"{self.__class__.__name__}({attrs})"

