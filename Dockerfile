FROM python:3.10-slim

# Install system dependencies (FFmpeg is required for video processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install lightweight CPU-only PyTorch first (saves 80% RAM and 2GB disk!)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure storage directories exist
RUN mkdir -p downloads output

# Default to tiny Whisper model for Railway low memory footprint (<250MB RAM)
ENV WHISPER_MODEL=tiny
ENV PORT=5000
EXPOSE 5000

# Start application
CMD ["python", "app.py"]
