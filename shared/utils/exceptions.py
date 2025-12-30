# coding: utf-8
"""
Excepciones personalizadas para el módulo NotificacionesCertificadas.

Define excepciones específicas para diferentes tipos de errores
que pueden ocurrir durante el proceso de envío de notificaciones.
"""


class NotificacionError(Exception):
    """
    Excepción base para errores del módulo NotificacionesCertificadas.

    Todas las excepciones específicas del módulo heredan de esta clase.
    """

    pass


class DatabaseError(NotificacionError):
    """
    Excepción para errores relacionados con la base de datos.

    Se lanza cuando hay problemas de conexión, consultas fallidas,
    o datos no encontrados en la base de datos.
    """

    pass


class AuthError(NotificacionError):
    """
    Excepción para errores de autenticación.

    Se lanza cuando falla el login en el portal de notificaciones
    certificadas o cuando las credenciales son inválidas.
    """

    pass


class TemplateError(NotificacionError):
    """
    Excepción para errores relacionadas con plantillas.

    Se lanza cuando la plantilla no se encuentra, está mal formateada,
    o falta información para reemplazar marcadores.
    """

    pass


class NavigationError(NotificacionError):
    """
    Excepción para errores de navegación web.

    Se lanza cuando hay problemas navegando el portal de notificaciones,
    elementos no encontrados, o timeouts.
    """

    pass


class ValidationError(NotificacionError):
    """
    Excepción para errores de validación de datos.

    Se lanza cuando los datos de entrada no cumplen con los requisitos
    esperados (correos inválidos, campos vacíos, etc.).
    """

    pass
