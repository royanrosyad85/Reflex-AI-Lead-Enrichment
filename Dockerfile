FROM python:3.11-slim

WORKDIR /app

# Install system deps + Node 20.x
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    unzip \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build once at image build time
RUN reflex init
RUN reflex export --no-zip

# DigitalOcean will probe the "Internal Port" you set (recommend 8000) or $PORT if you use it.
EXPOSE 8000

# IMPORTANT: bind to 0.0.0.0 inside container
CMD ["sh", "-lc", "reflex run --env prod --backend-host 0.0.0.0 --backend-port ${PORT:-8000}"]