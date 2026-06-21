FROM python:3.11-slim

WORKDIR /app

# Install only what's needed for the packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Pre-create upload directories
RUN mkdir -p uploads/pdf uploads/docx uploads/csv uploads/xml uploads/vector_stores

# Expose port
EXPOSE 10000

# Start — use PORT env var from Render (default 10000)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
