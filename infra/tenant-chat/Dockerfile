FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    aiohttp==3.12.15 \
    docker==7.1.0 \
    fastapi==0.116.1 \
    uvicorn==0.35.0 \
    websockets==15.0.1

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
