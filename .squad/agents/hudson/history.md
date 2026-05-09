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
