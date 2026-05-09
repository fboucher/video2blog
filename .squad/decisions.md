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

---

## 2026-05-07: Decision — PR #32 Review — Blog Generation with Gemini Timestamps

**Date:** 2026-05-07  
**By:** Liz (Lead/Architect)  
**PR:** #32 (closes #25)  
**Author:** Ripley  
**Status:** APPROVED

### Verdict

**APPROVED** — All five acceptance criteria met. Architecture is clean and follows established patterns.

### Acceptance Criteria Assessment

| Criterion | Status |
|---|---|
| Blog generation calls Gemini and returns a blog draft | ✅ `gemini_service.generate_blog()` returns `{draft, timestamps}` |
| Gemini-suggested timestamps used for frame extraction | ✅ Timestamps passed to `extract_frames_at_timestamps()` |
| Scene detection fallback when timestamps empty | ✅ `extract_keyframes()` called when `timestamps` is falsy |
| Generated frames appear in output alongside blog draft | ✅ Response includes `frames` list + `blog` field |
| Old Reka blog generation route/logic removed | ✅ `/reka/ask` route replaced by `/gemini/generate-blog` |

### Review Notes

1. **Prompt design is solid.** Requesting raw JSON (no code fences) with a code-fence stripping fallback is a pragmatic two-layer defense against Gemini's formatting variability.
2. **`_resolve_gemini_uri()` reused correctly** — same helper used by the Q&A route at line 1106. No duplication.
3. **`_gemini_cache_status()` extracted cleanly** — single definition at line 98, reused in `_resolve_gemini_uri()`.
4. **Fallback path is clearly conditional.** `if timestamps:` → Gemini timestamps; `else:` → scene detection.
5. **Return shape** `{blog, frames, source, gemini_cache_status}` gives the UI all it needs.
6. **`/upload-from-url` rewrite** correctly replaces Reka with Gemini URL refs.

### Minor Observations (Non-blocking)

1. Response key mismatch: `generate_blog()` returns `draft`, route serializes as `blog`. Works fine for UI.
2. Reka remnants in other routes — scoped to #28.
3. `reka_service` import still present — scoped to #28.
4. Test covers fallback path only — Bishop can add happy-path test in #25's test pass.

### Implications for Downstream Issues

- **#27:** Can reuse `_resolve_gemini_uri()` and timestamp-vs-fallback pattern.
- **#28:** Must remove `import reka_service` and all remaining Reka routes/references.

---

## 2026-05-07: Decision — `GET /videos/list` Must Include URL-Based Videos

**Date:** 2026-05-08  
**By:** Ripley (Backend)  
**Related:** Issue #21 validation  
**Status:** IMPLEMENTED

### What

`GET /videos/list` now returns both local files (from filesystem) and URL-based videos (from DB). The two sources are merged into a single `videos` array.

### Why

URL videos have no local file — they are tracked only in the `video_sync` table with `source_url IS NOT NULL` and a pseudo-filename like `url-<hash>`. Filesystem-only scanning silently dropped them from the library, breaking the URL-as-input flow.

### Shape of URL Video Entries

```json
{
  "id": 42,
  "name": "My YouTube Video",
  "source": "url",
  "local_filename": "url-a1b2c3d4",
  "gemini_cache_status": "fresh",
  "can_select": true,
  "can_delete_local": false,
  "duration": 0,
  "size": 0,
  "fps": 0
}
```

- `gemini_cache_status` is hardcoded `"fresh"` — Gemini handles URLs natively, no TTL.
- `can_delete_local` is `false` — there is no local file to delete.
- `can_select` is `true` — URL videos are immediately usable for Q&A.

### Impact

- Frontend `loadAllVideos` now sees URL videos in the library after submission.
- No change to DB schema, DB service, or upload-from-url route.
- Local video behavior unchanged.

---

## 2026-05-07: Decision — URL Video UI Messaging — Issue #26

**Date:** 2026-05-07  
**By:** Hudson (Frontend)  
**Status:** IMPLEMENTED

### What

Implemented Option B (separate messaging + disabled button stub) to communicate URL video capabilities and frame-extraction deferral to users.

### Details

1. **URL Video Badge** — "🌐 URL video — Q&A ready" (lavender, `#b4befe`) in video library list.
2. **Q&A-Only Messaging** — Info box shown in chat welcome section when URL video is selected.
3. **Frame Extraction CTA** — Disabled button with toast on click; issue #27 will activate it.

### Why

Tooltip-only (Option A) is not discoverable. Badge-only (Option C) is insufficient. Option B gives users three progressive cues: badge → info box → disabled CTA.

### Implementation

- `static/js/app.js` — Conditional rendering in `displayUnifiedVideoList()`, `selectVideo()`, `handleExtraction()`
- `static/css/style.css` — Badge-lavender + message box styling

### Follow-up

Issue #27 will replace the disabled button stub with actual yt-dlp extraction UI.

---

## 2026-05-07: Frontend Audit — Stale Reka References + Defensive Defaults

**Date:** 2025-07-10  
**By:** Hudson (Frontend)  
**Status:** IMPLEMENTED

### What

Audited `static/js/app.js` and `templates/index.html` for stale Reka references and defensively handled absent API fields.

### Findings

1. **No stale Reka references** — frontend was already clean (no `/reka/*` routes, `refresh-status`, or `indexing_status`).
2. **`can_select` bug fixed** — when backend omits `can_select`, it was evaluated as `undefined` (falsy), disabling all videos. Fixed with `const canSelect = video.can_select !== false;` — defaults to `true`.
3. **`source` default added** — `const videoSource = video.source || 'local_only';` prevents `class="sync-icon undefined"` CSS class names.
4. **URL upload flow verified** — no frontend changes required; `loadAllVideos()` + `displayUnifiedVideoList()` already handle `source === 'url'` correctly once backend returns the field.

### Why

Defensive defaults ensure videos remain usable even if the backend temporarily omits explicit fields. Both defaults become no-ops once Ripley's backend fix adds explicit field values.


## 2026-05-09: Decision — SDK Migration from google-generativeai to google-genai

**Date:** 2026-05-09  
**By:** Ripley (Backend)  
**Status:** Implemented

### Context

Google ended all support for the `google-generativeai` package. Container was logging `FutureWarning: All support for the google.generativeai package has ended. Please switch to the google.genai package.` on every startup.

### Decision

Migrate `gemini_service.py` to `google-genai` (new unified SDK). Key changes:

- `_client()` now returns `genai.Client(api_key=key)` — single entry point for all API calls
- Chat: `client.chats.create(model=name, history=[...])` replaces `model.start_chat(history=[...])`
- Files: `client.files.upload/get/delete` replaces module-level `genai.upload_file/get_file/delete_file`
- `requirements.txt`: `google-generativeai` → `google-genai>=1.0.0` (latest: 2.0.1)

### Consequences

- **All public function signatures preserved** — no changes needed in `web_app.py` or other callers
- **Tests updated** to patch `gemini_service._client` directly (more robust, SDK-agnostic strategy)
- `google-genai` is actively maintained and required for continued Gemini 2.x access
- Conversation history format (list of `{role, parts}` dicts) unchanged

---

## 2026-05-09: Database Fix — init_db() Migration Ordering

**Date:** 2026-05-09  
**By:** Ripley (Backend)  
**Status:** Implemented

### What

Fixed `init_db()` in `db_service.py` to create `idx_source_url` index AFTER `ALTER TABLE ADD COLUMN source_url`, not before. Resolves migration crash on new DB initialization.

### Why

SQLite does not allow indexing non-existent columns. The migration order was:
1. ❌ CREATE INDEX idx_source_url ON video_sync(source_url) — fails, column doesn't exist yet
2. ALTER TABLE ADD COLUMN source_url

Corrected to:
1. ✅ ALTER TABLE ADD COLUMN source_url
2. CREATE INDEX idx_source_url ON video_sync(source_url)

### Impact

- Fresh DB initialization now succeeds
- Test coverage: 14/14 passing
### 2026-05-09: Pre-flight — Issue #12 AI Editing Phase

**By:** Liz (Lead)  
**Status:** APPROVED TO START

---

## Reka References Found and Fixed

| Issue | What Changed |
|-------|--------------|
| #12 | "Reka API" → "Gemini API" (2 occurrences in problem statement and solution); "Reka draft message" → "Gemini draft message" (user story 1); "reka_video_id" → "gemini file URI" (database schema note) |
| #14 | "Wire the existing **Reka** chat" → "Wire the existing **Gemini** chat"; "on each **Reka** draft message" → "on each **Gemini** draft message" |
| #13 | ✅ No Reka references |
| #15 | ✅ No Reka references |
| #16 | ✅ No Reka references (correctly uses Anthropic/OpenAI for editing service — NOT Gemini) |
| #17 | ✅ No Reka references |
| #18 | ✅ No Reka references |
| #19 | ✅ No Reka references |
| #20 | ✅ No Reka references |

---

## Architecture Note: Dual-Service Design

**The editing_service uses Anthropic/OpenAI — this is CORRECT and should NOT be changed to Gemini.**

Rationale:
- **Gemini** handles video understanding (upload, Q&A, blog generation from video) — it has native multimodal video capabilities
- **editing_service** handles text refinement (the "editorial polish" phase) — this is pure text-in/text-out, best served by Claude or GPT models via Anthropic/OpenAI SDKs
- This is a deliberate dual-provider architecture: Gemini for video, Claude/OpenAI for text editing

---

## Current Codebase Touchpoints for #14

### Where the "Start Editing" button needs to hook in

**File:** `static/js/app.js`  
**Function:** `addChatMessage(role, content)` (line 835)

Currently, assistant messages render with a "Download MD" button:
```javascript
} else if (role === 'assistant') {
    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        <button class="download-md-btn" onclick='downloadAsMarkdown(...)'>
            <span class="material-symbols-rounded">download</span>
            <span>Download MD</span>
        </button>
    `;
}
```

**Implementation approach:** Add a second button adjacent to "Download MD":
```javascript
<button class="start-editing-btn" onclick='startEditing(...)'>
    <span class="material-symbols-rounded">edit_note</span>
    <span>Start Editing</span>
</button>
```

### Route that generates Gemini chat response

**File:** `web_app.py`  
**Route:** `POST /gemini/ask` (called from `sendChatMessage()` in app.js at line 780)  
**Returns:** `{ answer: string, gemini_cache_status: string }`

### Message object shape in app.js

The `chatMessages` array stores objects as:
```javascript
{ role: 'user' | 'assistant', content: string }
```

The `content` field contains the raw markdown blog draft from Gemini. This is what the "Start Editing" button should POST to `/editing/drafts`.

### Video context available

`currentVideo` global object contains:
- `currentVideo.filename` — local filename or pseudo-filename for URL videos
- `currentVideo.name` — display name
- `currentVideo.source` — 'local_only' or 'url'

This provides the `video_id` and `video_name` fields needed for the draft creation.

---

## Work Order: Dependency Chain

```
#13 (DB layer)
    ↓
#14 (Start Editing button + editor skeleton)
    ↓
#15 (Skills discovery) ─────────────────┐
    ↓                                    │
#16 (AI streaming + Apply) ←────────────┤
    ↓                                    │
#17 (Export: Download/Copy) [parallel]   │
#18 (Transcript input) [after #16]       │
#19 (Parameterized modal) [after #15,#16]
#20 (Undo + history) [after #16]
```

### Execution order

1. **#13** — Ripley implements DB schema. Can start immediately.
2. **#14** — Hudson/Ripley collaborate on routes + UI. Blocked by #13.
3. **#15** — Ripley implements skills_service. Can start after #14 routes exist.
4. **#16** — Ripley implements editing_service + streaming. Blocked by #14, #15.
5. **#17, #18, #19, #20** — These can proceed in parallel once their blockers complete.

### Parallel opportunities

- Once #13 is done: #14 can start
- Once #14 is done: #15 and #17 can run in parallel
- Once #15 and #16 are done: #18, #19, #20 can all run in parallel

---

## Scope Concerns and Risks

### Low Risk
1. **Skills discovery** — straightforward file scanning with YAML parsing. Well-scoped.
2. **Export buttons** — reuses existing `downloadAsMarkdown` pattern. Minimal new code.
3. **DB schema** — simple two-table design with clear FK relationship.

### Medium Risk
1. **SSE streaming** — Flask's `stream_with_context` requires careful handling. Test with both providers.
2. **Provider detection** — Must gracefully handle missing API keys without crashing the app.

### Potential Scope Creep (Watch Out)
1. **text-editor sub-buttons (#19)** — The "modes" dropdown/sub-buttons could expand scope. Recommend: implement as a simple modal first, defer fancy UI.
2. **Transcript file parsing** — `.srt` and `.vtt` have timing metadata. Clarify: do we strip timings or preserve them? Recommend: strip timings, return plain text.

### Architecture Recommendation
- Create `editing_routes.py` as a separate Blueprint rather than adding to `web_app.py` — keeps concerns separated and `web_app.py` from growing larger.

---

## Checklist Before Team Starts

- [x] Feature branch `feat/issue-12-ai-editing` exists and is pushed
- [x] All issues (#12–#20) reviewed for stale Reka references
- [x] Issues #12 and #14 updated with Gemini terminology
- [x] Codebase confirms Gemini migration complete (no Reka imports in web_app.py, gemini_service.py is sole video provider)
- [x] Current chat message rendering location identified (`addChatMessage` at line 835 in app.js)
- [x] Dual-service architecture confirmed correct (Gemini for video, Anthropic/OpenAI for editing)

---

**Go/No-Go:** ✅ **GO** — All issues are ready. Team can begin implementation.

