from catboost import CatBoostRegressor
from loguru import logger
import shap
from app.core.config import settings


class ModelService:
    """
    Сервис-обертка над ML-моделью CatBoost.
    Отвечает за загрузку файла, выполнение предсказания и расчет SHAP values.
    """

    _model = None
    _explainer = None
    _feature_names = []

    @classmethod
    def load_model(self):
        """
        Загружает модель в память и инициализирует SHAP explainer.
        """
        if self._model is None:
            logger.info(f"Загрузка модели из: {settings.MODEL_PATH}")
            if not settings.MODEL_PATH.exists():
                logger.error(f"Файл модели не найден: {settings.MODEL_PATH}")
                raise FileNotFoundError(f"Model not found at {settings.MODEL_PATH}")

            try:
                # 1. Загрузка CatBoost
                self._model = CatBoostRegressor()
                self._model.load_model(str(settings.MODEL_PATH))
                self._feature_names = self._model.feature_names_
                logger.info("Модель успешно загружена.")

                # 2. Инициализация SHAP Explainer
                logger.info("Инициализация SHAP Explainer...")
                self._explainer = shap.TreeExplainer(self._model)
                logger.info("SHAP Explainer готов.")

                logger.debug(f"Признаки модели: {self._feature_names}")
            except Exception as e:
                logger.critical(f"Не удалось загрузить модель или explainer: {e}")
                raise e
        return self._model

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

    @classmethod
    def explain(cls, vectors) -> list:
        """
        Возвращает матрицу SHAP values для переданных векторов.
        :param vectors: Список векторов признаков (List[List[float]]).
        :return: Массив (или список массивов) SHAP values.
        """
        if cls._explainer is None:
            cls.load_model()

        shap_values = cls._explainer.shap_values(vectors)
        return shap_values
