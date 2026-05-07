# Decision: PR #32 Review — Blog Generation with Gemini Timestamps

**Date:** 2026-05-07  
**By:** Liz (Lead/Architect)  
**PR:** #32 (closes #25)  
**Author:** Ripley  
**Status:** APPROVED

## Verdict

**APPROVED** — All five acceptance criteria met. Architecture is clean and follows established patterns.

## Acceptance Criteria Assessment

| Criterion | Status |
|---|---|
| Blog generation calls Gemini and returns a blog draft | ✅ `gemini_service.generate_blog()` returns `{draft, timestamps}` |
| Gemini-suggested timestamps used for frame extraction | ✅ Timestamps passed to `extract_frames_at_timestamps()` |
| Scene detection fallback when timestamps empty | ✅ `extract_keyframes()` called when `timestamps` is falsy |
| Generated frames appear in output alongside blog draft | ✅ Response includes `frames` list + `blog` field |
| Old Reka blog generation route/logic removed | ✅ `/reka/ask` route replaced by `/gemini/generate-blog` |

## Review Notes

### Strengths

1. **Prompt design is solid.** Requesting raw JSON (no code fences) with a code-fence stripping fallback is a pragmatic two-layer defense against Gemini's formatting variability.
2. **`_resolve_gemini_uri()` reused correctly** — same helper used by the Q&A route at line 1106. No duplication.
3. **`_gemini_cache_status()` extracted cleanly** — single definition at line 98, reused in `_resolve_gemini_uri()`.
4. **Fallback path is clearly conditional.** `if timestamps:` → Gemini timestamps; `else:` → scene detection. Easy to read.
5. **Return shape** `{blog, frames, source, gemini_cache_status}` gives the UI all it needs: the draft, frame filenames, how frames were selected, and cache freshness.
6. **`/upload-from-url` rewrite** correctly replaces Reka with Gemini URL refs and uses `db_service.get_video_by_url()` for idempotency.

### Minor Observations (Non-blocking)

1. **Response key mismatch (cosmetic):** `generate_blog()` returns `draft` but the route serializes it as `blog` (`'blog': draft`). This works fine for the UI but the naming inconsistency between service and route is worth noting. Not blocking — the UI contract uses `blog` and that's what matters.
2. **Reka remnants remain** in other routes (upload, list, delete, status check). These are explicitly scoped to #28 per the issue map, so not a concern for this PR.
3. **`reka_service` import still present** at line 18. Also scoped to #28 for full removal.
4. **Test covers the fallback path only** (plain text → empty timestamps). A test for the happy path (valid JSON with timestamps) would strengthen coverage. Non-blocking — Bishop can add this in #25's test pass.

## Implications for Downstream Issues

- **#27 (URL video frame extraction):** Can reuse `_resolve_gemini_uri()` and the timestamp-vs-fallback pattern directly.
- **#28 (Reka removal):** Must remove `import reka_service` and all remaining Reka routes/references.
