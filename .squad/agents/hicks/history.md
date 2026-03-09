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

### 2024 — Docker Image Analysis (Initial)

- **opencv-python wheel**: 59MB compressed → ~180MB+ installed. Bundles Qt5/GUI libs the app never uses.
- **opencv-python-headless wheel**: 47MB compressed → ~130MB installed. Same API surface minus GUI.
- **cv2 usage in keyframe_extractor.py**: All headless-safe — `VideoCapture`, `cvtColor`, `calcHist`, `normalize`, `compareHist`, `imwrite`. No `imshow`, `waitKey`, or any display calls.
- **web_app.py**: Flask server, imports keyframe_extractor + reka_service + db_service. No direct cv2 usage.
- **Unnecessary apt packages for headless**: `libgl1` (Mesa/GL), `libsm6` (X11 session mgmt), `libxext6` (X11 extensions), `libxrender-dev` (X rendering + dev headers). All X11/display deps not needed with headless OpenCV.
- **Required apt packages**: `libglib2.0-0` (GLib, needed by OpenCV internals), `libgomp1` (OpenMP, needed for parallel processing).
- **No .dockerignore**: Build context includes `node_modules/` (332MB!), `.git/`, `assets/`, `.squad/`, `.copilot/`, `.github/`. Doesn't inflate image (COPY is per-file) but massively slows builds.
- **Multi-stage build**: Low value here — no compilation happening, already using `--no-cache-dir`. Would add complexity for ~5MB.
- **Folder restructuring**: Zero impact on image size. COPY commands are explicit.

### 2026-03-09 — Deep Docker Analysis & Optimization Strategy (Session Completion)

**Work Completed:**
- Conducted comprehensive Docker layer analysis across all 12 build stages
- Identified root causes: OpenCV GUI libs (Qt5, X11 stack), 4 unnecessary apt packages, unoptimized .dockerignore
- Produced P1-P6 prioritized optimization strategy with impact estimates and risk assessments
- Recommended P1+P2+P3 approach for 100-250MB reduction with low risk

**Strategic Recommendation:**
P1 (headless OpenCV) + P2 (remove X11 libs) + P3 (.dockerignore) together. Expected total reduction: ~100-250MB plus massively faster build context transfer.

**Key Insight:** For headless server applications using OpenCV, switching to opencv-python-headless should always be the first optimization — saves far more than multi-stage build complexity.

**Validation Note:** While recommending removal of libgl1 initially, Vasquez's final implementation correctly retained it. OpenCV headless variant still requires libgl1 for OpenGL operations. Bishop's build verification confirmed this design works correctly.

