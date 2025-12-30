# coding: utf-8
"""
Clase base abstracta para scraping de páginas web.
Proporciona funcionalidad común para todos los módulos de scraping.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from shared.utils.logger import get_logger

logger = get_logger("BaseScraper")


class BaseScraper(ABC):
    """Clase base abstracta para scraping de páginas web."""
    
    def __init__(self, session_data: Dict[str, Any], driver: Optional[webdriver.Chrome] = None):
        """
        Inicializa el scraper.
        
        Args:
            session_data: Datos de sesión del login
            driver: Instancia de WebDriver (opcional)
        """
        self.session_data = session_data
        self.driver = driver
        if not self.driver and session_data.get("driver"):
            self.driver = session_data["driver"]
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """
        Obtiene la URL base para las operaciones de scraping.
        Debe ser implementado por cada subclase.
        
        Returns:
            URL base
        """
        pass
    
    def _safe_find_text(self, parent, by: By, value: str) -> str:
        """
        Busca texto de forma segura.
        
        Args:
            parent: Elemento padre donde buscar
            by: Método de búsqueda (By.ID, By.CLASS_NAME, etc.)
            value: Valor a buscar
        
        Returns:
            Texto encontrado o cadena vacía
        """
        try:
            element = parent.find_element(by, value)
            return element.text.strip()
        except:
            return ""
    
    def _safe_find_attribute(self, parent, by: By, value: str, attribute: str) -> str:
        """
        Busca atributo de forma segura.
        
        Args:
            parent: Elemento padre donde buscar
            by: Método de búsqueda
            value: Valor a buscar
            attribute: Nombre del atributo a obtener
        
        Returns:
            Valor del atributo o cadena vacía
        """
        try:
            element = parent.find_element(by, value)
            return element.get_attribute(attribute) or ""
        except:
            return ""
    
    def _apply_filters(self, filters: Dict[str, Any]) -> None:
        """
        Aplica filtros en la página.
        Puede ser sobrescrito por subclases para lógica específica.
        
        Args:
            filters: Diccionario con filtros
        """
        try:
            # Implementación básica - las subclases pueden extender
            if "date_from" in filters:
                date_from_field = self.driver.find_element(By.ID, "date-from")
                date_from_field.send_keys(filters["date_from"])
            
            if "date_to" in filters:
                date_to_field = self.driver.find_element(By.ID, "date-to")
                date_to_field.send_keys(filters["date_to"])
            
            # Aplicar filtros si hay botón
            try:
                apply_button = self.driver.find_element(By.ID, "apply-filters")
                apply_button.click()
                import time
                time.sleep(2)
            except:
                pass
        
        except Exception as e:
            logger.warning(f"Error al aplicar filtros: {e}")
    
    def download_document(self, document_id: str, folder: str = ".") -> str:
        """
        Descarga un documento.
        Implementación base que puede ser extendida por subclases.
        
        Args:
            document_id: ID del documento
            folder: Carpeta donde guardar el documento
        
        Returns:
            Ruta del archivo descargado
        """
        try:
            if not self.driver:
                raise Exception("Driver no disponible")
            
            import os
            # Crear carpeta si no existe
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            # Navegar al documento (método abstracto)
            document_url = self._get_document_url(document_id)
            self.driver.get(document_url)
            
            # Esperar a que cargue
            import time
            time.sleep(2)
            
            # Localizar botón de descarga (método abstracto)
            download_button = self._locate_download_button()
            download_button.click()
            
            # Esperar a que se descargue
            time.sleep(5)
            
            # Obtener nombre del archivo (método abstracto)
            filename = self._get_document_filename(document_id)
            filepath = os.path.join(folder, filename)
            
            logger.info(f"Documento descargado: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error al descargar documento: {e}")
            raise
    
    @abstractmethod
    def _get_document_url(self, document_id: str) -> str:
        """
        Obtiene la URL del documento a descargar.
        Debe ser implementado por cada subclase.
        
        Args:
            document_id: ID del documento
        
        Returns:
            URL del documento
        """
        pass
    
    @abstractmethod
    def _locate_download_button(self):
        """
        Localiza el botón de descarga.
        Debe ser implementado por cada subclase.
        
        Returns:
            Elemento del botón de descarga
        """
        pass
    
    @abstractmethod
    def _get_document_filename(self, document_id: str) -> str:
        """
        Obtiene el nombre del archivo a descargar.
        Debe ser implementado por cada subclase.
        
        Args:
            document_id: ID del documento
        
        Returns:
            Nombre del archivo
        """
        pass

