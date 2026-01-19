## Backend (FastAPI)

### Run (Windows PowerShell)

```powershell
cd backend
# 1) Create a local virtualenv
uv venv

# 2) Install deps from pyproject.toml into .venv
uv sync

# 3) Run the API (reload for dev)
uv run uvicorn app.main:app --reload --port 8000
```

### Endpoints

- `GET /api/health` -> `{ "status": "ok" }`
- `POST /api/transcribe` -> `{ "transcript": "<same text>" }` (placeholder)

