# coding: utf-8
"""
Clase base abstracta para manejo de login en páginas web.
Proporciona funcionalidad común para todos los módulos de login.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from shared.utils.logger import get_logger

logger = get_logger("BaseLogin")


class BaseLogin(ABC):
    """Clase base abstracta para manejo de login."""
    
    def __init__(self, url: str, driver: Optional[webdriver.Chrome] = None):
        """
        Inicializa el login handler.
        
        Args:
            url: URL de la página de login
            driver: Instancia de WebDriver (opcional)
        """
        self.url = url
        self.driver = driver
        self.session_data = {}
    
    def login(self, username: str, password: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza el login en la página.
        
        Args:
            username: Usuario
            password: Contraseña
            timeout: Timeout para operaciones (default: 30)
        
        Returns:
            Diccionario con datos de sesión
        """
        try:
            # Obtener driver si no se proporciona
            if not self.driver:
                self.driver = self._get_driver()
            
            logger.info(f"Navegando a {self.url}")
            self.driver.get(self.url)
            
            # Esperar a que cargue la página de login
            wait = WebDriverWait(self.driver, timeout)
            
            # Localizar campos de login (método abstracto para implementar en subclases)
            username_field, password_field, login_button = self._locate_login_elements(wait)
            
            # Ingresar credenciales
            logger.info("Ingresando credenciales...")
            username_field.clear()
            username_field.send_keys(username)
            
            password_field.clear()
            password_field.send_keys(password)
            
            # Hacer clic en login
            login_button.click()
            
            # Esperar a que se complete el login
            self._wait_for_login_completion()
            
            # Verificar si el login fue exitoso
            if self._verify_login_success():
                # Obtener datos de sesión
                self.session_data = {
                    "cookies": self.driver.get_cookies(),
                    "session_id": self._get_session_id(),
                    "url": self.driver.current_url,
                    "logged_in": True
                }
                
                logger.info("Login exitoso")
                return self.session_data
            else:
                raise Exception("Login fallido: Credenciales inválidas o error en la página")
        
        except TimeoutException as e:
            logger.error(f"Timeout durante el login: {e}")
            raise Exception(f"Timeout: No se pudo completar el login en {timeout} segundos")
        except NoSuchElementException as e:
            logger.error(f"Elemento no encontrado: {e}")
            raise Exception("No se encontraron los elementos de login en la página")
        except Exception as e:
            logger.error(f"Error durante el login: {e}")
            raise
    
    def _get_driver(self) -> webdriver.Chrome:
        """
        Obtiene una instancia de WebDriver.
        Usa WebDriverFactory si está disponible, sino crea uno básico.
        
        Returns:
            Instancia de Chrome WebDriver
        """
        try:
            from .web_driver_factory import WebDriverFactory
            return WebDriverFactory.create_driver()
        except ImportError:
            # Fallback si no está disponible el factory
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            logger.error(f"Error al crear WebDriver: {e}")
            raise
    
    @abstractmethod
    def _locate_login_elements(self, wait: WebDriverWait):
        """
        Localiza los elementos de login en la página.
        Debe ser implementado por cada subclase.
        
        Args:
            wait: WebDriverWait para esperar elementos
        
        Returns:
            Tupla con (username_field, password_field, login_button)
        """
        pass
    
    def _wait_for_login_completion(self, seconds: int = 2):
        """
        Espera a que se complete el login.
        Puede ser sobrescrito por subclases si necesitan más tiempo.
        
        Args:
            seconds: Segundos a esperar (default: 2)
        """
        import time
        time.sleep(seconds)
    
    def _verify_login_success(self) -> bool:
        """
        Verifica si el login fue exitoso.
        Puede ser sobrescrito por subclases para lógica específica.
        
        Returns:
            True si el login fue exitoso, False en caso contrario
        """
        try:
            current_url = self.driver.current_url
            
            # Si la URL cambió (ya no está en login)
            if "login" not in current_url.lower():
                return True
            
            # Verificar si hay mensajes de error
            error_elements = self.driver.find_elements(By.CLASS_NAME, "error")
            if error_elements:
                error_text = error_elements[0].text
                logger.warning(f"Error detectado: {error_text}")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"Error al verificar login: {e}")
            return False
    
    def _get_session_id(self) -> Optional[str]:
        """
        Extrae el session ID de las cookies.
        Puede ser sobrescrito por subclases para lógica específica.
        
        Returns:
            Session ID o None
        """
        try:
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                if 'session' in cookie['name'].lower() or 'sid' in cookie['name'].lower():
                    return cookie['value']
            return None
        except:
            return None
    
    def get_driver(self) -> webdriver.Chrome:
        """
        Obtiene el driver actual.
        
        Returns:
            Instancia de WebDriver
        """
        return self.driver
    
    def close(self) -> None:
        """Cierra el driver."""
        if self.driver:
            self.driver.quit()
            logger.info("Driver cerrado")

