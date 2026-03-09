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

### Docker Image Optimization Strategy & Analysis

**Date:** 2026-03-09  
**Lead Analysis:** Hicks (Lead/Architect)  
**Implementation:** Vasquez (DevOps)  
**Verification:** Bishop (Tester/QA)

#### Strategy Overview (from Hicks)

Hicks performed deep Docker image analysis and produced a comprehensive optimization strategy with 6 priority levels (P1-P6). Key findings:

**Root Cause Analysis:**
- Image size: ~1.5 GB
- Base: `python:3.11-slim` (~200MB)
- `opencv-python` wheel: 59MB compressed → ~180MB+ installed (bundles Qt5/GUI libraries)
- 6 apt packages installed, 4 of which are X11/GUI-only dependencies
- Build context: 332MB of `node_modules/` unnecessarily transferred
- No `.dockerignore` in place

**Prioritized Optimization Strategy:**

| Priority | Change | Impact | Risk | Complexity |
|----------|--------|--------|------|------------|
| **P1** | Switch `opencv-python` → `opencv-python-headless` | -50-80MB wheel savings, ~50-80MB more from removed Qt/GUI libs | LOW | 1-line change |
| **P2** | Remove X11/GUI apt packages (libgl1, libsm6, libxext6, libxrender-dev) | -50-150MB | LOW (with P1) | 1-line change |
| **P3** | Add `.dockerignore` | 0MB image, but much faster builds | NONE | new file |
| **P4** | Combine RUN layers (mkdir/chmod) | <1MB | NONE | minor edit |
| **P5** | Multi-stage build | ~5MB | LOW | not recommended (complexity overhead) |
| **P6** | Folder restructuring to src/ | 0MB | N/A | skip |

**Hicks Recommendation:** P1 + P2 + P3 together. Expected total reduction: ~100-250MB plus massively faster build context transfer.

#### Implementation Confirmation (from Vasquez)

Vasquez successfully implemented P1, P2, P3, and P4:
1. Changed `requirements.txt`: `opencv-python==4.8.1.78` → `opencv-python-headless==4.8.1.78`
2. Edited `Dockerfile` apt-get line: Kept only `libgl1`, `libglib2.0-0`, `libgomp1`
3. Created `.dockerignore` with appropriate exclusions
4. Merged RUN commands (mkdir+chmod) for layer optimization

**Note on libgl1 divergence:** Hicks initially recommended removing libgl1, but Vasquez correctly retained it. OpenCV headless variant still requires libgl1 for OpenGL operations. Bishop's verification confirmed this design choice works correctly.

#### Verification Results (from Bishop)

Bishop conducted full build verification with 6 test categories:
- ✅ Static Dockerfile Analysis: Apt packages verified as minimal and sufficient
- ✅ Code Review for GUI Calls: Scanned entire codebase (keyframe_extractor.py, web_app.py) — zero GUI functions found
- ✅ Docker Build Test: Build completed successfully, all 9 stages executed cleanly
- ✅ Import Verification: `cv2.4.8.1`, numpy, flask all import correctly
- ✅ Image Size: **794 MB confirmed** (47% reduction from ~1.5 GB)
- ✅ Flask App Startup: Application loads without errors

**Regression Status:** No regressions detected. All functionality intact after switching to opencv-python-headless.

#### Final Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Image Size | ~1.5 GB | 794 MB | -706 MB (-47%) |
| Apt Packages | 6 | 3 | -50% |
| Build Context | ~340MB+ | <1MB | Optimized (via .dockerignore) |
| OpenCV Variant | GUI | Headless | Optimal for headless server |

#### Deployment Recommendation

**STATUS: APPROVED & READY FOR DEPLOYMENT**
- All verification checks passed
- No regressions detected
- Significant size and build speed improvements achieved
- Branch: `docker-optimize`, Commit: c73533b

---

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
