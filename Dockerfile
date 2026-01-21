FROM python:3.11-slim

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY keyframe_extractor.py .
COPY web_app.py .
COPY reka_service.py .
COPY db_service.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Create directories for uploads, output, and database
RUN mkdir -p /app/uploads /app/output /app/data

# Make scripts executable
RUN chmod +x keyframe_extractor.py web_app.py

# Expose port for Flask
EXPOSE 5123

# Set default command to run web app
CMD ["python", "web_app.py"]