# Development Guide

## Local Setup

```bash
# Clone and enter the repo
git clone https://github.com/fboucher/video2blog.git
cd video2blog

# Copy environment file
cp .env.example .env
# Fill in your API keys

# Run with Docker Compose
docker compose up --build
```

The app is available at [http://localhost:5123](http://localhost:5123).

## Running Tests

```bash
python -m pytest tests/ -q
```

All PRs must pass the existing test suite before merging.

## Project Structure

```
video2blog/
├── video2blog/             # Python package (source code)
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point for keyframe extraction
│   ├── keyframe_extractor.py   # Keyframe extraction library
│   ├── web_app.py              # Flask web application (routes, endpoints)
│   ├── db_service.py           # SQLite database service
│   ├── gemini_service.py       # Google Gemini API integration
│   ├── editing_service.py      # AI editing provider abstraction
│   ├── editing_routes.py       # Editor API routes
│   └── skills_service.py       # Skills loading and execution
├── templates/              # Jinja2 HTML templates
│   ├── index.html
│   ├── editor.html
│   └── settings.html
├── static/                 # Frontend assets
│   ├── css/style.css
│   └── js/app.js
├── skills/                 # User-defined AI editing skills
│   └── <skill-name>/SKILL.md
├── tests/                  # Python test suite
├── docs/                   # Documentation
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Code Style

- Python: follow PEP 8, use type hints where practical
- Keep functions small and focused
- Comment only where clarification is needed
- Prefer pathlib over os.path for file operations

## Pull Request Guidelines

1. Branch from `dev`, not `main`
2. Keep PRs focused — one feature or fix per PR
3. Write clear commit messages — describe what and why
4. Add tests for any new behaviour
5. Update documentation if your change affects usage or configuration

## Adding a Custom Skill

See [docs/skills.md](skills.md) for the full guide.

Quick start — create a folder and SKILL.md:

```
skills/
└── your-skill-name/
    └── SKILL.md
```

```markdown
---
name: Your Skill Name
description: One-line description shown in the UI
---

Your system prompt here.
```
