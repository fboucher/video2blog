# Squad Decisions

## Active Decisions

### Docker Image Optimization (2026-03-09)

**Owner:** Vasquez (DevOps)  
**Requested by:** fboucher  
**Status:** APPROVED & IMPLEMENTED

#### Summary

Optimized video2blog Docker image from ~1.5 GB to **794 MB** (47% reduction, ~700 MB savings).

#### Changes Implemented

1. **opencv-python → opencv-python-headless** (requirements.txt)
   - Rationale: App is headless Flask server; cv2 only used for VideoCapture, frame reading, property queries
   - Impact: Removes Qt, X11 GUI libraries (~400-600 MB savings)

2. **Removed Display Libraries** (Dockerfile)
   - Removed: `libsm6`, `libxext6`, `libxrender-dev`
   - Retained: `libgl1`, `libglib2.0-0`, `libgomp1` (essential for OpenCV)
   - Impact: ~100-150 MB savings

3. **.dockerignore** (new file)
   - Excludes development artifacts (`.git/`, `.squad/`, `node_modules/`, `__pycache__/`, `*.pyc`, assets, docs)
   - Prevents unnecessary context transfer, speeds builds

4. **Dockerfile Layer Optimizations**
   - Added `--no-install-recommends` to apt-get
   - Combined RUN operations (mkdir/chmod)
   - Enhanced cleanup (apt cache, /tmp/*, /var/tmp/*)

#### Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Image Size | ~1.5 GB | 794 MB | -706 MB (-47%) |
| Apt Packages | 6 | 3 | -50% |
| OpenCV | GUI variant | Headless | Optimal for server |

#### Verification

- Docker build successful
- Image size verified: 794 MB
- Application functionality confirmed (headless OpenCV intact)

#### Recommendation

Commit and deploy. Improvements:
- Faster Docker pulls
- Lower storage requirements
- Improved container startup time
- Better CI/CD pipeline efficiency

---

### User Directive: Folder Restructuring (2026-03-09)

**Source:** fboucher (via Copilot)  
**Scope:** Optional refactoring  

Only restructure code directories (e.g., moving to `src/`) if it genuinely and meaningfully reduces Docker image size. Prefer not to change folder structure otherwise.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
