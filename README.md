# Video 2 Blog

[![Build and Push Docker Image](https://github.com/fboucher/video2blog/actions/workflows/docker-build.yml/badge.svg?branch=main)](https://github.com/fboucher/video2blog/actions/workflows/docker-build.yml) ![GitHub License](https://img.shields.io/github/license/fboucher/video2blog) ![Vision AI · Gemini](https://img.shields.io/badge/Vision%20AI-Gemini-blue?logo=google) ![OpenAI API Compatible](https://img.shields.io/badge/OpenAI%20API-Compatible-412991?logo=openai)

Transform videos into blog posts with AI. Upload a video, generate a draft with Gemini, refine it in the **AI Blog Editor**, and extract keyframes to illustrate your post.

---

## Quick Start

```bash
docker compose up -d
```

Open [http://localhost:5123](http://localhost:5123).

See [docs/](docs/index.md) for the full workflow guide.  
To run without Docker, see the [Development guide](docs/development.md#local-setup-without-docker).

## Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
EDITING_PROVIDER=anthropic          # anthropic or openai
EDITING_API_KEY=your_api_key
EDITING_MODEL=claude-sonnet-4-6     # optional, provider default if omitted
EDITING_BASE_URL=                   # optional, for custom OpenAI-compatible endpoints
SKILLS_FOLDER=./skills              # optional, default ./skills
```

## Workflow

| Step | What happens |
|------|-------------|
| 1 — Upload | Upload a local video or paste a YouTube URL |
| 2 — Chat | Gemini analyzes the video and generates a blog draft |
| 3 — Extract | Select keyframes to extract; configure frames per timestamp |
| 4 — Edit | Refine the draft with AI-powered skills in the editor |

See [docs/workflow.md](docs/workflow.md) for details.

## Documentation

| Guide | Description |
|-------|-------------|
| [Workflow](docs/workflow.md) | Full walkthrough of all four steps |
| [Skills](docs/skills.md) | Write custom AI editing skills |
| [Development](docs/development.md) | Local setup, testing, project structure |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — bug reports, feature requests, and custom skills are all welcome.

## Resources

- [Google Gemini API](https://ai.google.dev/) — Get an API key at Google AI Studio
- [Anthropic Claude API](https://www.anthropic.com/api) — Get an API key from Anthropic
- [OpenAI API](https://platform.openai.com/api/keys) — Get an API key from OpenAI
