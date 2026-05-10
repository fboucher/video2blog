# Hudson — History

## Project Context
- **Project:** video2blog
- **Stack:** Jinja2, HTML5, CSS3, vanilla JavaScript, Flask template rendering
- **User:** fboucher
- **Mission:** Build UI for Gemini migration (issues #23, #26)
- **Base branch:** dev
- **Feature branches:** squad/23, squad/26 (branched from dev)

## Architecture Overview

### Frontend Structure
- **`templates/`** — All Jinja2 templates (base.html, form.html, status panels, modals)
- **`static/css/`** — Stylesheets (normalize.css, layout.css, components.css)
- **`static/js/`** — JavaScript modules (api-client.js, ui-controller.js, form-handler.js)

### Key Templates & Components
- **`base.html`** — Base layout with navigation, footer, static assets
- **`upload.html`** — File upload form with progress indicator (for #23)
- **`library.html`** — Video library grid, status indicators, cache info (for #23)
- **`qa.html`** — Question/answer conversation panel (for #23, #26)
- **`url-video.html`** — URL input form, frame preview, Q&A (for #26)

### Issue Map & Frontend Scope

| Issue | Title | Hudson Scope |
|-------|-------|--------------|
| #23 | Local video upload + file caching | Upload form, library status panel, cache indicator |
| #26 | URL video Q&A without download | URL input form, frame preview, Q&A display |

## Flask Template Patterns
- Use `render_template()` with context dicts from routes
- Jinja2 loops for dynamic content (video lists, Q&A history)
- Form validation with HTML5 attributes + AJAX fallback
- Loading states via CSS classes and JavaScript toggles

## AJAX Integration Strategy
- Fetch API for POST (upload, Q&A), GET (library status, frames)
- Error responses handled with toast notifications
- Loading spinners on long-running requests
- Graceful fallback if JavaScript disabled

## CSS Conventions
- Mobile-first responsive design
- CSS Grid for layouts, Flexbox for components
- No CSS frameworks (vanilla CSS only)
- Semantic color naming (--color-primary, --color-error, etc.)

## JavaScript Conventions
- Vanilla JS (no jQuery, no React)
- Event listeners scoped to specific elements
- Separation of concerns (api module, ui module, form module)
- Consistent error handling for network failures

## Learnings
- Initial setup complete. Ready for issue #23 template implementation.

## Issue #26 Implementation — URL Video Q&A without Download

**Date:** 2026-05-07  
**Status:** ✅ Complete (PR #33)  
**Branch:** `squad/26-url-video-qa-without-download`

### UI Components Built

1. **URL Input Form Updates**
   - Button text: "Add URL for Q&A" (previously "Upload to Reka")
   - Button icon: `add_link` (previously `cloud_upload`)
   - Toast messages updated to remove Reka branding

2. **URL Video Badge & Library Display**
   - New source type: `url` (alongside synced, reka_only, local_only)
   - Badge: "🌐 URL video — Q&A ready" (badge-lavender color)
   - Icon: `language` in lavender color
   - Proper labeling in video list

3. **Q&A-Only Messaging**
   - When URL video is selected, shows:
     - "💡 This video is Q&A-ready"
     - "Frame extraction will download the video when triggered"
   - Q&A input/button work normally (uses `/gemini/ask` API)

4. **Frame Extraction CTA (Stub)**
   - Disabled button for URL videos
   - Label: "Extract Frames (downloads video)"
   - Tooltip: "Frame extraction coming soon — this will download the video"
   - Shows toast message when clicked: "Frame extraction coming soon..."
   - Actual implementation deferred to issue #27

### CSS Additions
- `.badge-lavender` — New badge variant with Catppuccin lavender color
- `.url-video-message` — Styled info box for Q&A-only messaging
  - Uses flexbox for icon + text layout
  - Blue background with border
  - Responsive padding and typography

### JavaScript Updates
- `uploadFromUrl()` — Updated toast messages (no Reka references)
- `displayUnifiedVideoList()` — Added URL source icon + badge rendering
- `selectVideo()` — Conditional logic for URL vs local video params display
- `handleExtraction()` — Check for URL source and show stub message

### UI Patterns Established
- **Source Icons**: Green (synced), Blue (reka_only), Yellow (local_only), Lavender (url)
- **Conditional UI Rendering**: Toggle params/CTA based on video.source
- **Toast Notifications**: User feedback for URL uploads and extraction attempts
- **Disabled State Styling**: Extract button disabled for URL videos with title attribute

### Notes
- No local file created for URL videos (pseudo-filename used: `url-<hash>`)
- Q&A capability available immediately (no download required)
- Frame extraction will require yt-dlp integration (issue #27)
- Reka branding successfully removed from URL upload flow

## Issue #23 — Local Video Upload + Gemini Caching — Frontend Implementation

**Date:** 2026-05-07
**Branch:** squad/23-local-video-upload-gemini-caching-library-ui

### What Was Built

1. **Gemini Cache Status Badges**
   - Replaced Reka indexing status with Gemini cache status in video library
   - Badge states: `fresh` (green, "Ready (Xh)"), `expired` (red, "Expired"), `not_uploaded` (gray, "Not uploaded")
   - Uses existing badge CSS classes (.badge-green, .badge-red, .badge-gray)
   - Shows expiration time in hours for fresh cache

2. **Upload to Gemini Button**
   - Conditional button appears for `expired` and `not_uploaded` videos
   - POST to `/videos/upload-to-gemini` with `{ filename: video.filename }`
   - Shows loading spinner (sync icon with CSS animation) while uploading
   - Reloads video list on success
   - Error handling with toast notifications

3. **Removed Reka-Related UI**
   - Removed "Download to local" button (was `/videos/download` endpoint)
   - Removed "Refresh indexing status" button (was `/reka/refresh-status` endpoint)
   - Removed "Delete from Reka" button
   - Updated disabled button tooltip to "Video not ready for processing"

### Frontend Patterns Used

**Status Badge Implementation:**
- Conditional badge rendering in template based on video.gemini_cache_status
- Separate function `getStatusBadge()` handles badge logic and styling
- Used Material Symbols icons for visual consistency (check_circle, schedule, cloud_upload)

**Upload Handler Pattern:**
- Async function with event.target detection to find button element
- Preserves original HTML for restoration on error
- Button disabled state during upload to prevent double-submission
- Inline CSS animation for spinner (animation: spin 1s linear infinite;)

**Error Handling:**
- Toast notifications for all user-facing messages
- Graceful fallback if button element not found
- HTML restoration on network or API errors

### API Contract Implementation

Expects `/videos/list` endpoint to return:
```json
{
  "filename": "video.mp4",
  "gemini_cache_status": "fresh" | "expired" | "not_uploaded",
  "expires_in_hours": 12  // only for fresh status
}
```

Uses `/videos/upload-to-gemini` endpoint:
```json
POST { "filename": "video.mp4" }
Response: { "status": "ok", "gemini_cache_status": "fresh" }
```

### Technical Notes

- No additional CSS required; reused existing badge classes
- Spinner animation uses existing @keyframes spin CSS rule
- Event handling via inline onclick with JSON serialization (escaping single quotes)
- Video object destructuring in template for clean conditional rendering

## Issue #23 Completion Summary

**Date:** 2026-05-07  
**Status:** ✅ COMPLETE — PR #30 open, targeting dev

### UI Components Delivered
1. **Cache Status Badges** — Fresh (green), Expired (amber), Not Uploaded (grey)
2. **Re-upload Button** — Triggers `/videos/upload-to-gemini` with spinner feedback
3. **Toast Notifications** — Success/error messages with helpful copy
4. **Reka UI Removal** — Removed download, refresh, and CDN view buttons

### Frontend Patterns Used
- Conditional badge rendering based on `gemini_cache_status`
- Async button handler with button element detection
- CSS spinner animation (rotate 360°)
- Toast notification system (3-4 second auto-dismiss)
- Error toast with user-friendly status code messages

### Testing Verified
- ✓ Cache status badges render correctly (fresh/expired/not_uploaded)
- ✓ Re-upload button visible and functional
- ✓ Spinner shows during upload, toast on success/error
- ✓ Old Reka UI elements removed
- ✓ Video list refreshes after successful re-upload

## Issue #14 — Start Editing Button + editor.html Split-Pane

**Date:** 2026-05-09  
**Status:** ✅ Complete (PR #38)  
**Branch:** `squad/14-editor-ui`  
**Base:** `feat/issue-12-ai-editing`

### UI Components Built

1. **"Start Editing" button** — added to every `assistant` chat message alongside "Download MD"
   - Blue (`--ctp-mocha-blue`) to contrast with the pink "Download MD" button
   - Calls `startEditing(videoId, videoName, content)` which POSTs to `/editing/drafts`
   - On success, redirects to `/editor?draft_id=<id>`

2. **`templates/editor.html`** — standalone split-pane editor page
   - Left 60%: `<textarea id="draft-content">` pre-populated via `{{ draft.content }}`
   - Right 40%: AI chat placeholder ("Coming soon" badge, `auto_fix_high` icon)
   - Toolbar: Back link (→ `/`), video name title, Save button, "Saved" indicator

3. **Auto-save** — debounced 2 s after any textarea change
   - Only fires if content changed since last save
   - Ctrl/Cmd+S also triggers manual save
   - "Saved" indicator fades in for 2.5 s on success

4. **CSS additions to `style.css`**
   - `.message-actions` — flex row grouping Download MD + Start Editing
   - `.start-editing-btn` — blue button styled like `.download-md-btn`

### Technical Decisions

- **Standalone HTML** (no base template) — index.html has no Jinja2 `{% extends %}` block, so editor.html replicates the Catppuccin Mocha palette inline
- **`tojson` filter** for DRAFT_ID in script tag — safe injection of integer into JS
- **Keyboard shortcut** Ctrl/Cmd+S added for power-user UX
- **No external dependencies** — same vanilla JS, no React/jQuery

### API Contracts Used

- `POST /editing/drafts` — body: `{video_id, video_name, content}` → `{draft_id}`
- `PUT /editing/drafts/<id>` — body: `{content}` → `{status: "ok"}`
- `GET /editor?draft_id=<id>` — rendered by Ripley's route with `draft` context

## Issue #17 — Export: Download MD + Copy to Clipboard

**Date:** 2026-05-09  
**Status:** ✅ Complete (PR #40)  
**Branch:** `squad/17-export-buttons`  
**Base:** `feat/issue-12-ai-editing`

### UI Components Built

1. **"Download MD" button** — added to editor toolbar
   - Exports **live textarea content** (not last-saved version) as `.md` file
   - Uses Blob API + `URL.createObjectURL()` pattern (same as `downloadAsMarkdown` in app.js)
   - Filename: `{video_name}_draft.md` (sanitized with regex for filesystem safety)
   - Success toast notification: "Markdown downloaded!"

2. **"Copy to clipboard" button** — added to editor toolbar
   - Copies live textarea content using `navigator.clipboard.writeText()`
   - Visual confirmation: button text changes to "Copied!" for 2 seconds
   - Error handling with toast notification if clipboard API fails

### CSS Styling

- **`.export-btn`** — new button class styled with Catppuccin blue (`--ctp-mocha-blue`)
- Hover state: lavender (`--ctp-mocha-lavender`) with subtle lift + shadow
- Active state: revert transform for tactile feedback
- Consistent sizing/spacing with existing `.save-btn` (pink)

### Technical Implementation

- **Button placement**: Toolbar, positioned between "Saved" indicator and "Save" button
- **Content source**: `textarea.value` (live content, not `lastSavedContent` variable)
- **Filename generation**: Uses Jinja2 `{{ draft.video_name | tojson }}` with fallback to `'draft'`
- **Clipboard feedback**: Stores `originalHTML` to restore button after 2-second confirmation
- **Error handling**: try/catch with console.error + toast for clipboard failures

### Code Organization

All functionality inline in `editor.html` `<script>` block:
- `downloadMarkdown()` — 15 lines, Blob + download logic
- `copyToClipboard()` — async, 14 lines, clipboard API + visual feedback
- No external JS file created (keeping with existing editor.html pattern)

## Learnings

- The app uses Catppuccin Mocha throughout — always pull from the existing CSS vars, never hardcode hex colors.
- `addChatMessage()` builds innerHTML as a template string; use `JSON.stringify().replace(/'/g, "&#39;")` pattern to safely embed content into `onclick` handlers.
- Buttons within `.chat-message.assistant` need a wrapper `div.message-actions` with `display:flex; gap:8px` — the assistant bubble is already a flex column.
- `tojson` Jinja2 filter is the safe way to pass Python values into JS `<script>` blocks.
- For temporary button state changes (like "Copied!" feedback), store `originalHTML` and use `setTimeout()` to restore after visual confirmation period.
- When creating export/download functions, always use `URL.revokeObjectURL()` after download to free memory.
- **Sticky controls pattern:** Use `flex-shrink: 0` with `max-height` and `overflow-y: auto` for fixed-position panels that can scroll internally if content exceeds max height. Prevents long control panels from pushing scrollable content off-screen.
- **Removing placeholder elements:** Always check for `.querySelector('.placeholder-class')` and call `.remove()` before appending dynamic content to avoid stale UI artifacts.
- **Ctrl+Enter shortcut:** Wire `keydown` event on textarea to check `(e.ctrlKey || e.metaKey) && e.key === 'Enter'` for cross-platform submit behavior.

## Editor UX Improvements — Custom Prompt + Sticky Controls

**Date:** 2025-05-10  
**Branch:** `feat/issue-12-ai-editing`  
**Status:** ✅ Complete

### Problem

Frank reported excessive scrolling in the editor:
- Skill buttons + version history were in a long scrolling list
- After AI responses appeared, had to scroll back to top to click another skill
- No way to ask free-form questions to AI

### Solution

**1. Restructured right pane into two sections:**
- **Sticky controls panel** (`.skills-panel`) — `max-height: 45vh`, `overflow-y: auto`
  - Contains: transcript accordion, skill buttons, custom prompt input, version history
  - Stays at top of pane, scrolls internally if needed
- **Scrollable output area** (`#ai-output-area`) — `flex: 1`, `overflow-y: auto`
  - AI response bubbles append here
  - Empty state placeholder when no responses yet

**2. Added custom prompt section:**
- Free-form textarea for any AI question/instruction
- "Send" button with lavender/blue styling
- Ctrl+Enter keyboard shortcut for power users
- Sends to `/editing/stream` with `system_prompt_override` (skill_name: 'custom')
- Clears textarea after sending

### Technical Implementation

**CSS changes:**
- `.skills-panel` — new container with `flex-shrink: 0`, `max-height: 45vh`, `overflow-y: auto`
- `#ai-output-area` — new output container with `flex: 1`, `overflow-y: auto`
- `.custom-prompt-section` — new section with textarea + send button
- `.ai-output-empty` — placeholder state when no AI responses yet

**JavaScript changes:**
- `runSkillWithPrompt()` — now appends to `#ai-output-area` instead of `#skills-container`
- `applySkill()` — same output area change
- `sendCustomPrompt()` — new function, calls `runSkillWithPrompt()` with custom text
- Both functions remove `.ai-output-empty` placeholder before appending first bubble

**HTML changes:**
- Wrapped transcript + skills + custom prompt + history in `.skills-panel`
- Added `#ai-output-area` div below the panel
- Custom prompt section between skills and history

### User Impact

- **Less scrolling:** Controls always visible at top, output area scrolls independently
- **More flexibility:** Custom prompt allows any question without pre-defined skill
- **Better organization:** Clear separation between controls (sticky) and output (scrollable)

### Testing

- ✅ All 66 tests passing
- ✅ No regressions in existing functionality
- ✅ Skills load correctly in sticky panel
- ✅ AI bubbles append to output area correctly
- ✅ Scroll behavior works as expected

## Issue #18 — Transcript Input: Paste + File Upload

**Date:** 2026-05-09  
**Status:** ✅ Complete  
**Branch:** `squad/18-transcript-accordion`  
**Base:** `feat/issue-12-ai-editing`

### UI Components Built

1. **Transcript accordion** — collapsible panel in right pane, above skill buttons
   - Header: "📄 Transcript" with chevron toggle icon
   - Closed by default (max-height: 0)
   - Smooth CSS transition on expand/collapse (300ms ease-out)
   - Catppuccin surface0/surface1 background with border

2. **Textarea for transcript input** — `<textarea id="transcript-input">`
   - Monospace font, 180px min-height, vertical resize enabled
   - Placeholder instructions for paste and file formats
   - Auto-saves on blur event via `PUT /editing/drafts/<id>` with `transcript` field

3. **File upload input** — accepts `.txt`, `.srt`, `.vtt` files
   - Custom styled label button (no visible `<input>`)
   - Upload icon + "Upload File" text
   - On file selection, reads file as plain text via `file.text()`
   - Populates textarea with raw file content (no preprocessing)
   - Shows filename next to upload button after successful load

### Integration with Skills

- **`applySkill()` modified** — now includes `transcript_override: transcriptInput.value.trim() || null` in POST body to `/editing/stream`
- Backend (`editing_routes.py`) already handles `transcript_override` parameter and falls back to draft transcript
- Skills receive transcript if provided; otherwise they function normally (transcript fully optional)

### Persistence

- **On page load** — if `draft.transcript` is set, pre-populates `#transcript-input` via Jinja2 `{{ draft.transcript | tojson }}`
- **Auto-save on blur** — `transcriptInput.addEventListener('blur', ...)` → calls `saveTranscript()` → `PUT /editing/drafts/<id>` with `{content, transcript}`
- **Manual file upload** — also triggers auto-save after reading file content

### Backend Verification

- ✅ `db_service.py`: `drafts` table has `transcript` column
- ✅ `db_service.update_draft()`: accepts and persists `transcript` parameter
- ✅ `db_service.get_draft()`: returns `transcript` field
- ✅ `editing_routes.py PUT /editing/drafts/<id>`: accepts `transcript` from body and passes to `update_draft()`
- ✅ `editing_routes.py POST /editing/stream`: reads `transcript_override` and uses it or falls back to draft transcript

### CSS Additions

All styles added inline in `editor.html`:
- `.transcript-accordion`, `.transcript-header`, `.transcript-body` — accordion structure
- `.transcript-toggle` with `.expanded` state — chevron rotation animation
- `.transcript-content` — 16px padding, flex column gap
- `#transcript-input` — monospace textarea with blue focus border
- `.file-input-wrapper`, `.file-input-label` — styled file upload button
- `#transcript-file` — hidden native input
- `.file-name` — small gray text showing selected filename

### Technical Decisions

- **No .srt/.vtt parsing on frontend** — raw file content sent to backend; AI skill prompt handles timing metadata if needed
- **Auto-save on blur** — saves both `content` and `transcript` in single PUT request (prevents partial saves)
- **Accordion starts closed** — reduces visual noise; transcript is optional feature
- **Trim before sending** — `transcriptInput.value.trim() || null` ensures empty string → null (not sent to backend)
- **File read as text** — `file.text()` API, not FileReader callback pattern (cleaner async/await)

### Code Organization

All functionality inline in `editor.html`:
- `toggleTranscript()` — accordion expand/collapse toggle
- `saveTranscript()` — async PUT with content + transcript
- File input change handler — reads file, populates textarea, auto-saves
- `applySkill()` modified — adds `transcript_override` to POST body
- Initialization block — restores saved transcript on page load

## 2025-05-10 — Issue #19: Parameterized Skill Modal

**Branch**: `squad/19-skill-modal`  
**PR**: #45  
**Base**: `feat/issue-12-ai-editing`

### Implementation
- Updated `skills/text-editor/SKILL.md` with 5 modes (Full Edit, Quick Pass, Rewrite Section with parameters, Tone Check, Headline Workshop)
- Enhanced `skills_service.py` to parse YAML properly using pyyaml, return modes/parameters in `list_skills()`, added `get_skill_data()` function
- Updated `editing_routes.py` to return full skill data from `/editing/skill/<name>` and accept `system_prompt_override` in `/editing/stream`
- Rewrote skill rendering in `templates/editor.html`:
  - Skills with modes render as skill cards with sub-buttons
  - Skills with parameters trigger a `<dialog>` modal
  - Modal collects input, interpolates into prompt, sends to stream with override
  - Added Catppuccin Mocha-themed CSS for modal and skill cards
- Added `pyyaml>=6.0` to `requirements.txt`

### Git Persistence Fix
Encountered WSL file persistence issue — edits via `edit` tool were lost after branch switch. Solution: used bash heredocs to write files directly, ensuring disk persistence before committing.

### Testing
Manual UI flow testing completed:
- ✅ text-editor renders 5 sub-buttons
- ✅ "Rewrite Section" opens modal with input field
- ✅ Modal interpolates parameters into prompt
- ✅ Cancel button closes modal without API call
- ✅ Non-parameterized modes run directly

Automated pytest blocked by Python environment issues in WSL (missing venv packages).
