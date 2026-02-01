FROM python:3.12-slim-bookworm

WORKDIR /app

COPY pyproject.toml ./

# Устанавливаем зависимости (включая dev для тестов)
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Копируем код проекта, модель и тесты
COPY app ./app
COPY models ./models
COPY tests ./tests

# Явно указываем Python искать модули в текущей директории
ENV PYTHONPATH=/app

# Запускаем тесты при сборке. 
RUN pytest tests/

EXPOSE 8000

# Команда для запуска приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
