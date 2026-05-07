# UI Decision: URL Video Q&A Messaging — Issue #26

**From:** Hudson (Frontend)  
**To:** Liz (Architect), Ripley (Backend)  
**Date:** 2026-05-07  
**Status:** Decision Made

---

## Question

How should we signal to users that URL-based videos are Q&A-ready but frame extraction requires download?

---

## Constraints

- No local file exists (pseudo-filename only: `url-<hash>`)
- Q&A capability available immediately
- Frame extraction deferred to issue #27 (yt-dlp integration)
- Must not confuse users with Reka terminology
- Mobile-friendly design

---

## Options Considered

### Option A: Disable extraction button, show disabled state
**Approach:** Disable extract button entirely; show tooltip on hover  
**Pros:** Clean, uncluttered UI; button visually distinct  
**Cons:** Users may not understand why it's disabled without hovering  
**Decision:** ❌ Not chosen (tooltip-only is not discoverable)

### Option B: Separate CTA section + inline messaging
**Approach:** Hide normal params; show dedicated info box with message + disabled button  
**Pros:** Clear separation of concerns; dedicated space for explanation  
**Cons:** More DOM changes; requires conditional rendering  
**Decision:** ✅ **CHOSEN** — Best UX clarity

### Option C: Badge only, no messaging
**Approach:** Just add "URL video" badge; rely on badge label  
**Pros:** Minimal UI changes  
**Cons:** Unclear what "Q&A-ready" means; users confused about extraction  
**Decision:** ❌ Not chosen (insufficient guidance)

---

## Decision

**Implement Option B:** Separate messaging + disabled button stub

### Details

1. **URL Video Badge**
   - Location: Video library list (next to status badge)
   - Appearance: "🌐 URL video — Q&A ready" (lavender badge)
   - Tooltip: Explains Q&A-ready + frame extraction behavior

2. **Q&A-Only Messaging**
   - Location: Chat welcome section (replaces generic "Ask me anything")
   - Format: `<h4>💡 This video is Q&A-ready</h4><p>Frame extraction will download the video when triggered...</p>`
   - Timing: Shown when URL video is selected

3. **Frame Extraction CTA**
   - Location: Step 3 params section
   - State: Disabled button with explanatory title
   - Label: "Extract Frames (downloads video)"
   - Behavior: Toast message on click → "Frame extraction coming soon..."
   - Future: Issue #27 will implement actual yt-dlp extraction

4. **Color Scheme**
   - Badge color: Lavender (`#b4befe`) — distinct from other source types
   - Message box: Blue background with lavender border (matches Q&A theme)

---

## Rationale

- **Clarity:** Three-part messaging (badge + info box + disabled CTA) ensures users understand video state
- **Progressive disclosure:** Users learn about Q&A first, extraction limitations as they explore
- **Accessibility:** Disabled button + title attribute + toast provide multiple cues
- **Consistency:** Reuses existing badge system and message styling
- **Deferability:** Clear stub allows issue #27 to implement extraction without changing UI structure

---

## Implementation

- ✅ `templates/index.html` — Button label change
- ✅ `static/js/app.js` — Conditional rendering logic
  - `displayUnifiedVideoList()` → Render URL badge
  - `selectVideo()` → Show message box + disable button
  - `handleExtraction()` → Toast for stub
- ✅ `static/css/style.css` → Badge-lavender + message box styling

---

## Follow-up

**Issue #27** will:
1. Replace disabled button with yt-dlp extraction UI
2. Implement actual video download + frame extraction
3. No changes needed to messaging/badge system
