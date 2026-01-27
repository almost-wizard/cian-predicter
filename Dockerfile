# Use official Playwright image (includes Python and Browsers)
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Copy dependency definition first (caching layer)
COPY pyproject.toml README.md ./

# Install dependencies
# We use --no-deps for the project itself to avoid reinstalling deps in the next step, 
# but here we just want libraries from pyproject.toml
RUN pip install --upgrade pip && \
    pip install -e .

# Copy the rest of the code
COPY app/ ./app/

# Create directories for data and logs
RUN mkdir -p data logs

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=True

# Run command as a module (fixes import issues)
CMD ["python", "-m", "app.main"]
