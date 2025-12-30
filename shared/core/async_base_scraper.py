"""
Clase base abstracta para operaciones de scraping con Playwright (async).

Proporciona métodos comunes para navegación y extracción de datos.
"""

from abc import ABC
from typing import Optional, Any, Dict
from playwright.async_api import Page, Browser, BrowserContext

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AsyncBaseScraper(ABC):
    """
    Clase base para scraping con Playwright.

    Proporciona funcionalidad común para navegación y scraping.
    """

    def __init__(
        self,
        browser: Optional[Browser] = None,
        context: Optional[BrowserContext] = None,
        page: Optional[Page] = None,
        session_data: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa el scraper.

        Args:
            browser: Instancia del navegador Playwright.
            context: Contexto del navegador.
            page: Página actual.
            session_data: Datos de sesión opcional.
        """
        self.browser = browser
        self.context = context
        self.page = page
        self.session_data = session_data or {}

    async def navigate_to(
        self,
        url: str,
        wait_until: str = 'networkidle'
    ) -> None:
        """
        Navega a una URL específica.

        Args:
            url: URL destino.
            wait_until: Estado de carga a esperar.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.goto(url, wait_until=wait_until)
            logger.info(f"Navegado exitosamente a: {url}")

        except Exception as e:
            logger.error(f"Error al navegar a {url}: {str(e)}")
            raise

    async def click_element(
        self,
        selector: str,
        timeout: int = 30000
    ) -> None:
        """
        Hace clic en un elemento.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera en ms.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
            logger.info(f"Clic exitoso en: {selector}")

        except Exception as e:
            logger.error(f"Error al hacer clic en {selector}: {str(e)}")
            raise

    async def fill_element(
        self,
        selector: str,
        text: str,
        timeout: int = 30000
    ) -> None:
        """
        Rellena un campo con texto.

        Args:
            selector: Selector del elemento.
            text: Texto a ingresar.
            timeout: Tiempo máximo de espera en ms.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.fill(selector, text)
            logger.info(f"Campo rellenado: {selector}")

        except Exception as e:
            logger.error(f"Error al rellenar {selector}: {str(e)}")
            raise

    async def get_text(
        self,
        selector: str,
        timeout: int = 30000
    ) -> str:
        """
        Obtiene el texto de un elemento.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera en ms.

        Returns:
            Texto del elemento.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            element = await self.page.query_selector(selector)
            if element:
                text = await element.text_content()
                logger.info(f"Texto obtenido de: {selector}")
                return text or ""
            return ""

        except Exception as e:
            logger.error(f"Error al obtener texto de {selector}: {str(e)}")
            raise

    async def scroll_down(self, pixels: int = 500) -> None:
        """
        Hace scroll hacia abajo en la página.

        Args:
            pixels: Cantidad de píxeles a desplazar.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            logger.info(f"Scroll down realizado: {pixels}px")

        except Exception as e:
            logger.error(f"Error al hacer scroll: {str(e)}")
            raise

    async def scroll_to_element(self, selector: str) -> None:
        """
        Hace scroll hasta un elemento específico.

        Args:
            selector: Selector del elemento.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            element = await self.page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
                logger.info(f"Scroll al elemento: {selector}")
            else:
                logger.warning(f"Elemento no encontrado: {selector}")

        except Exception as e:
            logger.error(f"Error al hacer scroll al elemento: {str(e)}")
            raise

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 30000,
        state: str = 'visible'
    ) -> bool:
        """
        Espera a que un elemento esté presente.

        Args:
            selector: Selector del elemento.
            timeout: Tiempo máximo de espera en ms.
            state: Estado del elemento ('visible', 'attached', 'hidden').

        Returns:
            True si el elemento aparece, False si timeout.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            await self.page.wait_for_selector(
                selector,
                timeout=timeout,
                state=state
            )
            logger.info(f"Elemento encontrado: {selector}")
            return True

        except Exception as e:
            logger.warning(
                f"Elemento no encontrado {selector}: {str(e)}"
            )
            return False

    async def element_exists(self, selector: str) -> bool:
        """
        Verifica si un elemento existe en la página.

        Args:
            selector: Selector del elemento.

        Returns:
            True si existe, False en caso contrario.

        Raises:
            RuntimeError: Si la página no está inicializada.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        try:
            element = await self.page.query_selector(selector)
            exists = element is not None
            logger.info(
                f"Elemento {selector}: "
                f"{'existe' if exists else 'no existe'}"
            )
            return exists

        except Exception as e:
            logger.error(
                f"Error al verificar existencia de {selector}: {str(e)}"
            )
            return False

    async def close(self) -> None:
        """Cierra el navegador y recursos asociados."""
        try:
            if self.page:
                await self.page.close()
                logger.info("Página cerrada")

            if self.context:
                await self.context.close()
                logger.info("Contexto cerrado")

            if self.browser:
                await self.browser.close()
                logger.info("Browser cerrado")

        except Exception as e:
            logger.error(f"Error al cerrar recursos: {str(e)}")

    def get_page(self) -> Optional[Page]:
        """Retorna la página actual."""
        return self.page

    def get_session_data(self) -> Dict[str, Any]:
        """Retorna los datos de sesión."""
        return self.session_data
