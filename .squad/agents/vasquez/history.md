# Vasquez — Project History

## Project Context

- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV (opencv-python), numpy, requests, python-dotenv
- **What it does:** Extracts keyframes from videos and generates blog posts from them
- **Requested by:** fboucher
- **Primary mission:** Reduce Docker image size (currently ~1.5 GB)

## Key Files

- `Dockerfile` — single-stage build, python:3.11-slim base
- `requirements.txt` — opencv-python==4.8.1.78, numpy==1.24.3, flask==3.0.0, werkzeug==3.0.1, python-dotenv==1.0.0, requests==2.31.0
- `docker-compose.yml` — service definition

## Known Constraints

- App runs headless (web server) — GUI OpenCV libs not needed
- Folder restructuring is optional (fboucher preference)

## Learnings

### 2024 - Dockerfile Optimization (Image Size Reduction: ~1.5GB → 794MB)

**Changes Made:**

1. **Switched to opencv-python-headless** (requirements.txt)
   - Replaced `opencv-python==4.8.1.78` with `opencv-python-headless==4.8.1.78`
   - Rationale: App is a headless Flask web server. No GUI/display functionality used. The code analysis confirmed cv2 is only used for VideoCapture, frame reading, and property queries.
   - Impact: Removes Qt, X11 GUI libraries, and display dependencies (~400-600 MB savings)

2. **Removed display-related apt packages** (Dockerfile)
   - Removed: `libsm6`, `libxext6`, `libxrender-dev` (X11/display libraries)
   - Kept: `libgl1` (OpenGL for some OpenCV ops), `libglib2.0-0` (GLib utilities), `libgomp1` (OpenMP for parallel processing)
   - Rationale: With headless OpenCV, X11 display libraries are no longer needed
   - Impact: ~100-150 MB savings

3. **Created .dockerignore**
   - Excluded: `.git/`, `.squad/`, `node_modules/`, `__pycache__/`, `*.pyc`, `assets/`, `README.md`, `LICENSE`, Docker files, etc.
   - Rationale: Prevents copying dev artifacts and documentation into image
   - Impact: Faster builds, cleaner image

4. **Dockerfile layer optimizations**
   - Combined RUN commands where logical (mkdir + chmod in one layer)
   - Used `--no-install-recommends` for apt packages
   - Added aggressive cleanup: `apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*`
   - Rationale: Reduce layer count and ensure no package manager caches remain

**Result:**
- Original size: ~1.5 GB
- Optimized size: 794 MB
- **Reduction: ~700 MB (47% smaller)**

**Key Insight:** The single biggest win was switching to opencv-python-headless. For server-side/headless applications using OpenCV, this should always be the first optimization. The package savings from removing GUI dependencies far outweigh any multi-stage build complexity for Python apps.

