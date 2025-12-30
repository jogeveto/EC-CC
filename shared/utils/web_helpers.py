# coding: utf-8
"""
Utilidades auxiliares para operaciones web y scraping.
"""

from typing import Optional, List
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from shared.utils.logger import get_logger

logger = get_logger("WebHelpers")


def safe_find_text(parent: WebElement, by: By, value: str, default: str = "") -> str:
    """
    Busca texto de un elemento de forma segura.
    
    Args:
        parent: Elemento padre donde buscar
        by: Método de búsqueda (By.ID, By.CLASS_NAME, etc.)
        value: Valor a buscar
        default: Valor por defecto si no se encuentra
    
    Returns:
        Texto encontrado o valor por defecto
    """
    try:
        element = parent.find_element(by, value)
        return element.text.strip()
    except (NoSuchElementException, AttributeError):
        return default
    except Exception as e:
        logger.warning(f"Error al buscar texto: {e}")
        return default


def safe_find_attribute(parent: WebElement, by: By, value: str, 
                        attribute: str, default: str = "") -> str:
    """
    Busca atributo de un elemento de forma segura.
    
    Args:
        parent: Elemento padre donde buscar
        by: Método de búsqueda
        value: Valor a buscar
        attribute: Nombre del atributo a obtener
        default: Valor por defecto si no se encuentra
    
    Returns:
        Valor del atributo o valor por defecto
    """
    try:
        element = parent.find_element(by, value)
        attr_value = element.get_attribute(attribute)
        return attr_value if attr_value else default
    except (NoSuchElementException, AttributeError):
        return default
    except Exception as e:
        logger.warning(f"Error al buscar atributo: {e}")
        return default


def safe_find_elements(parent: WebElement, by: By, value: str) -> List[WebElement]:
    """
    Busca múltiples elementos de forma segura.
    
    Args:
        parent: Elemento padre donde buscar
        by: Método de búsqueda
        value: Valor a buscar
    
    Returns:
        Lista de elementos encontrados (vacía si no hay)
    """
    try:
        return parent.find_elements(by, value)
    except Exception as e:
        logger.warning(f"Error al buscar elementos: {e}")
        return []


def wait_for_element(driver, by: By, value: str, timeout: int = 10) -> Optional[WebElement]:
    """
    Espera a que un elemento esté presente en la página.
    
    Args:
        driver: Instancia de WebDriver
        by: Método de búsqueda
        value: Valor a buscar
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        Elemento encontrado o None
    """
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))
    except TimeoutException:
        logger.warning(f"Timeout esperando elemento: {value}")
        return None
    except Exception as e:
        logger.warning(f"Error esperando elemento: {e}")
        return None


def wait_for_clickable(driver, by: By, value: str, timeout: int = 10) -> Optional[WebElement]:
    """
    Espera a que un elemento sea clickeable.
    
    Args:
        driver: Instancia de WebDriver
        by: Método de búsqueda
        value: Valor a buscar
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        Elemento encontrado o None
    """
    try:
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.element_to_be_clickable((by, value)))
    except TimeoutException:
        logger.warning(f"Timeout esperando elemento clickeable: {value}")
        return None
    except Exception as e:
        logger.warning(f"Error esperando elemento clickeable: {e}")
        return None


def safe_click(element: WebElement) -> bool:
    """
    Hace clic en un elemento de forma segura.
    
    Args:
        element: Elemento en el que hacer clic
    
    Returns:
        True si el clic fue exitoso, False en caso contrario
    """
    try:
        element.click()
        return True
    except Exception as e:
        logger.warning(f"Error al hacer clic: {e}")
        return False


def safe_send_keys(element: WebElement, text: str, clear_first: bool = True) -> bool:
    """
    Envía texto a un elemento de forma segura.
    
    Args:
        element: Elemento al que enviar texto
        text: Texto a enviar
        clear_first: Si True, limpia el campo antes de escribir
    
    Returns:
        True si fue exitoso, False en caso contrario
    """
    try:
        if clear_first:
            element.clear()
        element.send_keys(text)
        return True
    except Exception as e:
        logger.warning(f"Error al enviar texto: {e}")
        return False

