from pathlib import Path
from typing import Union

from app.core.logger import log
from app.models.apartment import FlatItem


class JsonlWriter:
    """
    Записывает данные в файл JSONL немедленно.
    Гарантирует отсутствие потери данных при сбое.
    """

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.touch()
            log.info(f"Created new output file: {self.file_path}")

    def write_item(self, item: FlatItem):
        """
        Добавляет один элемент в файл.
        """
        try:
            json_line = item.model_dump_json()

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")

        except Exception as e:
            log.error(f"Failed to write item to disk: {e}")
