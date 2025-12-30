"""
Clase base abstracta para operaciones de login usando Playwright (async).

Implementa el patrón Template Method para el flujo de autenticación.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from playwright.async_api import Page, Browser, BrowserContext, Playwright

from .playwright_factory import PlaywrightFactory
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AsyncBaseLogin(ABC):
    """
    Clase base abstracta para login con Playwright.

    Implementa Template Method pattern para flujo de autenticación.
    Las subclases deben implementar métodos abstractos específicos.
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        headless: bool = True,
        playwright_instance: Optional[Playwright] = None
    ):
        """
        Inicializa el handler de login.

        Args:
            url: URL de la página de login.
            username: Usuario para autenticación.
            password: Contraseña para autenticación.
            headless: Modo de ejecución del navegador.
            playwright_instance: Instancia de Playwright.
        """
        self.url = url
        self.username = username
        self.password = password
        self.headless = headless
        self.playwright_instance = playwright_instance
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_data: Dict[str, Any] = {}

    @abstractmethod
    async def locate_login_elements(
        self,
        page: Page
    ) -> Tuple[str, str, str]:
        """
        Localiza los elementos del formulario de login.

        Args:
            page: Página actual de Playwright.

        Returns:
            Tuple con (username_selector, password_selector,
                      submit_button_selector).
        """
        pass

    async def wait_for_login_completion(self, page: Page) -> None:
        """
        Espera a que se complete el login.

        Puede ser sobrescrito por subclases para lógica personalizada.

        Args:
            page: Página actual de Playwright.
        """
        await page.wait_for_load_state('networkidle', timeout=10000)
        logger.info("Login completado - página cargada")

    async def verify_login_success(self, page: Page) -> bool:
        """
        Verifica si el login fue exitoso.

        Puede ser sobrescrito por subclases.

        Args:
            page: Página actual de Playwright.

        Returns:
            True si login exitoso, False en caso contrario.
        """
        return page.url != self.url

    async def extract_session_data(self, page: Page) -> Dict[str, Any]:
        """
        Extrae datos de sesión después del login.

        Puede ser sobrescrito por subclases.

        Args:
            page: Página actual de Playwright.

        Returns:
            Diccionario con datos de sesión.
        """
        return {
            'url': page.url,
            'title': await page.title()
        }

    async def create_browser(self) -> None:
        """Crea instancia del navegador."""
        self.browser = await PlaywrightFactory.create_browser(
            headless=self.headless,
            playwright_instance=self.playwright_instance
        )
        logger.info("Browser creado para login")

    async def create_context(
        self,
        storage_state: Optional[str] = None
    ) -> None:
        """
        Crea contexto del navegador.

        Args:
            storage_state: Ruta opcional al archivo de storage state.
        """
        if not self.browser:
            raise RuntimeError("Browser no inicializado")

        self.context = await PlaywrightFactory.create_context(
            browser=self.browser,
            storage_state=storage_state
        )
        logger.info("Contexto creado para login")

    async def create_page(self) -> None:
        """Crea nueva página en el contexto."""
        if not self.context:
            raise RuntimeError("Contexto no inicializado")

        self.page = await PlaywrightFactory.create_page(self.context)
        logger.info("Página creada para login")

    async def navigate_to_login(self) -> None:
        """Navega a la URL de login."""
        if not self.page:
            raise RuntimeError("Página no inicializada")

        await self.page.goto(self.url, wait_until='networkidle')
        logger.info(f"Navegado a URL de login: {self.url}")

    async def fill_credentials(
        self,
        username_selector: str,
        password_selector: str
    ) -> None:
        """
        Rellena las credenciales en el formulario.

        Args:
            username_selector: Selector del campo de usuario.
            password_selector: Selector del campo de contraseña.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        await self.page.fill(username_selector, self.username)
        logger.info("Campo de usuario rellenado")

        await self.page.fill(password_selector, self.password)
        logger.info("Campo de contraseña rellenado")

    async def submit_login(self, submit_selector: str) -> None:
        """
        Hace clic en el botón de submit.

        Args:
            submit_selector: Selector del botón de submit.
        """
        if not self.page:
            raise RuntimeError("Página no inicializada")

        await self.page.click(submit_selector)
        logger.info("Botón de login presionado")

    async def login(
        self,
        storage_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de login (Template Method).

        Args:
            storage_state: Ruta opcional al storage state guardado.

        Returns:
            Diccionario con datos de sesión.

        Raises:
            Exception: Si el login falla.
        """
        try:
            logger.info("Iniciando proceso de login")

            await self.create_browser()
            await self.create_context(storage_state)
            await self.create_page()
            await self.navigate_to_login()

            user_sel, pass_sel, submit_sel = (
                await self.locate_login_elements(self.page)
            )

            await self.fill_credentials(user_sel, pass_sel)
            await self.submit_login(submit_sel)
            await self.wait_for_login_completion(self.page)

            if not await self.verify_login_success(self.page):
                raise Exception("Login fallido - verificación no exitosa")

            self.session_data = await self.extract_session_data(self.page)
            logger.info("Login exitoso")

            return self.session_data

        except Exception as e:
            logger.error(f"Error durante login: {str(e)}")
            await self.close()
            raise

    async def save_storage_state(self, path: str) -> None:
        """
        Guarda el storage state actual.

        Args:
            path: Ruta donde guardar el storage state.
        """
        if not self.context:
            raise RuntimeError("Contexto no inicializado")

        await PlaywrightFactory.save_storage_state(self.context, path)

    async def close(self) -> None:
        """Cierra página, contexto y navegador."""
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

    def get_browser(self) -> Optional[Browser]:
        """Retorna el navegador actual."""
        return self.browser

    def get_context(self) -> Optional[BrowserContext]:
        """Retorna el contexto actual."""
        return self.context
