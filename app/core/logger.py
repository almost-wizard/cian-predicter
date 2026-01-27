import sys

from loguru import logger

from app.config import config

# Удаляем стандартный обработчик
logger.remove()

# Добавляем консольный обработчик (читаемый формат)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",  # noqa: E501
    level="INFO",
)

# Добавляем файловый обработчик
logger.add(
    config.LOG_FILE,
    rotation="10 MB",  # Ротация, когда файл достигает 10MB
    retention="1 week",  # Хранить логи 1 неделю
    compression="zip",  # Сжимать старые логи
    level="DEBUG",
    encoding="utf-8",
)

# Экспортируем инициализированный логгер
log = logger
