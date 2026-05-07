# Ripley — History

## Project Context
- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV, numpy, Google Gemini API, SQLite
- **User:** fboucher
- **Mission:** Migrate from Reka to Gemini API (issues #22–#28)
- **Base branch:** dev
- **Feature branches:** squad/22 through squad/28 (branched from dev)

## Architecture Overview

### Key Files & Ownership
- **`web_app.py`** — Main Flask application (routes, request handling)
- **`db_service.py`** — SQLite database layer (schema, queries)
- **`gemini_service.py`** — Google Gemini API wrapper (created in #22)
- **`reka_service.py`** — Legacy Reka service (TO BE REPLACED in #28)
- **`keyframe_extractor.py`** — Video frame extraction utilities
- **`requirements.txt`** — Python dependencies
- **`Dockerfile`** — Container config (Vasquez owns)
- **`templates/`** — Jinja2 templates (Hudson owns)
- **`static/`** — CSS, JavaScript (Hudson owns)

### Issue Map & Scope

| Issue | Title | Ripley Scope |
|-------|-------|--------------|
| #22 | Gemini service foundation | ✅ Created `gemini_service.py`, updated DB schema for file caching |
| #23 | Local video upload + file caching | ✅ Wired `/upload` to Gemini, rebuilt `/videos/list`, added `/videos/upload-to-gemini` |
| #24 | Q&A on local videos | Implement Q&A route, conversation history |
| #25 | Blog generation with timestamps | Gemini-assisted timestamp suggestion, blog formatting |
| #26 | URL video Q&A without download | URL metadata extraction, Gemini Q&A on frames |
| #27 | yt-dlp frame extraction | Integrate yt-dlp for URL video frames |
| #28 | Reka removal + cleanup | Remove reka_service.py, update requirements.txt, Dockerfile |

## Gemini API Integration Strategy
- Use Google Generative AI Python client
- File caching for uploaded videos (avoid re-upload costs)
- Streaming responses where applicable
- Error handling for rate limits, invalid inputs
- Token usage monitoring in logs

## Database Schema (v2 — implemented in #22)
- **`video_sync` table:** `id`, `local_filename` (UNIQUE), `video_name`, `sync_status`, `gemini_file_uri`, `gemini_uploaded_at`, `created_at`, `updated_at`
- Key functions: `add_sync(local_filename, video_name)`, `update_gemini_upload(filename, uri, iso_timestamp)`, `get_gemini_file_info(filename)`

## Known Patterns
- Flask routes use `request.get_json()` for input validation
- `db_service.py` functions are atomic (rollback on error)
- Video processing catches exceptions and logs clearly
- All file operations sanitize filenames (`sanitize_filename()` in #28)
- Always gate Gemini API calls on `gemini_service.is_configured()`
- `upload_video()` is blocking (polls up to 300 s) — future issues should consider background task + polling

## Issue #23 — API Contracts

### `GET /videos/list` Response Shape
```json
{
  "videos": [
    {
      "filename": "demo.mp4",
      "filepath": "/app/uploads/demo.mp4",
      "size": 104857600,
      "modified": 1746633000.0,
      "duration": 120.5,
      "fps": 30.0,
      "gemini_uri": "files/abc123",
      "gemini_cache_status": "fresh",
      "expires_in_hours": 41
    },
    {
      "filename": "old.mp4",
      "filepath": "/app/uploads/old.mp4",
      "size": 52428800,
      "modified": 1746546600.0,
      "duration": 60.0,
      "fps": 25.0,
      "gemini_uri": "files/xyz789",
      "gemini_cache_status": "expired",
    },
    {
      "filename": "local.mp4",
      "filepath": "/app/uploads/local.mp4",
      "size": 20971520,
      "modified": 1746546600.0,
      "duration": 45.0,
      "fps": 24.0,
      "gemini_uri": null,
      "gemini_cache_status": "not_uploaded"
    }
  ]
}
```
- `gemini_cache_status`: `"fresh"` | `"expired"` | `"not_uploaded"`
- `expires_in_hours`: int, **only present when status is `"fresh"`**
- `gemini_uri`: string or `null`
- Cache TTL = 48 hours from `gemini_uploaded_at` in DB

### `POST /upload` Response Shape (new fields)
```json
{
  "success": true,
  "filename": "demo.mp4",
  "filepath": "/app/uploads/demo.mp4",
  "duration": 120.5,
  "fps": 30.0,
  "total_frames": 3615,
  "width": 1920,
  "height": 1080,
  "gemini_uri": "files/abc123",
  "gemini_cache_status": "fresh"
}
```
- `gemini_upload_error` key added only when Gemini upload fails (non-fatal)
- `gemini_cache_status`: `"fresh"` or `"not_uploaded"` (never `"expired"` on fresh upload)

### `POST /videos/upload-to-gemini` — Re-upload endpoint
- **Request:** `{"filename": "demo.mp4"}`
- **Success:** `{"status": "ok", "uri": "files/abc123", "gemini_cache_status": "fresh"}`
- **Error (no key):** 503 `{"error": "GEMINI_API_KEY is not configured"}`
- **Error (file not found):** 404 `{"error": "File not found"}`
- **Error (upload failed):** 500 `{"error": "<message>"}`

## Learnings
- Issue #22 established `gemini_service.py` and DB schema foundation. All subsequent issues build on it.
- Issue #23 dropped all Reka CDN/sync logic from `/videos/list` and `/upload`. Those routes are now purely local+Gemini.
- Removed routes: `/videos/download`, `/reka/refresh-status/<video_id>`.
