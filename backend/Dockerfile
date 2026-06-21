FROM python:3.11-slim

WORKDIR /app

# faiss-cpu needs these
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create upload dirs
RUN mkdir -p uploads/pdf uploads/docx uploads/csv uploads/xml uploads/vector_stores

EXPOSE 10000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
