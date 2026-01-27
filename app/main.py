"""
Модуль запуска парсера Cian Parser.

Этот скрипт инициализирует и запускает процесс парсинга, обрабатывая основные исключения
и сигналы завершения.
"""

import asyncio

from app.core.logger import log
from app.parser.cian import CianParser


async def main():
    """
    Основная точка входа в приложение.

    Инициализирует парсер и запускает асинхронный цикл сбора данных.
    """
    log.info("Starting Cian Parser...")
    parser = CianParser()
    await parser.run()
    log.info("Job finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as e:
        log.critical(f"Unexpected crash: {e}")
