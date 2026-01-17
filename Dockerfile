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

# Expose port (frontend akan proxy ke backend internally)
EXPOSE 3000

# IMPORTANT: Run BOTH frontend & backend on SAME port (3000)
# Reflex akan auto-handle WebSocket routing ke backend
CMD ["sh", "-lc", "reflex run --env prod --frontend-port ${PORT:-3000} --backend-host 0.0.0.0 --backend-port ${PORT:-3000}"]