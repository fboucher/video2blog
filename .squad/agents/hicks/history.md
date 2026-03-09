# Hicks — Project History

## Project Context

- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV (opencv-python), numpy, requests, python-dotenv
- **What it does:** Extracts keyframes from videos and generates blog posts from them
- **Requested by:** fboucher
- **Primary mission:** Reduce Docker image size (currently ~1.5 GB)

## Key Files

- `Dockerfile` — single-stage build, python:3.11-slim base, apt installs OpenCV system deps
- `requirements.txt` — 6 dependencies: opencv-python, numpy, flask, werkzeug, python-dotenv, requests
- `web_app.py`, `keyframe_extractor.py`, `reka_service.py`, `db_service.py` — app source

## Known Constraints

- fboucher prefers not to change the folder structure unless it meaningfully helps
- Folder restructuring (e.g., moving code to `src/`) is optional and only if it genuinely reduces image size

## Learnings

