import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Убеждаемся, что директории существуют
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class Config:
    """
    Конфигурация приложения.

    Содержит настройки для парсера, путей к файлам, таймаутов и параметров браузера.
    """

    BASE_URL = "https://spb.cian.ru/snyat-kvartiru/"

    # Настройки парсера
    START_PAGE: int = int(os.getenv("START_PAGE", "40"))

    # FIXME: Absolutely useless timeout...
    # Таймаут загрузки страницы (Playwright)
    TIMEOUT: int = 30000  # мс (начальный)
    MAX_PAGE_TIMEOUT: int = 60000  # мс (предел)

    # Задержки между повторными попытками (Exponential Backoff)
    BASE_RETRY_DELAY: int = 5  # секунд
    MAX_RETRY_DELAY: int = 600  # секунд (10 минут)
    RETRY_DELAY_MULTIPLIER: float = 2.0

    MAX_RETRIES: int = 5
    SUCCESS_THRESHOLD_FOR_RESET: int = 5  # Сброс после N успехов

    DELAY_RANGE: tuple[int, int] = (2, 5)  # секунды между запросами (штатная пауза)

    # Коэффициент рандомизации (0.25 = +/- 25% отклонения от выбранного времени)
    TIME_VARIANCE: float = 0.25

    # Пути к файлам
    OUTPUT_FILE = DATA_DIR / "cian_rentals.jsonl"
    LOG_FILE = LOGS_DIR / "parser.log"

    # Настройки браузера
    # В Docker/CI обычно нужен режим Headless. По умолчанию True, если не указано иное.
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() in ("true", "1", "yes")


config = Config()
