from fastapi import Depends
from app.services.model_service import ModelService
from app.services.prediction_service import PredictionService
from app.services.transformer_service import TransformerService


def get_model_service() -> ModelService:
    """
    Провайдер сервиса модели.
    Гарантирует загрузку модели.
    """
    ModelService.load_model()
    return ModelService


def get_transformer_service() -> TransformerService:
    """
    Провайдер сервиса трансформации данных.
    """
    return TransformerService()


def get_prediction_service(
    model_service: ModelService = Depends(get_model_service),
    transformer_service: TransformerService = Depends(get_transformer_service),
) -> PredictionService:
    """
    Провайдер сервиса предсказаний.
    Внедряет зависимости ModelService и TransformerService.
    """
    return PredictionService(model_service, transformer_service)
