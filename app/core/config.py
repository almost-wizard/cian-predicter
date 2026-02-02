from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """
    Конфигурация приложения.
    Использует pydantic-settings для загрузки переменных окружения.
    """

    PROJECT_NAME: str = "Cian Price Predicter"
    VERSION: str = "1.0.0"

    # --- Пути к файлам ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODEL_PATH: Path = BASE_DIR / "models" / "catboost_price_predictor.cbm"

    # --- ML Параметры ---
    # Границы диапазона цены, используемые для отображения "вилки" цены
    PREDICTION_MARGIN_PERCENT: float = 0.15

    # --- Логирование ---
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
