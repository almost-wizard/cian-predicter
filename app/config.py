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
    TIMEOUT: int = 30000  # мс для playwright
    MAX_RETRIES: int = 3
    DELAY_RANGE: tuple[int, int] = (2, 5)  # секунды между запросами

    # Коэффициент рандомизации (0.25 = +/- 25% отклонения от выбранного времени)
    TIME_VARIANCE: float = 0.25

    # Пути к файлам
    OUTPUT_FILE = DATA_DIR / "cian_rentals.jsonl"
    LOG_FILE = LOGS_DIR / "parser.log"

    # Настройки браузера
    # В Docker/CI обычно нужен режим Headless. По умолчанию True, если не указано иное.
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() in ("true", "1", "yes")


config = Config()
