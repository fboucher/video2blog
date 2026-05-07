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
