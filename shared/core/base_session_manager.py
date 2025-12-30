# coding: utf-8
"""
Clase base para gestión de sesiones.
Proporciona funcionalidad común para guardar y cargar sesiones.
"""

import json
import os
from typing import Dict, Any, Optional, List

from shared.utils.logger import get_logger

logger = get_logger("BaseSessionManager")


class BaseSessionManager:
    """Clase base para gestionar sesiones."""

    def __init__(self, sessions_dir: str = "sessions"):
        """
        Inicializa el gestor de sesiones.

        Args:
            sessions_dir: Directorio donde guardar las sesiones
        """
        self.sessions_dir = sessions_dir
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)

    def save_session(self, session_name: str, session_data: Dict[str, Any]) -> None:
        """
        Guarda una sesión.

        Args:
            session_name: Nombre de la sesión
            session_data: Datos de la sesión

        Example:
            manager = BaseSessionManager()
            manager.save_session("default",
                {"cookies": [...], "session_id": "abc123"})
        """
        try:
            # No guardar el driver en la sesión (no es serializable)
            data_to_save = {k: v for k, v in session_data.items() if k != "driver"}

            filepath = os.path.join(self.sessions_dir, f"{session_name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

            logger.info(f"Sesión '{session_name}' guardada")
        except Exception as e:
            logger.error(f"Error al guardar sesión: {e}")
            raise

    def load_session(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Carga una sesión.

        Args:
            session_name: Nombre de la sesión

        Returns:
            Datos de la sesión o None si no existe

        Example:
            session = manager.load_session("default")
        """
        try:
            filepath = os.path.join(self.sessions_dir, f"{session_name}.json")
            if not os.path.exists(filepath):
                logger.warning(f"Sesión '{session_name}' no encontrada")
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            logger.info(f"Sesión '{session_name}' cargada")
            return session_data
        except Exception as e:
            logger.error(f"Error al cargar sesión: {e}")
            return None

    def delete_session(self, session_name: str) -> bool:
        """
        Elimina una sesión.

        Args:
            session_name: Nombre de la sesión

        Returns:
            True si se eliminó, False en caso contrario
        """
        try:
            filepath = os.path.join(self.sessions_dir, f"{session_name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Sesión '{session_name}' eliminada")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar sesión: {e}")
            return False

    def list_sessions(self) -> List[str]:
        """
        Lista todas las sesiones guardadas.

        Returns:
            Lista de nombres de sesiones
        """
        try:
            sessions = []
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith(".json"):
                    sessions.append(filename[:-5])  # Remover .json
            return sessions
        except Exception as e:
            logger.error(f"Error al listar sesiones: {e}")
            return []
