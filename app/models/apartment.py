from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FlatItem(BaseModel):
    """
    Детальная модель данных об аренде квартиры.
    """

    # --- Основная информация ---
    url: str
    title: str = ""

    # --- Цена ---
    price_per_month: Optional[int] = None
    price_currency: str = "RUB"
    cian_estimated_price: Optional[int] = None  # Оценка циана

    # --- Местоположение ---
    address: str = ""  # Полный соединенный адрес
    metro_count: int = 0
    metro_nearest_time: str = ""

    # --- Ключевые характеристики ---
    total_area: str = ""
    floor: str = ""

    # --- Динамические факты ---
    # Пример: {"general_area": "34 м²", "payment_utility": "not_included"}
    facts: Dict[str, str] = Field(default_factory=dict)

    # --- Особенности (флаги) ---
    # Пример: ["Холодильник", "Интернет"]
    features: List[str] = Field(default_factory=list)

    # --- Метаданные ---
    parsed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
