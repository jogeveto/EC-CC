# coding: utf-8
"""
Módulo core con interfaces y clases base para módulos web.
Incluye tanto implementaciones Selenium (legacy) como Playwright (async).
"""

# Playwright async (nueva implementación)
try:
    from .async_base_login import AsyncBaseLogin
    from .async_base_scraper import AsyncBaseScraper
    from .playwright_factory import PlaywrightFactory
except ImportError:
    AsyncBaseLogin = None
    AsyncBaseScraper = None
    PlaywrightFactory = None

__all__ = [
    # Playwright async
    "AsyncBaseLogin",
    "AsyncBaseScraper",
    "PlaywrightFactory",
]
