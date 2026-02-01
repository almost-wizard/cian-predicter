from catboost import CatBoostRegressor
from loguru import logger
from app.core.config import settings


class ModelService:
    _model = None
    _feature_names = []

    @classmethod
    def load_model(cls):
        if cls._model is None:
            logger.info(f"Loading model from: {settings.MODEL_PATH}")
            if not settings.MODEL_PATH.exists():
                logger.error(f"Model file not found: {settings.MODEL_PATH}")
                raise FileNotFoundError(f"Model not found at {settings.MODEL_PATH}")

            try:
                cls._model = CatBoostRegressor()
                cls._model.load_model(str(settings.MODEL_PATH))
                cls._feature_names = cls._model.feature_names_
                logger.info("Model loaded successfully.")
                logger.debug(f"Model features: {cls._feature_names}")
            except Exception as e:
                logger.critical(f"Failed to load model: {e}")
                raise e
        return cls._model

    @classmethod
    def get_feature_names(cls):
        if not cls._feature_names:
            cls.load_model()
        return cls._feature_names

    @classmethod
    def predict(cls, data_pool) -> list:
        model = cls.load_model()
        return model.predict(data_pool)


def get_model_service():
    ModelService.load_model()
    return ModelService