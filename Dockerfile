# Use Python 3.11 slim image for AMD64 architecture
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --disable-pip-version-check \
    -r requirements.txt \
    && pip cache purge

# Copy the application source code
COPY src/ ./src/
COPY download_models.py .

# Create necessary directories
RUN mkdir -p ./input ./output ./models

# Download and cache ML models during build time
# This ensures the container works offline
RUN python download_models.py

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set the default command to run the main application
CMD ["python", "src/main.py"]
