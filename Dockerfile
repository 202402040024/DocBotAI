FROM python:3.11-slim

WORKDIR /app

# System deps for faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY api/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create upload and vector store dirs
RUN mkdir -p uploads/pdf uploads/docx uploads/csv uploads/xml uploads/vector_stores

# Expose single port (Streamlit frontend)
EXPOSE 8000

# Start script runs FastAPI on :8001 + Streamlit on :$PORT
CMD ["sh", "start.sh"]
