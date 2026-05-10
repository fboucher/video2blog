# Liz — History

## Project Context
- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV, numpy, Google Gemini API, SQLite
- **User:** fboucher
- **Mission:** Migrate from Reka to Gemini (issues #22–#28)
- **Base branch:** dev
- **Feature branches:** squad/22 through squad/28 (all branched from dev)

## Issue Map
- #22: Gemini service + DB schema foundation (FOUNDATION — others depend on this)
- #23: Local video upload with Gemini file caching + library status UI
- #24: Q&A on local videos via Gemini
- #25: Blog generation with Gemini-suggested timestamps
- #26: URL video Q&A without download
- #27: URL video frame extraction via yt-dlp
- #28: Reka removal, sanitize_filename cleanup, Dockerfile + README update

## Team
- Ripley: Backend Developer — owns all Python/Flask implementation
- Hudson: Frontend Developer — owns templates/JS/CSS
- Vasquez: DevOps — owns Dockerfile (#28)
- Bishop: Tester/QA — owns test coverage

## Learnings

### 2026-05-10: Dead Code Audit — feat/issue-12-ai-editing

**Context:** Frank requested cleanup of unused files, folders, and dead code before finalizing the AI editing feature branch.

**Findings and Actions:**

1. **Deleted `=1.0.0`** — Pip error artifact (externally-managed-environment error text) that was somehow tracked. Not used anywhere.

2. **Deleted `.skills/` directory** — Duplicate of `skills/` directory. The app uses `skills_service.py` which defaults to `./skills` (not `.skills`). Both directories contained identical `edit-video-blog/` and `text-editor/` subdirectories with matching SKILL.md files.

3. **No dead templates** — Both `templates/index.html` and `templates/editor.html` are actively rendered via `web_app.py` and `editing_routes.py`.

4. **No dead Python code** — All functions in `keyframe_extractor.py`, `gemini_service.py`, `editing_service.py`, and `editing_routes.py` are actively used.

5. **Reka references** — Only exist in migration code (`db_service.py` line 32-34 for schema migration detection) and tests (`test_db_service.py` for schema validation). No active Reka imports or API calls.

6. **data/ folder** — Contains runtime `video_sync.db`. Already properly gitignored via `.gitignore` entries: `data/` and `*.db`.

7. **assets/ folder** — Contains screenshots referenced in README.md. Kept as documented.

8. **No dead CSS/JS** — No obvious Reka-prefixed classes or stale modal code found. CSS is clean for Catppuccin Mocha theme.

**Test Results:** 66 passed, 1 skipped — no regressions.

**Commit:** `1d9415d` - "chore: remove dead code - =1.0.0 pip artifact and .skills/ duplicate"
