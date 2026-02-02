from catboost import CatBoostRegressor
from loguru import logger
from app.core.config import settings


class ModelService:
    """
    Сервис-обертка над ML-моделью CatBoost.
    Отвечает за загрузку файла и выполнение предсказания.
    """

    _model = None
    _feature_names = []

    @classmethod
    def load_model(cls):
        """
        Загружает модель в память.
        """
        if cls._model is None:
            logger.info(f"Загрузка модели из: {settings.MODEL_PATH}")
            if not settings.MODEL_PATH.exists():
                logger.error(f"Файл модели не найден: {settings.MODEL_PATH}")
                raise FileNotFoundError(f"Model not found at {settings.MODEL_PATH}")

            try:
                cls._model = CatBoostRegressor()
                cls._model.load_model(str(settings.MODEL_PATH))
                cls._feature_names = cls._model.feature_names_
                logger.info("Модель успешно загружена.")
                logger.debug(f"Признаки модели: {cls._feature_names}")
            except Exception as e:
                logger.critical(f"Не удалось загрузить модель: {e}")
                raise e
        return cls._model

    @classmethod
    def get_feature_names(cls):
        if not cls._feature_names:
            cls.load_model()
        return cls._feature_names

    @classmethod
    def predict(cls, data_pool) -> list:
        """
        Выполняет предсказание.
        """
        model = cls.load_model()
        return model.predict(data_pool)
