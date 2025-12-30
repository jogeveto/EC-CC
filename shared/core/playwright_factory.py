"""
Factory para crear instancias de Browser y Context de Playwright.

Este módulo proporciona métodos centralizados para crear navegadores
Playwright con configuraciones estándar y manejo de contextos.
"""

from typing import Optional, Dict, Any
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlaywrightFactory:
    """
    Factory para creación de navegadores Playwright.

    Proporciona métodos para crear browsers y contexts con
    configuraciones predefinidas y optimizadas.
    """

    @staticmethod
    async def create_browser(
        headless: bool = True,
        playwright_instance: Optional[Playwright] = None
    ) -> Browser:
        """
        Crea una instancia de browser Chromium con configuración estándar.

        Args:
            headless: Si el navegador debe ejecutarse sin UI (True)
                     o visible (False).
            playwright_instance: Instancia de Playwright opcional.

        Returns:
            Browser: Instancia del navegador Chromium.

        Raises:
            Exception: Si falla la creación del navegador.
        """
        try:
            if playwright_instance is None:
                logger.error(
                    "No se proporcionó instancia de Playwright. "
                    "Use async with async_playwright() as p"
                )
                raise ValueError("playwright_instance es requerido")

            launch_options = {
                'headless': headless,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            }

            # Si no es headless, abrir maximizado
            if not headless:
                launch_options['args'].extend([
                    '--start-maximized',
                    '--disable-infobars',
                    '--window-position=0,0'
                ])

            browser = await playwright_instance.chromium.launch(
                **launch_options
            )
            logger.info(
                f"Browser Chromium creado exitosamente. "
                f"Headless: {headless}"
            )
            return browser

        except Exception as e:
            logger.error(f"Error al crear browser: {str(e)}")
            raise

    @staticmethod
    async def create_context(
        browser: Browser,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        storage_state: Optional[str] = None
    ) -> BrowserContext:
        """
        Crea un contexto de navegador con configuración personalizada.

        Args:
            browser: Instancia del navegador.
            viewport: Diccionario con 'width' y 'height' del viewport.
            user_agent: User agent personalizado.
            storage_state: Ruta al archivo JSON con storage state.

        Returns:
            BrowserContext: Contexto del navegador creado.

        Raises:
            Exception: Si falla la creación del contexto.
        """
        try:
            context_options: Dict[str, Any] = {
                'locale': 'es-CO',
                'timezone_id': 'America/Bogota'
            }

            # Configurar viewport
            # None = usar tamaño de ventana del navegador (maximizado)
            if viewport is not None:
                context_options['viewport'] = viewport
            else:
                # No viewport = usar tamaño de ventana completo
                context_options['viewport'] = None

            if user_agent:
                context_options['user_agent'] = user_agent

            if storage_state:
                context_options['storage_state'] = storage_state
                logger.info(
                    f"Restaurando sesión desde: {storage_state}"
                )

            context = await browser.new_context(**context_options)
            logger.info("Contexto del navegador creado exitosamente")
            return context

        except Exception as e:
            logger.error(f"Error al crear contexto: {str(e)}")
            raise

    @staticmethod
    async def create_page(context: BrowserContext) -> Page:
        """
        Crea una nueva página en el contexto especificado.

        Args:
            context: Contexto del navegador.

        Returns:
            Page: Nueva página creada.

        Raises:
            Exception: Si falla la creación de la página.
        """
        try:
            page = await context.new_page()
            logger.info("Nueva página creada exitosamente")
            return page

        except Exception as e:
            logger.error(f"Error al crear página: {str(e)}")
            raise

    @staticmethod
    async def save_storage_state(
        context: BrowserContext,
        path: str
    ) -> None:
        """
        Guarda el storage state del contexto actual.

        Args:
            context: Contexto del navegador.
            path: Ruta donde guardar el storage state.

        Raises:
            Exception: Si falla el guardado del storage state.
        """
        try:
            await context.storage_state(path=path)
            logger.info(f"Storage state guardado en: {path}")

        except Exception as e:
            logger.error(f"Error al guardar storage state: {str(e)}")
            raise
