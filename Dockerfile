# Multi-stage build for production (optional - skipped for dev)
# We use separate frontend/backend services in docker-compose for development

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.4.1 --no-cache-dir

# Copy backend files
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies without virtual environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Copy backend application
COPY . .

# Build check - verify all imports resolve
RUN python -c "from app.main import app; print('Build check passed')"

# Create uploads directory
RUN mkdir -p ./uploads

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command (can be overridden by docker-compose)
CMD ["gunicorn", "app.main:socket_app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

