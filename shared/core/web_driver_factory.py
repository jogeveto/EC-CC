# coding: utf-8
"""
Factory para crear instancias de WebDriver con configuración común.
"""

from typing import Optional, List
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from shared.utils.logger import get_logger

logger = get_logger("WebDriverFactory")


class WebDriverFactory:
    """Factory para crear WebDrivers con configuración estándar."""
    
    @staticmethod
    def _get_rocketbot_base_path() -> Optional[str]:
        """
        Obtiene la ruta base de Rocketbot usando múltiples estrategias.
        
        Returns:
            Ruta base de Rocketbot si se encuentra, None si no
        """
        # Estrategia 1: Usar tmp_global_obj (Rocketbot inyecta esto)
        try:
            tmp_global_obj  # type: ignore[name-defined]
            base_path = tmp_global_obj.get("basepath", "")
            if base_path and os.path.isdir(base_path):
                logger.debug(f"Rocketbot basepath desde tmp_global_obj: {base_path}")
                return base_path
        except (NameError, AttributeError, KeyError):
            pass
        
        # Estrategia 2: Calcular desde la ubicación del archivo actual
        # shared/core/web_driver_factory.py -> shared/ -> modules/ -> Rocketbot/
        current_file = os.path.abspath(__file__)
        # Subir niveles: web_driver_factory.py -> core/ -> shared/ -> modules/ -> Rocketbot/
        shared_dir = os.path.dirname(os.path.dirname(current_file))  # shared/
        modules_dir = os.path.dirname(shared_dir)  # modules/
        rocketbot_base = os.path.dirname(modules_dir)  # Rocketbot/
        
        if os.path.isdir(rocketbot_base):
            # Verificar que realmente es Rocketbot buscando indicadores
            if os.path.isdir(os.path.join(rocketbot_base, "modules")) or \
               os.path.isdir(os.path.join(rocketbot_base, "drivers")):
                logger.debug(f"Rocketbot basepath calculado desde archivo: {rocketbot_base}")
                return rocketbot_base
        
        # Estrategia 3: Buscar desde el directorio de trabajo actual
        cwd = os.getcwd()
        # Si estamos en modules/Docuware, subir dos niveles
        if "modules" in cwd:
            parts = cwd.split(os.sep)
            try:
                modules_idx = parts.index("modules")
                rocketbot_base = os.sep.join(parts[:modules_idx])
                if os.path.isdir(rocketbot_base):
                    logger.debug(f"Rocketbot basepath desde cwd: {rocketbot_base}")
                    return rocketbot_base
            except ValueError:
                pass
        
        # Estrategia 4: Buscar en rutas comunes de instalación
        common_paths = [
            r"C:\Rocketbot",
            r"C:\Program Files\Rocketbot",
            r"C:\Program Files (x86)\Rocketbot",
        ]
        
        for common_path in common_paths:
            if os.path.isdir(common_path):
                # Verificar que tiene la estructura de Rocketbot
                if os.path.isdir(os.path.join(common_path, "modules")) or \
                   os.path.isdir(os.path.join(common_path, "drivers")):
                    logger.debug(f"Rocketbot basepath encontrado en ubicación común: {common_path}")
                    return common_path
        
        return None
    
    @staticmethod
    def _find_chromedriver() -> Optional[str]:
        """
        Busca ChromeDriver en ubicaciones comunes, priorizando la ruta de Rocketbot.
        
        Returns:
            Ruta al ChromeDriver si se encuentra, None si no
        """
        possible_paths = []
        
        # PRIORIDAD 1: Ruta estándar de Rocketbot (drivers\win\chrome\chromedriver.exe)
        rocketbot_base = WebDriverFactory._get_rocketbot_base_path()
        if rocketbot_base:
            # Ruta estándar: Rocketbot\drivers\win\chrome\chromedriver.exe
            standard_path = os.path.join(rocketbot_base, "drivers", "win", "chrome", "chromedriver.exe")
            possible_paths.append(standard_path)
            logger.debug(f"Agregada ruta estándar de Rocketbot: {standard_path}")
            
            # Otras ubicaciones posibles en Rocketbot
            rocketbot_paths = [
                os.path.join(rocketbot_base, "drivers", "chromedriver.exe"),
                os.path.join(rocketbot_base, "chromedriver.exe"),
                os.path.join(rocketbot_base, "selenium", "webdriver", "common", "windows", "chromedriver.exe"),
                os.path.join(rocketbot_base, "libs", "chromedriver.exe"),
            ]
            possible_paths.extend(rocketbot_paths)
        
        # PRIORIDAD 2: Rutas relativas desde el proyecto
        # Si estamos en modules/Docuware, subir a Rocketbot y buscar drivers
        current_file = os.path.abspath(__file__)
        # shared/core/web_driver_factory.py -> shared/ -> modules/ -> Rocketbot/
        try:
            shared_dir = os.path.dirname(os.path.dirname(current_file))
            modules_dir = os.path.dirname(shared_dir)
            rocketbot_from_file = os.path.dirname(modules_dir)
            relative_path = os.path.join(rocketbot_from_file, "drivers", "win", "chrome", "chromedriver.exe")
            if os.path.isfile(relative_path):
                possible_paths.append(relative_path)
                logger.debug(f"Agregada ruta relativa desde archivo: {relative_path}")
        except Exception:
            pass
        
        # PRIORIDAD 3: Desde el directorio de trabajo actual
        cwd = os.getcwd()
        # Si cwd contiene "modules", intentar construir ruta relativa
        if "modules" in cwd:
            try:
                # Encontrar índice de "modules" y construir ruta hacia Rocketbot
                parts = cwd.split(os.sep)
                if "modules" in parts:
                    modules_idx = parts.index("modules")
                    rocketbot_from_cwd = os.sep.join(parts[:modules_idx])
                    relative_path = os.path.join(rocketbot_from_cwd, "drivers", "win", "chrome", "chromedriver.exe")
                    if os.path.isfile(relative_path):
                        possible_paths.append(relative_path)
                        logger.debug(f"Agregada ruta relativa desde cwd: {relative_path}")
            except Exception:
                pass
        
        # PRIORIDAD 4: Otras ubicaciones comunes
        possible_paths.extend([
            # Directorio actual
            os.path.join(os.getcwd(), "chromedriver.exe"),
            # En el directorio del módulo
            os.path.join(os.path.dirname(__file__), "chromedriver.exe"),
            # En el directorio shared
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "chromedriver.exe"),
            # En el directorio modules
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chromedriver.exe"),
        ])
        
        # PRIORIDAD 5: PATH del sistema (último recurso)
        possible_paths.append("chromedriver.exe")
        
        # Buscar en todas las rutas
        for path in possible_paths:
            if not path:
                continue
            try:
                # Normalizar la ruta
                normalized_path = os.path.normpath(path)
                if os.path.isfile(normalized_path):
                    logger.info(f"✓ ChromeDriver encontrado en: {normalized_path}")
                    return normalized_path
            except Exception as e:
                logger.debug(f"Error verificando ruta {path}: {e}")
                continue
        
        logger.warning("ChromeDriver no encontrado en ninguna ubicación")
        return None
    
    @staticmethod
    def create_driver(headless: bool = False, 
                     additional_options: Optional[List[str]] = None,
                     chromedriver_path: Optional[str] = None) -> webdriver.Chrome:
        """
        Crea una instancia de Chrome WebDriver con configuración común.
        
        Args:
            headless: Si True, ejecuta en modo headless
            additional_options: Lista adicional de opciones de Chrome
            chromedriver_path: Ruta opcional al ChromeDriver (si None, intenta encontrarlo automáticamente)
        
        Returns:
            Instancia de Chrome WebDriver
        
        Example:
            driver = WebDriverFactory.create_driver(headless=True)
        """
        try:
            options = ChromeOptions()
            
            # Opciones estándar
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            # Deshabilitar Selenium Manager para evitar errores de detección
            options.add_experimental_option('useAutomationExtension', False)
            
            # Deshabilitar guardado de contraseñas y autocompletado
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2,  # Bloquear notificaciones
            }
            options.add_experimental_option("prefs", prefs)
            # Intentar deshabilitar Selenium Manager explícitamente
            try:
                # En versiones recientes de Selenium, podemos deshabilitar Selenium Manager
                options.add_experimental_option('detach', True)
            except:
                pass
            
            # Modo headless
            if headless:
                options.add_argument('--headless')
            
            # Opciones adicionales
            if additional_options:
                for option in additional_options:
                    options.add_argument(option)
            
            # Intentar usar ChromeDriver manual si está disponible
            service = None
            if chromedriver_path:
                if os.path.isfile(chromedriver_path):
                    logger.info(f"Usando ChromeDriver especificado: {chromedriver_path}")
                    service = ChromeService(chromedriver_path)
                else:
                    logger.warning(f"ChromeDriver especificado no encontrado: {chromedriver_path}")
            else:
                # Buscar ChromeDriver automáticamente
                chromedriver_found = WebDriverFactory._find_chromedriver()
                if chromedriver_found:
                    logger.info(f"Usando ChromeDriver encontrado: {chromedriver_found}")
                    service = ChromeService(chromedriver_found)
                else:
                    logger.info("ChromeDriver no encontrado, usando Selenium Manager (puede fallar si no detecta Chrome)")
            
            # Crear driver con o sin Service
            if service:
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Intentar crear sin Service (usará Selenium Manager)
                # Si falla, intentar con Service vacío para forzar búsqueda en PATH
                try:
                    driver = webdriver.Chrome(options=options)
                except Exception as selenium_manager_error:
                    if "Selenium Manager" in str(selenium_manager_error) or "chromedriver" in str(selenium_manager_error).lower():
                        logger.warning("Selenium Manager falló, intentando buscar ChromeDriver en PATH del sistema...")
                        # Intentar sin Service (buscará en PATH)
                        try:
                            service = ChromeService()  # Service vacío busca en PATH
                            driver = webdriver.Chrome(service=service, options=options)
                        except Exception as path_error:
                            logger.error(f"Error al crear WebDriver: {path_error}")
                            logger.error("Sugerencia: Instala ChromeDriver manualmente o asegúrate de que Chrome esté instalado correctamente")
                            raise selenium_manager_error from path_error
                    else:
                        raise
            
            # Configuraciones adicionales del driver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("WebDriver creado exitosamente")
            return driver
        
        except Exception as e:
            logger.error(f"Error al crear WebDriver: {e}")
            error_msg = str(e)
            if "Selenium Manager" in error_msg or "chromedriver" in error_msg.lower():
                logger.error("SOLUCIÓN: Instala ChromeDriver manualmente:")
                logger.error("  1. Descarga ChromeDriver desde https://chromedriver.chromium.org/")
                logger.error("  2. Colócalo en el PATH del sistema o en el directorio del proyecto")
                logger.error("  3. O especifica la ruta con: WebDriverFactory.create_driver(chromedriver_path='ruta/al/chromedriver.exe')")
            raise
    
    @staticmethod
    def create_driver_with_profile(profile_path: Optional[str] = None,
                                  chromedriver_path: Optional[str] = None) -> webdriver.Chrome:
        """
        Crea un WebDriver con un perfil de usuario específico.
        
        Args:
            profile_path: Ruta al perfil de usuario de Chrome
            chromedriver_path: Ruta opcional al ChromeDriver
        
        Returns:
            Instancia de Chrome WebDriver
        """
        try:
            options = ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            if profile_path:
                options.add_argument(f'--user-data-dir={profile_path}')
            
            # Usar el mismo método de búsqueda de ChromeDriver
            service = None
            if chromedriver_path:
                if os.path.isfile(chromedriver_path):
                    service = ChromeService(chromedriver_path)
            else:
                chromedriver_found = WebDriverFactory._find_chromedriver()
                if chromedriver_found:
                    service = ChromeService(chromedriver_found)
            
            if service:
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            logger.info("WebDriver con perfil creado exitosamente")
            return driver
        
        except Exception as e:
            logger.error(f"Error al crear WebDriver con perfil: {e}")
            raise

