FROM python:3.10-slim

# Install system dependencies (FFmpeg is required for video processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure storage directories exist
RUN mkdir -p downloads output

# Expose default port
ENV PORT=5000
EXPOSE 5000

# Start application
CMD ["python", "app.py"]
