FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Set up working directory
WORKDIR /app

# Create an empty README.md file if it doesn't exist
RUN touch README.md

# Copy poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Copy source code
COPY src/ ./src/

# Install dependencies
RUN poetry install --only main --no-interaction --no-ansi

# Copy remaining application code
COPY . .

# Command to run the application
CMD ["uvicorn", "ml_classifier.main:app", "--host", "0.0.0.0", "--port", "8000"]
