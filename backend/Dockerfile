# backend/Dockerfile
# Multi-stage build for Python Flask backend with OCR capabilities

# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Update package lists and install system dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    postgresql-client \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    gcc \
    g++ \
    build-essential \
    curl \
    wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
# Stage 2: Python dependencies builder
FROM base as builder

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Final runtime image
FROM base as runtime

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads /app/logs /app/temp && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser ./src/ ./src/
COPY --chown=appuser:appuser ./app.py .
COPY --chown=appuser:appuser ./requirements.txt .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Create directories for file storage
RUN mkdir -p /app/uploads/statements /app/uploads/processed /app/temp && \
    chown -R appuser:appuser /app/uploads /app/temp

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/health')" || exit 1

# Expose port
EXPOSE 5001

# Run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5001"]
