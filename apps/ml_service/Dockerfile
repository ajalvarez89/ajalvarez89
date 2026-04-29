FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
# Phase 0 installs base deps only. ML extras (torch, neuralforecast, transformers) install in Phase 3
# via `pip install -e '.[ml]'` inside the running container, to keep the Phase 0 image small.
RUN pip install --upgrade pip && pip install -e .

COPY src ./src
COPY tests ./tests

EXPOSE 8002

CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
