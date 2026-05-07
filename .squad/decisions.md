# Team Decisions Log

## 2026-05-07: Team Expanded for Gemini Migration

**Date:** 2026-05-07  
**By:** Liz (on behalf of fboucher)  
**Status:** Active

### What
Hired two new team members to handle Gemini migration (issues #22–#28):
- **Ripley** — Backend Developer (Python, Flask, Gemini API, SQLite)
- **Hudson** — Frontend Developer (HTML/Jinja2, CSS, JavaScript, UI)

### Why
The existing team (Liz, Vasquez, Bishop) was built for Docker optimization and lacks backend implementation capacity. Gemini migration requires:
- Deep Python/Flask/REST API expertise (Ripley)
- Template/UI/AJAX expertise (Hudson)
- Vasquez continues to own Dockerfile/infra changes (#28)

### Scope
- Ripley owns issues #22–28 (backend, Python, Gemini API, database, yt-dlp)
- Hudson owns #23, #26 (frontend, UI, templates, JavaScript)
- Vasquez owns Docker changes in #28
- Bishop provides test coverage expectations for both

### Coordination Model
1. Ripley & Hudson sync on API response contracts before implementation
2. All decisions documented in decisions/inbox before action
3. Liz approves architecture/scope changes
4. Bishop sets test coverage gates

### Implementation Notes
- Onboarding files created: `.squad/agents/ripley/{charter,history}.md`, `.squad/agents/hudson/{charter,history}.md`
- Team registry updated in `.squad/casting/registry.json`
- Routing document updated: `.squad/routing.md`
- Team manifest updated: `.squad/team.md`

---

## 2026-05-07: Renamed Hicks → Liz

**By:** fboucher (via Copilot)  
**What:** Lead/Architect renamed from Hicks to Liz. All squad files updated.  
**Why:** User preference.

---

## 2026-05-07: Decision — PR #29 Review — Gemini Service Foundation

**Date:** 2026-05-07  
**By:** Liz (Lead/Architect)  
**Status:** APPROVED

### Context

PR #29 implements Issue #22 — the Gemini service + DB schema foundation that all other issues (#23–#28) depend on.

### Verdict

**APPROVED** — All acceptance criteria met. Architecture is sound for a Flask service layer.

### Architectural Decisions Established

1. **Stateless client pattern**: `_client()` reconfigures `genai` on every call. No singleton. Safe for multi-request Flask processes, avoids stale API key issues.
2. **No DB migration**: Schema uses `CREATE TABLE IF NOT EXISTS`. Existing Reka databases are not migrated — a fresh DB is expected. This is acceptable since we're replacing the entire system.
3. **Blocking upload**: `upload_video()` polls for up to 300s. Callers (Issue #23) MUST wrap this in a background task for acceptable UX.
4. **Dual file_ref contract**: `generate_blog()` and `ask()` accept both Gemini file URIs and public URLs. This enables #23 (local upload) and #26 (URL-based) to share the same API.

### What #23–#28 Implementers Must Know

- Always gate on `is_configured()` before API calls
- `upload_video()` is long-running — use background task + status polling
- After upload, persist via `db_service.update_gemini_upload(filename, uri, iso_timestamp)`
- Check `get_gemini_file_info(filename)` before re-uploading (48hr cache window)
- History format: `[{"role": "user"|"model", "parts": [str]}]`

### Follow-up Items (non-blocking)

- Pin `google-generativeai` version in requirements.txt
- Move inline imports to module level
- Extract `_configure()` helper for DRY
- Extract video_part resolution helper in generate_blog

---

## 2026-05-07: API Contract — Issue #23 Gemini Cache Status

**Date:** 2026-05-07  
**By:** Ripley (Backend)  
**For:** Hudson (Frontend UI implementation)  
**Status:** IMPLEMENTED

### What
Documented `/videos/list`, `POST /upload`, and `POST /videos/upload-to-gemini` response contracts for cache-aware UI badges and re-upload flow.

### Key Contracts

**`GET /videos/list`** returns all videos with cache status:
- `gemini_cache_status`: `"fresh"` | `"expired"` | `"not_uploaded"`
- `expires_in_hours`: present only when `"fresh"`
- `gemini_uri`: file URI or `null`

**`POST /upload`** (existing, now returns Gemini fields):
- Returns `gemini_uri`, `gemini_cache_status`, optional `gemini_upload_error`

**`POST /videos/upload-to-gemini`** (new re-upload endpoint):
- Request: `{ "filename": "..." }`
- Response: `{ "status": "ok", "uri": "files/...", "gemini_cache_status": "fresh" }`
- Error codes: 400 (missing field), 404 (file not found), 503 (key not configured), 500 (API error)

### UI Badges (Hudson)
- **Fresh (green):** "✓ Cached (41h remaining)" — re-upload not needed
- **Expired (amber):** "⚠ Cache Expired" — show "Re-upload" button
- **Not Uploaded (grey):** "○ Local Only" — show "Upload to Gemini" button

### Removed Routes
- ~~`POST /videos/download`~~ (Reka CDN)
- ~~`POST /reka/refresh-status/<video_id>`~~ (Reka polling)
