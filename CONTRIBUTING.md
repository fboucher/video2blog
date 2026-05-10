# Contributing to video2blog

Thanks for your interest in contributing! All contributions are welcome — bug fixes, features, documentation, and new skills.

## Ways to Contribute

- **Report a bug** — [Open an issue](https://github.com/fboucher/video2blog/issues/new)
- **Request a feature** — [Start a discussion](https://github.com/fboucher/video2blog/discussions)
- **Chat with us** — Join the [Discord server](https://discord.gg/6zA3jKw)
- **Submit a pull request** — Fork the repo and open a PR against `dev`

## Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/fboucher/video2blog.git
cd video2blog

# Copy and fill in your environment variables
cp .env.example .env

# Run with Docker Compose
docker compose up --build
```

## Running Tests

```bash
python -m pytest tests/ -q
```

All PRs must pass the existing test suite before merging.

## Pull Request Guidelines

1. **Branch from `dev`** — not from `main`
2. **Keep PRs focused** — one feature or fix per PR
3. **Write clear commit messages** — describe what and why
4. **Add tests** for any new behaviour
5. **Update documentation** if your change affects usage or configuration

## Adding a Custom Skill

Skills are the easiest way to contribute! A skill is just a Markdown file:

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

Your system prompt here. This is sent to the AI when a user applies this skill.
```

See the built-in skills in `skills/` for examples.

## Code Style

- Python: follow PEP 8, use type hints where practical
- Keep functions small and focused
- Comment only where clarification is needed

## Questions?

Open an issue, start a discussion, or drop by the [Discord](https://discord.gg/6zA3jKw).
