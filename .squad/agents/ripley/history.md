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

### Bug Fix — Issue #21 Validation: URL Videos Not Appearing in `/videos/list` + Duplicate Function (2026-05-08)

**Bug 1 — `list_all_videos()` only scanned filesystem:**  
URL-based videos live only in the DB (pseudo-filename `url-<hash>`, `source_url` set, no local file). The original implementation used `os.listdir()` exclusively, so URL videos were invisible to the frontend. Fixed by:
- Moving `import cv2` to the top of the function (cosmetic)
- Pre-fetching all DB records via `db_service.list_all_syncs()` and building a `db_by_filename` lookup
- Enriching local video entries with `id`, `name`, `source='local_only'`, `local_filename`, `can_select=True`, `can_delete_local=True`
- Adding a second loop over all DB records to append URL videos (`source_url IS NOT NULL` + `local_filename LIKE 'url-%'`) with `source='url'`, `can_select=True`, `can_delete_local=False`, `gemini_cache_status='fresh'`
- Deduplication guard: skip URL records whose `local_filename` already appears in the local-file list (handles converted videos)

**Bug 2 — Duplicate `_gemini_cache_status` definition:**  
The function was defined twice. The first definition (lines 91–107) used `GEMINI_CACHE_TTL_HOURS` before it was defined (line 144) and returned `age_hours` instead of `expires_in_hours`. The second definition (lines 147–166) was the correct one. Removed the dead first definition entirely.

**Pattern confirmed:** Always query DB for URL videos — they have no filesystem presence.
- Issue #22 established `gemini_service.py` and DB schema foundation. All subsequent issues build on it.
- Issue #23 dropped all Reka CDN/sync logic from `/videos/list` and `/upload`. Those routes are now purely local+Gemini.
- Removed routes: `/videos/download`, `/reka/refresh-status/<video_id>`.

## Issue #23 Completion Summary

**Date:** 2026-05-07  
**Status:** ✅ COMPLETE — PR #30 open, targeting dev

### Endpoints Delivered
1. **`GET /videos/list`** — Returns all videos with Gemini cache status (fresh/expired/not_uploaded)
2. **`POST /videos/upload-to-gemini`** — Re-upload endpoint for expired/not_uploaded videos
3. **`POST /upload` (enhanced)** — Now returns `gemini_uri` and `gemini_cache_status`

### Implementation Decisions
- Cache status computed from `gemini_uploaded_at` in DB (48-hour TTL)
- Upload runs in background thread (non-blocking)
- Error handling: 503 (key not configured), 404 (file not found), 500 (API error)
- Removed `/videos/download` and `/reka/refresh-status/<video_id>` endpoints

### Testing Verified
- ✓ `/videos/list` returns correct cache status for all video states
- ✓ Upload persists URI to DB
- ✓ Error codes returned correctly
- ✓ Old Reka routes removed

---

## Issue #27 — URL Video Frame Extraction via yt-dlp

**Branch**: `squad/27-url-video-frame-extraction-yt-dlp`

### What was built
- Added `yt-dlp` to `requirements.txt`
- Added `download_video_from_url(url, output_path) -> str` to `gemini_service.py` — wraps yt-dlp subprocess with extension auto-detection
- Added `convert_url_video_to_local(url_filename, local_filename)` to `db_service.py` — renames the DB record from pseudo-filename to real local file after download
- Added `POST /videos/extract-frames-url` route to `web_app.py` — downloads URL video via yt-dlp, updates DB, runs `extract_keyframes()`
- Updated `static/js/app.js` — enabled disabled Extract Frames button for URL videos; wired it to new endpoint via `handleUrlExtraction()`; refreshes video library on success so URL video appears as local

---

## Issue #28 — Final Reka removal, UUID sanitize_filename, Dockerfile + README

**PR**: https://github.com/fboucher/video2blog/pull/35
**Branch**: `squad/28-reka-removal-sanitize-dockerfile-readme`

### What was done
- Deleted `reka_service.py` entirely
- Removed `import reka_service` and all four `/reka/*` routes (`/reka/status`, `/reka/videos`, `/reka/upload`, `/reka/delete/<id>`) from `web_app.py`
- Replaced `sanitize_filename(video_name, reka_video_id)` with UUID-based `sanitize_filename(video_name)` — appends `uuid4().hex[:8]` suffix to avoid filename collisions
- Dockerfile updated: `COPY reka_service.py` → `COPY gemini_service.py`
- README updated: replaced Reka badge and docs with Gemini API key table; removed all Reka mentions
- `app.js` cleaned: removed dead `downloadVideo`, `refreshStatus`, `deleteReka` functions; removed `reka_*` field references from upload toast logic and source icon map

**Note**: The full Gemini migration PRD (#21) is now complete with this issue.

---

## Learnings

### Bug Fix — Reka schema DB migration in init_db (2026-05-09)

**Problem:** The persisted Docker volume DB had the old Reka schema (`reka_video_id TEXT NOT NULL`, no `gemini_file_uri`). `CREATE TABLE IF NOT EXISTS` skips creation on existing DBs, so the new columns were never added and the NOT NULL constraint on `reka_video_id` caused `add_sync()` to fail.

**Fix:** Added a Reka-schema detection step in `init_db()` using `PRAGMA table_info(video_sync)`. If `reka_video_id` is found, perform a full table rebuild: rename old table, create new table, copy rows (mapping `sync_status` to `'synced'`, NULLing Reka-only columns), drop old table. Followed by incremental `ADD COLUMN` migrations for partial Gemini schema DBs.

**Pattern confirmed:** SQLite can't DROP COLUMN or remove NOT NULL without a full table rebuild. The rename→create→copy→drop pattern is the canonical SQLite migration strategy for structural schema changes.

---

### Bug Fix — init_db column ordering crash + google-genai SDK migration (2026-05-09)

**Bug 1 — `CREATE INDEX` before `ALTER TABLE` migration:**
`init_db()` was creating `idx_source_url` on line 49 *before* the `ALTER TABLE ADD COLUMN source_url` migration on line 52. On existing databases that predate the `source_url` column, SQLite raised `OperationalError: no such column: source_url`. Fix: moved the index creation to after the try/except migration block.

**Pattern confirmed:** Always run schema migrations (ALTER TABLE) before any index or constraint that depends on the new column — even within a single `init_db()` function.

**Bug 2 — FutureWarning from deprecated `google-generativeai` package:**
Google ended support for `google.generativeai`; new SDK is `google.genai`. Key API differences:
- Old: `genai.configure(api_key=key); model = genai.GenerativeModel(name); chat = model.start_chat(history=...); chat.send_message(...)`
- New: `client = genai.Client(api_key=key); chat = client.chats.create(model=name, history=...); chat.send_message(...)`
- Files: `genai.upload_file(path, mime_type=...)` → `client.files.upload(path=path)`; `genai.get_file(name)` → `client.files.get(name=name)`; `genai.delete_file(name)` → `client.files.delete(name=name)`
- `_client()` now returns `genai.Client` instead of `genai.GenerativeModel` — cleaner single abstraction point

**Test strategy:** Patching `gemini_service._client` to return a `MagicMock` is cleaner than mocking module-level `genai` attributes. Tests no longer import `google.generativeai` at all.

---

### Bug Fix — google.genai SDK API surface mismatches in gemini_service.py (2026-05-09)

Three confirmed runtime bugs caused 500s on `POST /videos/upload-to-gemini` and `POST /gemini/ask`:

**Bug 1 — `files.upload()` keyword arg:**  
Old code: `client.files.upload(path=local_path)` — **wrong keyword**.  
New SDK signature: `files.upload(*, file: Union[str, PathLike, IOBase], config=None)`.  
Fix: `client.files.upload(file=local_path)`.

**Bug 2 — URL video part was a raw dict:**  
`{"file_uri": url, "mime_type": "video/mp4"}` was passed as an element of a list to `send_message()`. The SDK's internal `_is_part_type()` check uses `get_args(types.PartUnion)` which is `(str, File, Part)` — **dicts are not in this tuple**, so `_is_part_type` returns `False` and `send_message` raises `ValueError`.  
Fix: Use `types.Part.from_uri(file_uri=url, mime_type="video/mp4")` — a proper `Part` object.

**Bug 3 — History dicts had string parts:**  
Chat history dicts `{"role": "user", "parts": ["text string"]}` were passed to `chats.create(history=...)`.  
`_BaseChat.__init__` calls `Content.model_validate(content_dict)` on each item.  
`Content.parts` is typed `list[Part]`, so Pydantic V2 rejects plain strings — raises `ValidationError`.  
Fix: Added `_build_history()` helper that converts each message dict into `types.Content` with explicit `types.Part(text=p)` wrappers.

**Key SDK facts verified from source (google-genai 2.0.1):**
- `files.upload(*, file=...)` — path as positional via `file=` kwarg
- `files.get(name=...)` returns a `File` object which IS a valid `PartUnion` member and can be passed directly to `send_message`
- `send_message(message)` validates via `_is_part_type()` against `PartUnion = Union[str, File, Part]` — dicts are rejected at runtime even though `PartUnionDict` is in the type annotation
- `FileState` is `CaseInSensitiveEnum(str, enum.Enum)` — both `.name` and `.value` equal `'PROCESSING'`/`'ACTIVE'` so existing state checks are correct
- History must contain `types.Content` objects (or dicts with proper `PartDict` parts, not plain strings)
