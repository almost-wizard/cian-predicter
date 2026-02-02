import sys
from fastapi import FastAPI
from loguru import logger
from app.api.endpoints import router as api_router
from app.services.model_service import ModelService
from app.core.config import settings

# Настройка глобального логгера
logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ML сервис для предсказания стоимости аренды квартир в Санкт-Петербурге",
    version=settings.VERSION,
)

# Подключение маршрутов API
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """
    Событие запуска приложения.
    """
    logger.info("Запуск приложения...")
    try:
        ModelService.load_model()
    except Exception as e:
        logger.critical(f"Сбой запуска: Не удалось загрузить модель. Ошибка: {e}")
        sys.exit(1)


@app.get("/health")
def health_check():
    """
    Простой эндпоинт для проверки работоспособности сервиса.
    """
    return {"status": "ok", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn

    # Запуск сервера разработки
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
