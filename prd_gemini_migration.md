# PRD: Migrate from Reka to Gemini

## Overview

Full replacement of the Reka Vision API with Google Gemini. Local files become the sole source of truth — the cloud video library concept is removed. Gemini handles video understanding, Q&A, blog generation, and smart timestamp suggestions for frame extraction.

## Goals

- Replace all Reka API calls with Gemini equivalents
- Simplify the video model: local files only, no cloud library
- Support YouTube and direct URLs via Gemini's native URL handling (no download required for Q&A)
- Cache Gemini file URIs in the DB to avoid re-uploading within the 48hr validity window
- Use Gemini to suggest meaningful timestamps for image extraction (replaces blind scene detection)
- Add `yt-dlp` to support frame extraction from URL videos (download → extract → keep locally)
- Make the Gemini model configurable via env var, defaulting to `gemini-2.0-flash`

## Out of Scope

- Multi-provider support (no Reka fallback)
- Migrating existing Reka videos (fresh start)
- Features described in #12 (separate track)

---

## Architecture

### Video model — before vs. after

| Before | After |
|---|---|
| Local file + Reka cloud copy (synced) | Local file only |
| Video queryable only when Reka `indexing_status = indexed` | Video queryable once Gemini file upload is `ACTIVE` |
| Reka file ID lives forever | Gemini file URI valid 48hrs — re-upload on expiry |
| Videos can exist in Reka without a local copy | All videos must be local |
| Frame images selected by blind scene detection | Gemini suggests meaningful timestamps during blog generation |

### Gemini file URI caching

When a Q&A or blog generation request comes in:
1. Check DB: does a `gemini_file_uri` exist and is `gemini_uploaded_at` within 48hrs?
2. Yes → reuse cached URI
3. No → upload to Gemini Files API, store `gemini_file_uri` + `gemini_uploaded_at`, then proceed

### URL video flow

- **Q&A / blog generation**: pass URL directly to Gemini — no download needed
- **Frame extraction**: yt-dlp downloads the video into the uploads folder first, then existing OpenCV extractor runs normally. The local copy is kept so the video appears in the library going forward. User can delete it via the delete action when done.

### Frame extraction upgrade

Blog generation returns both a draft and a list of suggested timestamps. Those timestamps feed directly into the existing `extract_frames_at_timestamps()` function — smarter image selection with no extra infrastructure.

---

## Work Breakdown

### 1. `gemini_service.py` (new, replaces `reka_service.py`)
- [ ] `upload_video(local_path)` → Files API upload, returns `file_uri`
- [ ] `upload_from_url(url)` → returns URL reference (Gemini handles it natively)
- [ ] `generate_blog(file_ref, messages)` → `generateContent` with video + conversation history, returns blog draft + suggested timestamps
- [ ] `delete_file(file_uri)` → Files API cleanup
- [ ] `is_configured()` → checks `GEMINI_API_KEY`
- [ ] `get_model()` → reads `GEMINI_MODEL` env var, defaults to `gemini-2.0-flash`

### 2. `db_service.py` updates
- [ ] Drop Reka columns: `reka_video_id`, `reka_url`, `reka_indexing_status`
- [ ] Add: `gemini_file_uri TEXT`, `gemini_uploaded_at TIMESTAMP`
- [ ] Add `update_gemini_upload(filename, uri, timestamp)`
- [ ] Add `get_gemini_file_info(filename)` → returns URI + upload time
- [ ] Remove all `reka_*` functions

### 3. `web_app.py` updates
- [ ] Replace `reka_service` import with `gemini_service`
- [ ] Remove all `/reka/*` routes
- [ ] Add `/gemini/status`, `/gemini/ask`, `/gemini/delete/<file_uri>`
- [ ] `/videos/list` — local files only, include Gemini cache status (fresh / expired / not uploaded)
- [ ] `/upload` — after saving locally, auto-upload to Gemini, store URI + timestamp
- [ ] `/upload-from-url` — pass URL to Gemini directly; no local file created until user triggers frame extraction
- [ ] `/gemini/ask` — resolve file ref via cache logic before calling Gemini
- [ ] Remove `/videos/download` (was Reka CDN download)
- [ ] Remove `/reka/refresh-status`
- [ ] `sanitize_filename()` — remove `reka_video_id` dependency, use a local UUID

### 4. `yt-dlp` integration
- [ ] Add `yt-dlp` to `requirements.txt`
- [ ] Add `download_video_from_url(url, output_path)` utility (wraps yt-dlp)
- [ ] Wire into frame extraction flow: URL video → yt-dlp download → save to uploads → extract frames
- [ ] After download, create DB record so video appears in the local library
- [ ] Confirm delete button is visible and functional for all local videos (including yt-dlp downloads)

### 5. Frame extraction upgrade
- [ ] Update blog generation prompt to ask Gemini for suggested image timestamps alongside the draft
- [ ] Pass returned timestamps to existing `extract_frames_at_timestamps()` instead of scene detection
- [ ] Keep scene detection as a fallback if Gemini returns no timestamps

### 6. Environment variables
- [ ] Remove `REKA_API_KEY`, `REKA_BASE_URL`
- [ ] Add `GEMINI_API_KEY`, `GEMINI_MODEL` (default: `gemini-2.0-flash`)
- [ ] Update `.env.example`

### 7. UI updates
- [ ] Remove indexing status indicators and sync badges
- [ ] Video list: show Gemini cache status — "Ready (expires in Xh)" / "Needs upload" / "Expired"
- [ ] URL upload: clarify it is Q&A-only until user triggers frame extraction (which downloads the video)
- [ ] Ensure delete action is clearly visible for all local videos

### 8. Dockerfile + cleanup
- [ ] Replace `reka_service.py` with `gemini_service.py` in `COPY` instruction
- [ ] Delete `reka_service.py`
- [ ] Update `README.md`

---

## Environment Variables

| Remove | Add |
|---|---|
| `REKA_API_KEY` | `GEMINI_API_KEY` |
| `REKA_BASE_URL` | `GEMINI_MODEL` (default: `gemini-2.0-flash`) |
