# video2blog Routing & Ownership

## Request Routing by Domain

### Backend / Python / Flask / API
**Owner:** Ripley  
**Context:** `.squad/agents/ripley/charter.md` + `.squad/agents/ripley/history.md`

**Covered:**
- Python code changes, Flask routes, request handling
- Google Gemini API integration, prompts, API calls
- SQLite database schema, queries, migrations
- File caching, video processing, yt-dlp integration
- `web_app.py`, `db_service.py`, `gemini_service.py`, `keyframe_extractor.py`
- `requirements.txt` (Python dependencies)
- Issues #22, #23, #24, #25, #26, #27, #28 (backend scope)

**Defer to:**
- Hudson: Template changes, HTML structure, CSS, JavaScript
- Bishop: Test strategy, test data, coverage expectations
- Vasquez: Docker image, deployment pipeline

---

### Frontend / UI / Templates / JavaScript / CSS
**Owner:** Hudson  
**Context:** `.squad/agents/hudson/charter.md` + `.squad/agents/hudson/history.md`

**Covered:**
- Jinja2 templates in `templates/`
- CSS in `static/css/`
- JavaScript in `static/js/`
- HTML forms, UI components, interactive elements
- AJAX/fetch calls to Flask endpoints
- Issues #23 (library status UI), #26 (URL Q&A UI)

**Defer to:**
- Ripley: Flask routes, API response contracts, backend logic
- Bishop: UI test coverage expectations
- Vasquez: Deployment, Docker config

---

### Infrastructure / Docker / Deployments
**Owner:** Vasquez  
**Context:** `.squad/agents/vasquez/charter.md` + `.squad/agents/vasquez/history.md`

**Covered:**
- `Dockerfile` configuration, image optimization, layer analysis
- `docker-compose.yml`, container networking
- Dependency installation (pip, system packages)
- Issue #28 (Dockerfile + README updates for Gemini migration)

**Defer to:**
- Ripley: Python dependencies in `requirements.txt`
- Hudson: Static assets, template compilation
- Hicks: Architecture decisions affecting infrastructure

---

### QA / Testing / Coverage
**Owner:** Bishop  
**Context:** `.squad/agents/bishop/charter.md` + `.squad/agents/bishop/history.md`

**Covered:**
- Test strategy, test data fixtures
- Automated test coverage expectations
- Test coverage gates before merge
- Regression testing across Gemini migration

**Collaborate with:**
- Ripley: Backend test coverage, API endpoint tests
- Hudson: UI test coverage, template rendering tests
- Vasquez: Infrastructure tests, Docker image tests

---

## Decision Making & Escalation

| Issue Type | Decision Owner | Collaborators |
|-----------|---|---|
| API contract changes | Ripley + Hudson sync | Hicks (scope) |
| Database schema | Ripley | Hicks (approval) |
| UI/UX changes | Hudson | Ripley (API impact) |
| Deployment/Docker | Vasquez | Hicks (approval) |
| Test coverage | Bishop | Ripley + Hudson (expectations) |
| Architecture | Hicks | All (consultation) |

## Communication Norms
- Ripley & Hudson: Sync on API contracts before implementation
- All team members: Read decisions/inbox before starting work
- Async-first: Document decisions in decisions/inbox before action
- Escalations to Hicks: Use for scope, architecture, or cross-team conflicts
