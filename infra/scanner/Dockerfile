FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    docker==7.1.0 \
    fastapi==0.116.1 \
    requests==2.32.5 \
    uvicorn==0.35.0

COPY app.py .

CMD ["python", "app.py"]
