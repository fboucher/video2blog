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
- **`gemini_service.py`** — Google Gemini API wrapper (TO BE CREATED in #22)
- **`reka_service.py`** — Legacy Reka service (TO BE REPLACED)
- **`keyframe_extractor.py`** — Video frame extraction utilities
- **`requirements.txt`** — Python dependencies
- **`Dockerfile`** — Container config (Vasquez owns)
- **`templates/`** — Jinja2 templates (Hudson owns)
- **`static/`** — CSS, JavaScript (Hudson owns)

### Issue Map & Scope

| Issue | Title | Ripley Scope |
|-------|-------|--------------|
| #22 | Gemini service foundation | Create `gemini_service.py`, update DB schema for file caching |
| #23 | Local video upload + file caching | Implement upload endpoint, Gemini file cache logic |
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

## Database Schema (v2)
- Videos table: id, filename, source (local/url), gemini_file_id, created_at
- Conversations table: id, video_id, user_message, gemini_response, timestamp
- Caches table: file_hash, gemini_file_id, expires_at (for file cache expiry)

## Known Patterns
- Flask routes use `request.get_json()` for input validation
- `db_service.py` functions are atomic (rollback on error)
- Video processing catches exceptions and logs clearly
- All file operations sanitize filenames (`sanitize_filename()` in #28)

## Learnings
- Initial setup complete. Ready for issue #22 implementation.
