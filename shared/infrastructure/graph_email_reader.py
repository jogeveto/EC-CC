# coding: utf-8
"""
Lector de correos electrónicos usando Microsoft Graph API.
Permite leer correos, obtener adjuntos y gestionar estado de correos.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import unicodedata
import re

from .graph_api_client import GraphApiClient
from shared.utils.logger import get_logger

logger = get_logger("GraphEmailReader")


class EmailReaderError(Exception):
    """Excepción para errores del lector de correos."""

    pass


class GraphEmailReader:
    """
    Lector de correos usando Microsoft Graph API.

    Args:
        config: Diccionario de configuración con credenciales de Graph API
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el lector de correos con la configuración proporcionada.

        Args:
            config: Diccionario de configuración con credenciales de Graph API
        """
        self.graph_client = GraphApiClient(config)

    def _looks_like_id(self, folder: str) -> bool:
        """Heurística simple para detectar si el parámetro parece un ID."""
        return bool(folder) and len(folder) > 30 and ("-" in folder or folder.isalnum())

    def _normalize_well_known(self, folder: str) -> Optional[str]:
        """Devuelve el nombre normalizado si es una well-known folder, None en caso contrario."""
        well_known = {"inbox", "drafts", "sentitems", "deleteditems", "junkemail", "outbox"}
        key = folder.lower().replace(" ", "") if folder else ""
        return key if key in well_known else None

    def _find_folder_id_by_name(self, folder: str) -> str:
        """Busca el ID de una carpeta por su nombre en raíz y en hijas."""
        folders_data = self.graph_client.make_request("GET", "mailFolders")
        target = folder.lower()
        for f in folders_data.get("value", []):
            if f.get("displayName", "").lower() == target:
                logger.info(f"Carpeta '{folder}' resuelta a ID: {f['id']}")
                return f["id"]
        for f in folders_data.get("value", []):
            child_folders = self.graph_client.make_request(
                "GET", f"mailFolders/{f['id']}/childFolders"
            )
            for child in child_folders.get("value", []):
                if child.get("displayName", "").lower() == target:
                    logger.info(
                        f"Carpeta '{folder}' resuelta a ID: {child['id']}"
                    )
                    return child["id"]
        raise EmailReaderError(f"Carpeta no encontrada: {folder}")

    def _resolve_folder_id(self, folder: str) -> str:
        """
        Resuelve un nombre de carpeta a su ID de Graph API.
        Si es un ID lo retorna, si es well-known retorna el nombre,
        si es personalizada busca su ID por nombre.
        """
        try:
            if self._looks_like_id(folder):
                logger.info(f"Usando ID de carpeta directamente: {folder}")
                return folder
            wk = self._normalize_well_known(folder)
            if wk:
                return wk
            return self._find_folder_id_by_name(folder)
        except EmailReaderError:
            raise
        except Exception as e:
            logger.error(f"Error buscando carpeta '{folder}': {e}")
            raise EmailReaderError(f"Error al buscar carpeta: {str(e)}")

    def _format_date_filter(self, date_field: str, date_value: datetime) -> str:
        """Formatea un filtro de fecha para la consulta."""
        return f"{date_field} {date_value.isoformat()}"

    def _format_address_filter(self, addresses: Union[str, List[str]]) -> str:
        """Formatea un filtro de dirección de correo."""
        addr_list = [addresses] if isinstance(addresses, str) else addresses
        return " or ".join(
            [f"from/emailAddress/address eq '{addr}'" for addr in addr_list]
        )

    def _format_subject_filter(self, subject_contains: str) -> str:
        """Formatea un filtro de asunto."""
        return f"contains(subject, '{subject_contains}')"

    def _build_filter_query(self, filter_criteria: Dict[str, Any]) -> str:
        """Construye una consulta de filtro para Graph API."""
        filters = []
        if filter_criteria.get("from"):
            from_filter = self._format_address_filter(filter_criteria["from"])
            filters.append(f"({from_filter})")
        if filter_criteria.get("subject_contains"):
            subject_filter = self._format_subject_filter(
                filter_criteria["subject_contains"]
            )
            filters.append(f"({subject_filter})")
        if filter_criteria.get("has_attachments"):
            filters.append("hasAttachments eq true")
        if filter_criteria.get("received_after"):
            filters.append(
                self._format_date_filter(
                    "receivedDateTime ge", filter_criteria["received_after"]
                )
            )
        if filter_criteria.get("received_before"):
            filters.append(
                self._format_date_filter(
                    "receivedDateTime le", filter_criteria["received_before"]
                )
            )
        return " and ".join(filters)

    def get_emails(
        self,
        folder: str = "inbox",
        filter_criteria: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
        read_status: str = "all",
    ) -> List[Dict[str, Any]]:
        """
        Obtiene correos electrónicos de una carpeta.

        Args:
            folder: Nombre de la carpeta (default: "inbox")
            filter_criteria: Criterios de filtrado opcionales
            max_results: Número máximo de correos a obtener
            read_status: Estado de lectura ("read", "unread", "all")

        Returns:
            Lista de diccionarios con información de correos

        Raises:
            EmailReaderError: Si hay error al obtener correos
        """
        try:
            if not isinstance(folder, str):
                raise ValueError("El parámetro folder debe ser un string")

            # Resolver nombre de carpeta a ID
            folder_id = self._resolve_folder_id(folder)

            params = self._build_request_params(
                filter_criteria, max_results, read_status
            )
            response = self.graph_client.make_request(
                "GET", f"mailFolders/{folder_id}/messages", params=params
            )
            if not response:
                raise EmailReaderError("No se pudo obtener respuesta del servidor")
            emails_data = response.get("value", [])
            return self._process_email_list(emails_data)
        except Exception as e:
            logger.error(f"Error obteniendo correos: {str(e)}")
            raise EmailReaderError(f"Error al obtener correos: {str(e)}")

    def _build_request_params(
        self,
        filter_criteria: Optional[Dict[str, Any]],
        max_results: Optional[int],
        read_status: str = "all",
    ) -> Dict[str, str]:
        """Construye parámetros de la petición a Graph API."""
        params = {
            "$select": "id,subject,from,toRecipients,receivedDateTime,body,isRead,hasAttachments"
        }
        filters = []
        if read_status == "unread":
            filters.append("isRead eq false")
        elif read_status == "read":
            filters.append("isRead eq true")
        if filter_criteria:
            custom_filter = self._build_filter_query(filter_criteria)
            if custom_filter:
                filters.append(custom_filter)
        if filters:
            params["$filter"] = " and ".join(filters)
        if max_results:
            if not isinstance(max_results, int) or max_results <= 0:
                raise ValueError("max_results debe ser un entero positivo")
            params["$top"] = str(max_results)
        return params

    def _process_email_list(
        self, emails_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Procesa la lista de correos obtenidos de Graph API."""
        result = []
        for email in emails_data:
            attachments = []
            if email.get("hasAttachments"):
                attachments = self._get_email_attachments(email["id"])
            result.append(self._format_email_data(email, attachments))
        return result

    def _get_email_attachments(self, email_id: str) -> List[Dict[str, Any]]:
        """Obtiene los adjuntos de un correo."""
        try:
            att_response = self.graph_client.make_request(
                "GET", f"messages/{email_id}/attachments"
            )
            if not att_response:
                logger.warning(f"No se obtuvo respuesta al obtener adjuntos del correo {email_id}")
                return []
            
            attachments_list = att_response.get("value", [])
            logger.info(f"Correo {email_id}: obtenidos {len(attachments_list)} adjunto(s) de Graph API")
            
            adjuntos = []
            for att in attachments_list:
                is_inline = att.get("contentDisposition", "") == "inline"
                adjunto_data = {
                    "id": att["id"],
                    "name": att["name"],
                    "content_type": att.get("contentType", "application/octet-stream"),
                    "size": att.get("size", 0),
                    "is_inline": is_inline,
                    "content_id": att.get("contentId", None),
                }
                adjuntos.append(adjunto_data)
                logger.debug(f"Adjunto procesado: nombre={adjunto_data['name']}, is_inline={is_inline}, id={adjunto_data['id']}")
            
            return adjuntos
        except Exception as e:
            logger.error(f"Error obteniendo adjuntos del correo {email_id}: {e}", exc_info=True)
            return []

    def _format_email_data(
        self, email: Dict[str, Any], attachments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Formatea los datos de un correo en un diccionario estandarizado."""
        destinatarios = []
        if email.get("toRecipients"):
            for recipient in email["toRecipients"]:
                if recipient.get("emailAddress", {}).get("address"):
                    destinatarios.append(recipient["emailAddress"]["address"])
        return {
            "id": email["id"],
            "subject": email.get("subject", ""),
            "from": email.get("from", {}).get("emailAddress", {}).get("address", ""),
            "to": destinatarios,
            "received_date": (
                datetime.fromisoformat(email["receivedDateTime"].rstrip("Z"))
                if email.get("receivedDateTime")
                else datetime.now()
            ),
            "body": email.get("body", {}).get("content", ""),
            "is_read": email.get("isRead", False),
            "has_attachments": email.get("hasAttachments", False),
            "attachments": attachments,
        }

    def get_attachment_content(self, email_id: str, attachment_id: str) -> bytes:
        """
        Obtiene el contenido binario de un adjunto.

        Args:
            email_id: ID del correo
            attachment_id: ID del adjunto

        Returns:
            Contenido binario del adjunto

        Raises:
            EmailReaderError: Si hay error al obtener el adjunto
        """
        try:
            if not email_id or not isinstance(email_id, str):
                raise ValueError("email_id debe ser un string válido")
            if not attachment_id or not isinstance(attachment_id, str):
                raise ValueError("attachment_id debe ser un string válido")
            content = self.graph_client.make_request(
                "GET",
                f"messages/{email_id}/attachments/{attachment_id}/$value",
                binary=True,
            )
            if not content:
                msg = "No se pudo obtener el contenido del adjunto"
                raise EmailReaderError(f"{msg} {attachment_id}")
            return content
        except ValueError as e:
            logger.error(f"Error de validación: {e}")
            raise
        except Exception as e:
            logger.error(f"Error obteniendo adjunto: {e}")
            raise EmailReaderError(f"Error al obtener adjunto: {str(e)}")

    def mark_as_read(self, email_id: str) -> bool:
        """
        Marca un correo como leído.

        Args:
            email_id: ID del correo

        Returns:
            True si se marcó exitosamente

        Raises:
            EmailReaderError: Si hay error al marcar el correo
        """
        try:
            if not email_id or not isinstance(email_id, str):
                raise ValueError("email_id debe ser un string válido")
            response = self.graph_client.make_request(
                "PATCH", f"messages/{email_id}", json_data={"isRead": True}
            )
            if not response:
                raise EmailReaderError(
                    f"No se pudo marcar el correo {email_id} como leído"
                )
            return True
        except ValueError as e:
            logger.error(f"Error de validación: {e}")
            raise
        except Exception as e:
            logger.error(f"Error marcando correo como leído: {e}")
            raise EmailReaderError(f"Error al marcar correo: {str(e)}")

    def move_to_folder(self, email_id: str, folder: str) -> str:
        """
        Mueve un correo a una carpeta y retorna el nuevo ID del correo movido.

        Args:
            email_id: ID del correo
            folder: Nombre de la carpeta destino

        Returns:
            Nuevo ID del correo movido (o ID original si falla)
        """
        try:
            folders_data = self.graph_client.make_request("GET", "mailFolders")
            folder_id = None
            for f in folders_data.get("value", []):
                if f["displayName"].lower() == folder.lower():
                    folder_id = f["id"]
                    break
            if not folder_id:
                raise ValueError(f"Carpeta no encontrada: {folder}")
            response = self.graph_client.make_request(
                "POST",
                f"messages/{email_id}/move",
                json_data={"destinationId": folder_id},
            )
            # La respuesta de Graph API contiene el correo movido con su nuevo ID
            nuevo_id = response.get("id", None) if response else None
            logger.info(
                f"Correo {email_id} movido a carpeta {folder}. Nuevo ID: {nuevo_id}"
            )
            return nuevo_id if nuevo_id else email_id
        except Exception as e:
            logger.error(f"Error moviendo correo: {e}")
            return email_id  # Retornar ID original si falla

    def test_reader_email(self) -> bool:
        """
        Prueba la configuración del lector de correos.

        Returns:
            True si la configuración es válida
        """
        try:
            self.graph_client.make_request("GET", "mailFolders")
            logger.info("Configuración del lector de correos válida")
            return True
        except Exception as e:
            logger.error(f"Error probando configuración: {e}")
            return False

    def clear_subject(self, subject: str) -> str:
        """
        Limpia un asunto de correo removiendo caracteres especiales.

        Args:
            subject: Asunto original

        Returns:
            Asunto limpio
        """
        if not subject:
            return ""
        subject = (
            unicodedata.normalize("NFKD", subject)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        subject = re.sub(r"[^A-Za-z0-9_\\-]", " ", subject)
        return subject

    def move_email(self, email_id: str, destination_folder: str) -> bool:
        """
        Mueve un correo a otra carpeta.

        Args:
            email_id: ID del correo a mover
            destination_folder: Nombre de la carpeta destino

        Returns:
            True si se movió exitosamente, False en caso contrario
        """
        try:
            # Primero obtener el ID de la carpeta destino (usa resolvedor existente)
            folder_id = self._resolve_folder_id(destination_folder)
            if not folder_id:
                logger.error(
                    f"No se encontró la carpeta '{destination_folder}'"
                )
                return False

            # Mover el correo usando la API de Graph
            endpoint = f"messages/{email_id}/move"
            payload = {"destinationId": folder_id}

            response = self.graph_client.make_request(
                "POST", endpoint, json_data=payload
            )

            if response:
                logger.info(
                    f"Correo {email_id} movido a '{destination_folder}'"
                )
                return True
            else:
                logger.error(f"Error moviendo correo {email_id}")
                return False

        except Exception as e:
            logger.error(f"Error moviendo correo {email_id}: {e}")
            return False
