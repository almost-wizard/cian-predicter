from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config import config
from app.core.logger import log
from app.core.ua_manager import UserAgentManager


class BrowserService:
    """
    Управляет экземпляром браузера Playwright и контекстами.
    """

    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.ua_manager = UserAgentManager()

    async def start(self):
        """Инициализирует браузер."""
        log.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",  # Помогает избежать простого обнаружения ботов
                "--no-sandbox",
            ],
        )
        log.info("Browser started.")

    async def get_new_context(self) -> tuple[BrowserContext, Page]:
        """
        Создает новый инкогнито-контекст со свежим User-Agent.

        Returns:
            tuple[BrowserContext, Page]: Кортеж из контекста браузера и страницы.
        """
        if not self.browser:
            await self.start()

        user_agent = self.ua_manager.get_random_ua()

        # Создаем контекст с заданным viewport и UA
        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )

        # Добавляем init-скрипт для маскировки свойства webdriver (дополнительная защита)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()
        return context, page

    async def stop(self):
        """Закрывает браузер."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        log.info("Browser stopped.")
