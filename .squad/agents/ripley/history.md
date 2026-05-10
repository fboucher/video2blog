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

---

### Issue #13 — DB Layer: Drafts & Version Schema (2026-05-09)

**Branch:** `squad/13-db-drafts-schema` → PR #36 → target `feat/issue-12-ai-editing`

**Schema decisions:**
- `drafts` table stores current content + optional transcript. `video_id` is a string key (local_filename or URL pseudo-filename) matching `video_sync`.
- `draft_versions` stores every content snapshot with `skill_used TEXT` (NULL = manual edit, `'restore'` = version restore, any string = AI skill label).
- Foreign key `draft_id REFERENCES drafts(id) ON DELETE CASCADE` enforces referential integrity.

**Function signatures established:**
```python
create_draft(video_id: str, video_name: str, content: str) -> int
get_draft(draft_id: int) -> dict | None
update_draft(draft_id: int, content: str, transcript: str | None = None, skill_used: str | None = None) -> None
list_draft_versions(draft_id: int) -> list[dict]
restore_draft_version(draft_id: int, version_id: int) -> None  # raises ValueError on bad version_id
```

**Patterns/gotchas:**
- `update_draft()` signature extends the spec with an optional `skill_used` param so callers (AI skills) don't need a separate path.
- `list_draft_versions()` orders by `id DESC` (not `created_at DESC`) — SQLite timestamps have 1-second resolution, which causes ties on fast consecutive inserts.
- `restore_draft_version()` raises `ValueError` (not silent) when `version_id` doesn't belong to `draft_id`. Protects against cross-draft corruption.
- Tests use same `mem_db` fixture pattern as `test_db_service.py` (patch `db_service.get_db` + `os.makedirs`, call `init_db()`).

---

## Issue #15 — Skills Discovery Service + Skill Buttons (2025-05-09)

**Branch:** `squad/15-skills-service` → PR #41 → target `feat/issue-12-ai-editing`

### What was built
- **`skills_service.py`** — core module for skill discovery:
  - `list_skills(skills_folder=None)` scans `SKILLS_FOLDER` env var (default `./skills`)
  - Parses YAML front matter (`name`, `description`) from `SKILL.md` files
  - Skips malformed files without crashing (logs warnings)
  - `get_skill_prompt(skill_name, skills_folder=None)` returns prompt body with front matter stripped
  - Raises `FileNotFoundError` for missing skills, `ValueError` for malformed front matter
  
- **Bundled skills:**
  - `skills/edit-video-blog/SKILL.md` — refine video-to-blog drafts for clarity, flow, SEO
  - `skills/text-editor/SKILL.md` — general-purpose copy editing and proofreading
  
- **API routes** (extended `editing_routes.py`):
  - `GET /editing/skills` — returns JSON list `[{name, description}, ...]`
  - `GET /editing/skill/<name>` — returns `{prompt: "..."}` or 404
  
- **Editor UI** (`templates/editor.html`):
  - Right pane changed from placeholder to skill buttons container
  - Fetches `/editing/skills` on page load, renders one button per skill
  - Clicking a skill shows toast (AI wiring deferred to #16)
  - CSS styles for skill buttons with hover effects
  
- **Infrastructure:**
  - `docker-compose.yml` — added `./skills:/app/skills` volume mount
  - `.env.example` — documented `SKILLS_FOLDER` configuration
  - Tests: `tests/test_skills_service.py` (9 tests) + integration tests in `test_editing_routes.py`

### Implementation details
- Simple front matter parser using regex (no YAML library dependency)
- Parsing pattern: `^---\n(.*?\n)---\n(.*)$` with manual key:value extraction
- Skills folder structure: `<skills_folder>/<skill-name>/SKILL.md`
- Malformed files (missing name/description, no front matter, etc.) are skipped with warnings

### Test coverage
- Valid/multiple skills, empty folder, missing front matter, missing required fields
- Ignores non-directory entries, handles nonexistent folder
- `get_skill_prompt()` returns body, raises errors for missing/malformed skills
- Integration tests for API routes (200, 404 cases)
- Fixed pre-existing test syntax error in `test_gemini_service.py` (unrelated to #15)

### Patterns/gotchas
- Skills are discovered dynamically — no static registration
- `skills_folder` param on all functions enables testing with tempdir
- Front matter is simple key:value pairs (not full YAML objects/arrays)
- UI fetches skills on page load (no caching, no hot reload)

## Issue #14 — Flask Editing Blueprint (2026-05-09)

**Branch:** `squad/14-editor-routes` → PR #39 → target `feat/issue-12-ai-editing`

### What was built
- Created `editing_routes.py` as a Flask Blueprint (`editing_bp`) with 4 routes:
  - `POST /editing/drafts` → 201 + `{draft_id}`
  - `GET /editing/drafts/<draft_id>` → 200 draft dict / 404
  - `PUT /editing/drafts/<draft_id>` → 200 `{status: ok}` / 400 if content missing
  - `GET /editor?draft_id=<id>` → renders `editor.html` / 400 if no param / 404 if not found
- Registered `editing_bp` in `web_app.py` via `app.register_blueprint(editing_bp)`
- Integration tests: 8 pass, 1 skip (template test pending Hudson's `editor.html`)

### conftest.py patterns for Flask route tests
When importing `web_app` in tests outside Docker, three mocks are needed:
1. `cv2` — not installed in linuxbrew Python env; `sys.modules.setdefault("cv2", MagicMock())`
2. `numpy` — same; `sys.modules.setdefault("numpy", MagicMock())`
3. `pathlib.Path.mkdir` — web_app.py creates `/app/uploads` at module level; wrap to swallow `PermissionError`/`FileNotFoundError`

All three mocks live in `tests/conftest.py` at module level so they're in place before the first `from web_app import app` call in any fixture.

### Pattern confirmed
- Blueprint registration: `app.register_blueprint(bp)` placed immediately after `db_service.init_db()` in web_app.py — keeps the registration site obvious.
- Hudson's `squad/14-editor-ui` branch already has `editor.html`; template test will pass once that PR merges into the base branch.

---

## Issue #16 — AI Streaming via editing_service + Apply to Draft (2026-05-09)

**Branch:** `squad/16-editing-service` → PR #XX → target `feat/issue-12-ai-editing`

### What was built
- **`editing_service.py`** — AI text editing service module:
  - `is_configured()` → returns True when `EDITING_API_KEY` is set
  - `get_provider()` → returns `"anthropic"` (default) or `"openai"` based on `EDITING_PROVIDER` env var (normalized to lowercase)
  - `stream_edit(system_prompt, draft, transcript, messages)` → generator yielding SSE-formatted JSON chunks `{"delta": "...", "done": false}` with final chunk `{"done": true}`
  - Routes to Anthropic SDK (streaming messages) or OpenAI SDK (chat completions with stream=True)
  - Supports `EDITING_BASE_URL` for OpenAI-compatible providers

- **`POST /editing/stream` route** (`editing_routes.py`):
  - Accepts `{draft_id, skill_name, transcript_override, messages}` (messages reserved for future multi-turn)
  - Returns 400 if draft_id/skill_name missing, 404 if draft/skill not found, 503 if editing service not configured
  - Streams SSE response with `Content-Type: text/event-stream` using `stream_with_context()`
  - Fetches draft, skill prompt, transcript; passes to `editing_service.stream_edit()`

- **Frontend streaming UI** (`templates/editor.html`):
  - Skill buttons now POST to `/editing/stream` when clicked
  - Streams response into `.ai-bubble` element in right pane using `ReadableStream` + `TextDecoder`
  - Parses SSE chunks line-by-line: `data: {...}\n\n`
  - Accumulates text as it arrives, appends to bubble
  - On `done: true`, adds "Apply to draft" button to bubble
  - "Apply to draft" replaces left-pane textarea content + PUTs to `/editing/drafts/<id>` to persist
  - Shows success toast on apply

- **Configuration** (`.env.example`):
  - Added `EDITING_PROVIDER` (default: anthropic)
  - `EDITING_API_KEY` (required)
  - `EDITING_MODEL` (defaults: claude-sonnet-4-6 for Anthropic, gpt-4o-mini for OpenAI)
  - `EDITING_BASE_URL` (optional, for OpenAI-compatible providers)

- **Dependencies** (`requirements.txt`):
  - Added `anthropic`
  - Added `openai`

- **Tests** (`tests/test_editing_stream.py`):
  - 7 unit tests for `is_configured()` and `get_provider()` with env var mocking (all passing)
  - 5 integration tests for `POST /editing/stream` (SSE headers, JSON chunk validation, error cases) using mocked `editing_service.stream_edit`
  - All 12 tests passing (unit tests run without Flask dependencies)
  - Tests use real skill names (`edit-video-blog`) to match bundled skills

### Architecture decisions
- **Gemini handles video understanding. Anthropic/OpenAI handle text editing.** These are INTENTIONALLY separate services with different roles. Gemini is for video Q&A and initial transcript generation. Editing service refines text drafts.
- Used `stream_with_context()` to keep Flask request context alive during SSE streaming
- SSE format: `data: <json>\n\n` (required double newline)
- Frontend buffers incomplete SSE lines (handles chunked TCP packets)
- "Apply to draft" creates a draft version snapshot (via existing `update_draft()`)

### API Contract for Hudson
**Endpoint:** `POST /editing/stream`

**Request:**
```json
{
  "draft_id": 123,
  "skill_name": "edit-video-blog",
  "transcript_override": "optional transcript",
  "messages": []  // reserved for multi-turn, not used yet
}
```

**Response:** `Content-Type: text/event-stream`
```
data: {"delta": "Hello", "done": false}

data: {"delta": " world", "done": false}

data: {"done": true}

```

**Error responses:**
- 400 `{"error": "draft_id and skill_name required"}` — missing required fields
- 404 — draft not found or skill not found
- 503 `{"error": "Editing service not configured. Set EDITING_API_KEY."}` — no API key

### Patterns/gotchas
- SSE chunks MUST end with `\n\n` (two newlines) per spec
- Frontend splits on `\n` and keeps incomplete line in buffer (handles TCP packet boundaries)
- `stream_edit()` is a generator — use `yield from` in Flask route
- Anthropic SDK: `client.messages.stream()` context manager, iterate `stream.text_stream`
- OpenAI SDK: `client.chat.completions.create(stream=True)`, iterate chunks, extract `delta.content`
- Both SDKs auto-chunk responses — no need for manual token buffering
- `EDITING_BASE_URL` enables compatibility with OpenRouter, Azure OpenAI, local LLMs, etc.

### Test strategy
- Unit tests use `monkeypatch` to control env vars, import `editing_service` after patching
- Integration tests mock `editing_service.stream_edit` to return pre-baked SSE chunks (avoids real API calls)
- Tests verify SSE headers (`text/event-stream`), JSON chunk validity, final `done: true` chunk
- Skills tests use real bundled skills (`edit-video-blog`, `text-editor`) — ensures integration contracts stay valid

