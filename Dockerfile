FROM python:3.10-slim

# Install system dependencies (FFmpeg for video, fonts for subtitles)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install (NO PyTorch needed - faster-whisper uses CTranslate2)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure storage directories exist
RUN mkdir -p downloads output

# Low-memory Whisper config for Railway (~200MB total RAM)
ENV WHISPER_MODEL=tiny
ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
