# coding: utf-8
"""
Infraestructura compartida para comunicación con servicios externos.
Incluye cliente de Graph API y servicios de email.
"""

from .graph_api_client import GraphApiClient
from .graph_email_reader import GraphEmailReader
from .graph_email_sender import GraphEmailSender

__all__ = ['GraphApiClient', 'GraphEmailReader', 'GraphEmailSender']

