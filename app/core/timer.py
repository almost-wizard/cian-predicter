import asyncio
import random

from app.config import config
from app.core.logger import log


class Timer:
    """
    Управляет искусственными задержками со случайным разбросом для имитации поведения человека.
    """

    def __init__(self):
        self.variance = config.TIME_VARIANCE

    async def sleep(self, min_s: float, max_s: float):
        """
        Ожидает в течение случайного промежутка времени в интервале [min_s, max_s]
        плюс/минус настроенный процент отклонения (variance).

        Args:
            min_s (float): Минимальное базовое время ожидания.
            max_s (float): Максимальное базовое время ожидания.
        """
        if min_s > max_s:
            min_s, max_s = max_s, min_s

        # 1. Выбираем базовое время из предоставленного интервала
        base_time = random.uniform(min_s, max_s)

        # 2. Вычисляем пределы отклонения
        # например, если база 3с и variance 0.25 (25%), дельта равна 0.75с
        delta = base_time * self.variance

        # 3. Применяем отклонение (случайно добавляем или вычитаем в пределах дельты)
        # Итоговое время будет в диапазоне [base - delta, base + delta]
        final_time = base_time + random.uniform(-delta, delta)

        # Убеждаемся, что время ожидания никогда не будет отрицательным или слишком малым
        final_time = max(0.5, final_time)

        log.debug(
            f"Sleeping for {final_time:.2f}s (Base: {base_time:.2f}s +/- {self.variance * 100}%)"
        )
        await asyncio.sleep(final_time)
