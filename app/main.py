import sys
from fastapi import FastAPI
from loguru import logger
from app.api.endpoints import router as api_router
from app.api.dependencies import ModelService
from app.core.config import settings

# Настройка логгера
logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL)

app = FastAPI(
    title="Cian Price Predicter",
    description="ML service for predicting rental prices in St. Petersburg",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    try:
        ModelService.load_model()
    except Exception as e:
        logger.critical(f"Startup failed: Model could not be loaded. Error: {e}")
        sys.exit(1)


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
