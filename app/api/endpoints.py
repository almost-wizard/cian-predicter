import numpy as np
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from app.models.api_schemas import RawApartmentInput, PredictionResponse, PredictionResponseItem
from app.api.dependencies import ModelService, get_model_service
from app.core.transformer import transformer
from app.core.config import settings

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_price(items: List[RawApartmentInput], model_service: ModelService = Depends(get_model_service)):
    logger.info(f"Received prediction request for {len(items)} items")

    vectors = []

    # 1. Transform raw -> ModelFeatures -> list
    for item in items:
        try:
            model_features = transformer.transform(item)
            vectors.append(model_features.to_list())
        except Exception as e:
            logger.error(f"Failed to transform item: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid input data: {e}")

    # 2. Predict (Batch)
    if not vectors:
        return PredictionResponse(predictions=[])

    try:
        log_predictions = model_service.predict(vectors)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

    # 3. Post-process
    response_items = []
    if np.isscalar(log_predictions):
        log_predictions = [log_predictions]

    for log_price in log_predictions:
        # Safety limits
        clean_log = min(log_price, 20)
        price = int(np.expm1(clean_log))

        # Range calculation using config
        margin = settings.PREDICTION_MARGIN_PERCENT
        low = int(price * (1 - margin))
        high = int(price * (1 + margin))

        response_items.append(PredictionResponseItem(price=price, price_range_low=low, price_range_high=high))

    logger.info(f"Successfully predicted {len(response_items)} prices")
    return PredictionResponse(predictions=response_items)
