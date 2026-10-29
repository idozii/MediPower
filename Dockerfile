FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Public research demo uses forced offline TF-IDF only. Avoid bundling
# Torch, FAISS and SentenceTransformers into this lightweight image.
COPY requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements-demo.txt

COPY app ./app
COPY logo.png ./logo.png

ENV FORCE_OFFLINE_RETRIEVER=1 \
    ALLOW_MODEL_DOWNLOAD=0 \
    ALLOW_EXTERNAL_GEOCODING=0 \
    MEDIPOWER_DEMO_PRESETS_ONLY=1

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log"]
