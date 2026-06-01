FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CUBY_CLOUD=1 \
    DEBUG=False

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libxml2 \
    libxml2-dev \
    libxslt1.1 \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-cloud.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-cloud.txt

COPY . .

RUN python scripts/init_db.py

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
