FROM python:3.13-slim

WORKDIR /app

# System build deps for pyarrow and lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Ensure storage exists
RUN mkdir -p storage

# Koyeb expects port 8080
EXPOSE 8080

# Single worker + 4 threads = better on 0.1 vCPU free tier
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "run:app"]