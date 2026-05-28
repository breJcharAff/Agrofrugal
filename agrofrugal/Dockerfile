# Cible: image < 150 MB (edge 4G, grange, <5W).
# Build: docker build -f agrofrugal/Dockerfile -t agrofrugal:edge .

FROM python:3.11-slim AS builder

WORKDIR /build
ENV PIP_NO_CACHE_DIR=1

COPY agrofrugal/requirements.txt .
RUN pip install --prefix=/install --no-deps -r requirements.txt \
    && find /install -name "*.pyc" -delete \
    && find /install -name "__pycache__" -type d -exec rm -rf {} + \
    && find /install -name "tests" -type d -exec rm -rf {} +


FROM python:3.11-slim AS runtime

RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=app:app agrofrugal/app.py ./
COPY --chown=app:app agrofrugal/data/ ./data/
COPY --chown=app:app agrofrugal/models/ ./models/
COPY --chown=app:app shared/codecarbon_middleware.py ./shared/codecarbon_middleware.py

ENV PYTHONUNBUFFERED=1 \
    REDIS_URL=redis://redis:6379/0 \
    FAQ_PATH=/app/data/faq_agriculture_300.json \
    MODEL_PATH=/app/models/distilbert-int8 \
    PYTHONPATH=/app

USER app
EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
