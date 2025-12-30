# coding: utf-8
"""
Enviador de correos electrónicos usando Microsoft Graph API.
Permite enviar correos con contenido HTML y adjuntos.
"""

import base64
from typing import List, Dict, Optional, Union, Any

from .graph_api_client import GraphApiClient
from shared.utils.logger import get_logger

logger = get_logger("GraphEmailSender")


class GraphEmailSender:
    """
    Enviador de correos usando Microsoft Graph API.

    Args:
        config: Diccionario de configuración con credenciales de Graph API
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el enviador de correos con la configuración proporcionada.

        Args:
            config: Diccionario de configuración con credenciales de Graph API
        """
        self.graph_client = GraphApiClient(config)

    def send_email(
        self,
        subject: str,
        html_content: str,
        to_recipients: Union[str, List[str]],
        cc_recipients: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Envía un correo electrónico usando Graph API.

        Args:
            subject: Asunto del correo
            html_content: Contenido HTML del correo
            to_recipients: Destinatarios (string o lista)
            cc_recipients: Destinatarios en copia (opcional)
            attachments: Lista de adjuntos (opcional)
                Cada adjunto debe tener: {"filename": str, "content": bytes, ...}

        Returns:
            Diccionario con resultado del envío:
            {
                "success": bool,
                "message_id": str,
                "status": str,
                "recipients": List[str],
                "cc_recipients": List[str] (opcional),
                "error": str (si hay error)
            }
        """
        try:
            to_list = (
                [to_recipients] if isinstance(to_recipients, str) else to_recipients
            )
            cc_list = None
            if cc_recipients:
                cc_list = (
                    [cc_recipients] if isinstance(cc_recipients, str) else cc_recipients
                )

            message = {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_content},
                "toRecipients": [
                    {"emailAddress": {"address": email}} for email in to_list
                ],
            }
            if cc_list:
                message["ccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in cc_list
                ]
            if attachments:
                message["attachments"] = self._process_attachments(attachments)

            response = self.graph_client.make_request(
                method="POST", endpoint="sendMail", json_data={"message": message}
            )
            return {
                "success": True,
                "message_id": response.get("id", ""),
                "status": "sent",
                "recipients": to_list,
                "cc_recipients": cc_list or [],
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error enviando correo: {error_msg}")
            return {"success": False, "error": error_msg, "status": "failed"}

    def _process_attachments(
        self, attachments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Procesa adjuntos para el formato de Graph API.

        Args:
            attachments: Lista de adjuntos con formato:
                {
                    "filename": str,
                    "content": bytes o str (base64),
                    "is_inline": bool (opcional),
                    "content_id": str (opcional),
                    "content_type": str (opcional)
                }

        Returns:
            Lista de adjuntos procesados para Graph API
        """
        processed_attachments = []
        for attachment in attachments:
            content = attachment["content"]
            if isinstance(content, bytes):
                content_base64 = base64.b64encode(content).decode("utf-8")
            else:
                content_base64 = content

            att_dict = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment["filename"],
                "contentBytes": content_base64,
            }

            if attachment.get("is_inline") and attachment.get("content_id"):
                att_dict["isInline"] = True
                att_dict["contentId"] = attachment["content_id"]
                if attachment.get("content_type"):
                    att_dict["contentType"] = attachment["content_type"]

            processed_attachments.append(att_dict)
        return processed_attachments

    def test_email_sender(self) -> bool:
        """
        Prueba la configuración del enviador de correos.

        Returns:
            True si la configuración es válida
        """
        try:
            # Intentar obtener información del usuario para verificar conexión
            self.graph_client.make_request("GET", "")
            logger.info("Configuración del sender de correos válida")
            logger.info(f"Usuario: {self.graph_client.user_email}")
            return True
        except Exception as e:
            logger.error(f"Error probando configuración del sender: {e}")
            return False
