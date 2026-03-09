# Bishop — Project History

## Project Context

- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV (opencv-python), numpy, requests, python-dotenv
- **What it does:** Extracts keyframes from videos and generates blog posts from them
- **Requested by:** fboucher
- **Primary mission:** Reduce Docker image size (currently ~1.5 GB)

## Key Files

- `Dockerfile` — what Vasquez will optimize; Bishop validates the result
- `web_app.py` — Flask app entry point; must start correctly in the container
- `keyframe_extractor.py` — uses OpenCV; must remain functional after switching to headless variant

## Known Constraints

- App runs on port 5123
- Must be able to import cv2, numpy, flask without errors in the final image

## Learnings

