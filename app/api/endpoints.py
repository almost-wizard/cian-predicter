from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.models.api_schemas import RawApartmentInput, PredictionResponse
from app.api.dependencies import get_prediction_service
from app.services.prediction_service import PredictionService

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_price(items: List[RawApartmentInput], service: PredictionService = Depends(get_prediction_service)):
    """
    API Эндпоинт для предсказания цены аренды.

    Принимает список квартир, делегирует обработку в PredictionService.

    - **items**: Список объектов с данными о квартирах.
    - **return**: Список прогнозов с диапазонами цен.
    """
    try:
        return service.make_prediction(items)
    except ValueError as e:
        # Ошибки валидации данных или бизнес-логики
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Внутренние ошибки выполнения модели
        raise HTTPException(status_code=500, detail=str(e))
