FROM python:3.11-slim

ARG APP_VERSION=0.5.1-preview
ENV APP_VERSION=${APP_VERSION}

# Install system dependencies for OpenCV headless (minimal set)
# libgl1: OpenGL library needed for some OpenCV operations
# libglib2.0-0: GLib library (general utility library)
# libgomp1: OpenMP runtime (parallel processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY keyframe_extractor.py web_app.py reka_service.py db_service.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create directories for uploads, output, and database, and make scripts executable in one layer
RUN mkdir -p /app/uploads /app/output /app/data && \
    chmod +x keyframe_extractor.py web_app.py

# Expose port for Flask
EXPOSE 5123

# Set default command to run web app
CMD ["python", "web_app.py"]