# CatGPT Gateway

Turn your ChatGPT or Claude browser session into a fully working OpenAI-compatible API, with a real-time Next.js dashboard.

## Architecture

| Service | Port | Command |
|---|---|---|
| Python API gateway | 8000 | `python -m src.api.server` |
| Next.js dashboard | 5000 | `cd dashboard && npm run dev` |

The dashboard proxies `/api/*`, `/v1/*`, and `/status` to the backend on port 8000 via Next.js rewrites.

## Quick Start

1. Copy `.env.example` to `.env` and set your `PROVIDER` and `API_TOKEN`
2. Start the API: workflow **"API Gateway"**
3. Start the dashboard: workflow **"Dashboard"**
4. Open the preview on port 5000

## API Usage

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy123")
response = client.chat.completions.create(
    model="catgpt-browser",  # or "claude-browser"
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## User Preferences

- Dark mode dashboard by default
- Python venv at `.venv/` (created by uv)
- Node modules at `dashboard/node_modules/`
- Dashboard uses Next.js 14 + Tailwind + shadcn-style components
