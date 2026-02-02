import numpy as np
from typing import List, Optional
from loguru import logger
from app.models.api_schemas import RawApartmentInput, PredictionResponse, PredictionResponseItem
from app.services.model_service import ModelService
from app.services.transformer_service import TransformerService
from app.core.config import settings


class PredictionService:
    """
    Сервис бизнес-логики для предсказания стоимости аренды.
    Оркестрирует процесс: валидация -> трансформация -> ML предсказание -> пост-процессинг.
    """

    def __init__(self, model_service: ModelService, transformer_service: TransformerService):
        self._model_service = model_service
        self._transformer_service = transformer_service

    def make_prediction(self, items: List[RawApartmentInput]) -> PredictionResponse:
        """
        Основной метод выполнения прогноза.

        :param items: Список объектов с сырыми данными о квартирах.
        :return: Ответ API с прогнозами и диапазонами цен.
        :raises RuntimeError: В случае ошибки при выполнении ML модели.
        """
        logger.info(f"Обработка пакета из {len(items)} объектов")

        # 1. Трансформация данных (Raw -> Model Vector)
        vectors = self._transform_data(items)
        if not vectors:
            return PredictionResponse(predictions=[])

        # 2. ML Предсказание (Вызов модели)
        try:
            log_predictions = self._model_service.predict(vectors)
        except Exception as e:
            logger.error(f"Ошибка ML модели: {e}")
            raise RuntimeError(f"ML Model error: {e}")

        # 3. Пост-процессинг и применение бизнес-логики
        results = self._post_process_predictions(items, log_predictions)

        return PredictionResponse(predictions=results)

    def _transform_data(self, items: List[RawApartmentInput]) -> List[list]:
        """
        Преобразует входные данные в формат, понятный модели CatBoost.
        """
        vectors = []
        for item in items:
            try:
                model_features = self._transformer_service.transform(item)
                vectors.append(model_features.to_list())
            except Exception as e:
                logger.error(f"Ошибка трансформации для объекта '{item.title}': {e}")
                raise ValueError(f"Data transformation error: {e}")
        return vectors

    def _post_process_predictions(
        self, items: List[RawApartmentInput], log_predictions
    ) -> List[PredictionResponseItem]:
        """
        Преобразует логарифмические предсказания обратно в рубли,
        считает диапазоны и оценивает выгодность предложения.
        """
        response_items = []

        # Если модель вернула одно скаляр, превращаем в список
        if np.isscalar(log_predictions):
            log_predictions = [log_predictions]

        for item, log_price in zip(items, log_predictions):
            # 1. Обратное преобразование (exp) и защита от переполнения
            clean_log = min(log_price, 20)
            price = int(np.expm1(clean_log))

            # 2. Расчет диапазона цен
            margin = settings.PREDICTION_MARGIN_PERCENT
            low = int(price * (1 - margin))
            high = int(price * (1 + margin))

            # 3. Расчет процента недооцененности
            undervalued_pct = self._calculate_undervaluation(price, item.price_per_month)

            response_items.append(
                PredictionResponseItem(
                    predicted_price=price,
                    price_range_low=low,
                    price_range_high=high,
                    undervalued_percent=undervalued_pct,
                )
            )

        return response_items

    def _calculate_undervaluation(self, predicted: int, real: Optional[int]) -> Optional[float]:
        """
        Считает, насколько реальная цена ниже предсказанной (в процентах).
        Положительный % = выгодно (реальная цена ниже рыночной).
        """
        if not real or real <= 0:
            return None

        diff = predicted - real
        return round((diff / predicted) * 100, 1)
