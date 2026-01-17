FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Initialize and build the Reflex app
RUN reflex init
RUN reflex export --frontend-only --no-zip

# Expose the ports Reflex uses
EXPOSE 8000 3000

CMD ["reflex", "run", "--env", "prod"]