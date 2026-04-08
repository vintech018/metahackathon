---
title: VulnArena AI
emoji: 🛡️
colorFrom: gray
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# VulnArena AI

VulnArena AI is a hackathon demo for interactive vulnerability triage. The app
combines a React frontend with a Python backend that simulates a multi-step
security analysis pipeline across bug reports, logs, and code snippets.

## What the demo includes

- Interactive VulnArena pipeline with isolated browser sessions
- Deterministic fallback mode when no external model credentials are configured
- Optional OpenAI-compatible triage endpoints for richer report scoring
- Docker-based deployment for Hugging Face Spaces

## Hugging Face Space deployment

This repository is configured as a Docker Space.

Optional secrets for live model-backed behavior:

- `API_KEY`
- `API_BASE_URL`
- `MODEL_NAME`

If those secrets are omitted, the Space still boots and runs in heuristic
fallback mode so the hackathon demo remains usable.

## Local development

Backend:

```bash
pip install -r requirements.txt
python backend.py --port 5001
```

Frontend dev server:

```bash
cd frontend
npm ci
npm run dev
```

Production-style frontend build:

```bash
cd frontend
npm ci
npm run build
```

## API surface

- `GET /api/health`
- `GET /api/tasks`
- `POST /reset`
- `POST /step`
- `GET /state`

The public triage endpoints can be enabled explicitly with
`ENABLE_PUBLIC_TRIAGE_API=true`.
