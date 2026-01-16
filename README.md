# Video2Blog

A Python application that extracts keyframes from videos and generates blog posts using AI vision models.

## Quick Start

### Build and Run

```bash
# Build the container
podman build -t video2blog .
# or with Docker:
docker build -t video2blog .

# Run the web application
podman run -d --name video2blog -p 5123:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  video2blog

# Or with docker-compose:
docker-compose up -d
```

### Access the Application

Open your browser and navigate to: **http://localhost:5123**

### Stop the Container

```bash
# Podman:
podman stop video2blog
podman rm video2blog

# Docker:
docker stop video2blog
docker rm video2blog
```

## Environment Variables

Create a `.env` file with:
```
REKA_API_KEY=your_reka_api_key_here
```
