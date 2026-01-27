from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    async def run(self):
        """Основной метод выполнения."""
        pass
