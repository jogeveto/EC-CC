"""
Utilidades para automatización web con Playwright.

Módulo con funciones helper para operaciones comunes con Playwright async API,
inspirado en web_scraping_utils.py pero adaptado para Playwright.
"""

from typing import Optional
from playwright.async_api import Page, Browser, BrowserContext, TimeoutError

from shared.utils.logger import get_logger

logger = get_logger(__name__)


class PlaywrightUtility:
    """Clase utilitaria para manejar operaciones de Playwright de manera genérica."""

    def __init__(
        self,
        page: Optional[Page] = None,
        browser: Optional[Browser] = None,
        context: Optional[BrowserContext] = None,
    ):
        """
        Inicializa una nueva instancia de PlaywrightUtility.

        Args:
            page: Instancia de Page de Playwright (opcional).
            browser: Instancia de Browser de Playwright (opcional).
            context: Instancia de BrowserContext de Playwright (opcional).
        """
        self.page = page
        self.browser = browser
        self.context = context

    async def wait_for_element(
        self, selector: str, timeout: int = 10000, state: str = "visible"
    ) -> bool:
        """
        Espera a que un elemento esté presente en la página.

        Args:
            selector: Selector del elemento (CSS, XPath).
            timeout: Tiempo máximo de espera en milisegundos.
            state: Estado del elemento ('attached', 'visible', 'hidden').

        Returns:
            True si el elemento se encontró, False si hubo timeout.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            await self.page.wait_for_selector(
                selector, timeout=timeout, state=state
            )
            logger.info(f"Elemento encontrado: {selector}")
            return True

        except TimeoutError:
            logger.warning(
                f"Timeout esperando elemento: {selector} (timeout={timeout}ms)"
            )
            return False

        except Exception as e:
            logger.error(f"Error esperando elemento {selector}: {str(e)}")
            return False

    async def click_element(
        self,
        selector: str,
        timeout: int = 10000,
        wait_after: int = 500,
        description: str = "",
    ) -> bool:
        """
        Hace clic en un elemento después de encontrarlo.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera.
            wait_after: Tiempo de espera después del clic (ms).
            description: Descripción del elemento para logs.

        Returns:
            True si el clic fue exitoso, False si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            # Esperar a que el elemento sea clickeable
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )

            if not element:
                logger.error(f"Elemento no encontrado: {selector}")
                return False

            # Hacer clic
            await element.click()

            desc_text = description or selector
            logger.info(f"Clic realizado en: {desc_text}")

            # Esperar después del clic si se especificó
            if wait_after > 0:
                await self.page.wait_for_timeout(wait_after)

            return True

        except TimeoutError:
            logger.error(f"Timeout haciendo clic en: {selector}")
            return False

        except Exception as e:
            logger.error(f"Error haciendo clic en {selector}: {str(e)}")
            return False

    async def fill_input(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout: int = 10000,
        description: str = "",
    ) -> bool:
        """
        Llena un campo de entrada con texto.

        Args:
            selector: Selector del input.
            text: Texto a ingresar.
            clear_first: Si debe limpiar el campo primero.
            timeout: Tiempo máximo de espera.
            description: Descripción del campo para logs.

        Returns:
            True si se llenó exitosamente, False si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            # Esperar a que el elemento esté visible
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )

            if not element:
                logger.error(f"Input no encontrado: {selector}")
                return False

            # Limpiar si se especificó
            if clear_first:
                await element.fill("")

            # Llenar con el texto
            await element.fill(text)

            desc_text = description or selector
            logger.info(f"Texto ingresado en: {desc_text}")

            return True

        except TimeoutError:
            logger.error(f"Timeout llenando input: {selector}")
            return False

        except Exception as e:
            logger.error(f"Error llenando input {selector}: {str(e)}")
            return False

    async def get_text(
        self, selector: str, timeout: int = 10000, description: str = ""
    ) -> Optional[str]:
        """
        Obtiene el texto de un elemento.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera.
            description: Descripción del elemento para logs.

        Returns:
            Texto del elemento o None si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return None

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )

            if not element:
                logger.error(f"Elemento no encontrado: {selector}")
                return None

            text = await element.text_content()

            desc_text = description or selector
            logger.info(f"Texto obtenido de: {desc_text}")

            return text.strip() if text else ""

        except TimeoutError:
            logger.error(f"Timeout obteniendo texto de: {selector}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo texto de {selector}: {str(e)}")
            return None

    async def is_element_visible(
        self, selector: str, timeout: int = 5000
    ) -> bool:
        """
        Verifica si un elemento está visible.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera.

        Returns:
            True si el elemento está visible, False si no.
        """
        if not self.page:
            return False

        try:
            element = await self.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )
            return element is not None

        except TimeoutError:
            return False

        except Exception:
            return False

    async def wait_for_navigation(
        self, timeout: int = 30000, wait_until: str = "networkidle"
    ) -> bool:
        """
        Espera a que la navegación se complete.

        Args:
            timeout: Tiempo máximo de espera.
            wait_until: Evento a esperar ('load', 'networkidle', 'domcontentloaded').

        Returns:
            True si la navegación completó, False si hubo timeout.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            await self.page.wait_for_load_state(wait_until, timeout=timeout)
            logger.info(f"Navegación completada (wait_until={wait_until})")
            return True

        except TimeoutError:
            logger.warning(f"Timeout esperando navegación ({wait_until})")
            return False

        except Exception as e:
            logger.error(f"Error esperando navegación: {str(e)}")
            return False

    async def take_screenshot(
        self, file_path: str, full_page: bool = False
    ) -> bool:
        """
        Captura una screenshot de la página.

        Args:
            file_path: Ruta donde guardar la screenshot.
            full_page: Si debe capturar toda la página o solo el viewport.

        Returns:
            True si se capturó exitosamente, False si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            await self.page.screenshot(path=file_path, full_page=full_page)
            logger.info(f"Screenshot guardada: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error capturando screenshot: {str(e)}")
            return False

    async def evaluate_script(self, script: str) -> Optional[any]:
        """
        Ejecuta JavaScript en la página.

        Args:
            script: Código JavaScript a ejecutar.

        Returns:
            Resultado de la ejecución o None si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return None

        try:
            result = await self.page.evaluate(script)
            logger.info("Script JavaScript ejecutado exitosamente")
            return result

        except Exception as e:
            logger.error(f"Error ejecutando script: {str(e)}")
            return None

    async def close_browser(self) -> None:
        """Cierra el navegador y limpia recursos."""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("Navegador cerrado")

        except Exception as e:
            logger.error(f"Error cerrando navegador: {str(e)}")

    async def navigate_to(self, url: str, timeout: int = 30000) -> bool:
        """
        Navega a una URL específica.

        Args:
            url: URL a la que se desea navegar.
            timeout: Tiempo máximo de espera.

        Returns:
            True si la navegación fue exitosa, False si hubo error.
        """
        if not self.page:
            logger.error("Página no inicializada")
            return False

        try:
            logger.info(f"Navegando a: {url}")
            await self.page.goto(url, timeout=timeout, wait_until="networkidle")
            logger.info(f"Navegación exitosa a: {url}")
            return True

        except TimeoutError:
            logger.error(f"Timeout navegando a: {url}")
            return False

        except Exception as e:
            logger.error(f"Error navegando a {url}: {str(e)}")
            return False
