# Team Decisions Log

## 2026-05-07: Team Expanded for Gemini Migration

**Date:** 2026-05-07  
**By:** Hicks (on behalf of fboucher)  
**Status:** Active

### What
Hired two new team members to handle Gemini migration (issues #22–#28):
- **Ripley** — Backend Developer (Python, Flask, Gemini API, SQLite)
- **Hudson** — Frontend Developer (HTML/Jinja2, CSS, JavaScript, UI)

### Why
The existing team (Hicks, Vasquez, Bishop) was built for Docker optimization and lacks backend implementation capacity. Gemini migration requires:
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
3. Hicks approves architecture/scope changes
4. Bishop sets test coverage gates

### Implementation Notes
- Onboarding files created: `.squad/agents/ripley/{charter,history}.md`, `.squad/agents/hudson/{charter,history}.md`
- Team registry updated in `.squad/casting/registry.json`
- Routing document updated: `.squad/routing.md`
- Team manifest updated: `.squad/team.md`
