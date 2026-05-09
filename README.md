
# Video 2 Blog

[![Build and Push Docker Image](https://github.com/fboucher/video2blog/actions/workflows/docker-build.yml/badge.svg?branch=main)](https://github.com/fboucher/video2blog/actions/workflows/docker-build.yml) ![GitHub License](https://img.shields.io/github/license/fboucher/video2blog) [![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-blue)](https://ai.google.dev/)

A simple web application running in a container that helps generate a blog post draft from a video. It uses AI to analyze the video content and generate a blog post draft. You can then chat with AI to refine the draft and finally extract keyframes from the video to illustrate the blog post.

## Quick Start

### Build and Run

```bash
# Run the web application
docker-d --name video2blog -p 5123:5000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  fboucher/video2blog

# Or with docker-compose:
docker-compose up -d
```

### Access the Application

Open your browser and navigate to: **http://localhost:5123**

## Environment Variables

Create a `.env` file with:
```
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

## How It Works

### Step 1: Select a video

You can upload a video file or provide a YouTube URL.

![Upload video](assets/step1-select-video.png)

### Step 2: Chat with AI

Chat with the AI to generate a blog post based on the video content. You can ask questions, request summaries, and more.

![step 2 chat](assets/step2-chat.png)

### Step 3: Extract keyframe images

The application extracts keyframes from the video and generates images with captions.

![step 3](assets/step3-extract.png)

## Resources

This project uses the [Google Gemini API](https://ai.google.dev/) for video understanding and blog generation. Get an API key at [Google AI Studio](https://aistudio.google.com/).