# coding: utf-8
"""
Componentes core de DynamicsCrmApi.
"""

from .dynamics_authenticator import Dynamics365Authenticator
from .dynamics_client import Dynamics365Client

__all__ = ['Dynamics365Authenticator', 'Dynamics365Client']
