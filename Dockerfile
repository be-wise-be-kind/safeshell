# syntax=docker/dockerfile:1
# safeshell Docker image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy project files
COPY pyproject.toml poetry.lock* ./
COPY README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install all dependencies (including dev for linting)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Make files readable by all users (for --user flag support)
RUN chmod -R a+rX /app

# Default command
CMD ["safeshell", "--help"]
