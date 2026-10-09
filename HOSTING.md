# ChainGuard hosting

## Local

Backend:

```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173

## Required environment variables

### Backend (`backend/.env`)

- `BLOCKCHAIN_PROVIDER=real` or `demo`
- `ETHERSCAN_API_KEY` (required for real Ethereum)
- `POLYGONSCAN_API_KEY` (required for real Polygon)
- `DEMO_MODE=false` for real investigations
- `DATABASE_URL=sqlite:///./chainguard.db`
- `AI_PROVIDER=none` or `openai` / `ollama`
- `AI_MODEL`, `AI_API_KEY`, `AI_BASE_URL` only if AI is enabled
- `CORS_ORIGINS` comma-separated frontend origins
- `CORS_ORIGIN_REGEX` optional Vercel preview regex

### Frontend (Vercel project env)

- `VITE_API_BASE=https://<backend-host>` (no trailing slash)
- `VITE_WS_BASE=wss://<backend-host>` only if you want demo event streaming

Do not set `VITE_WS_BASE` for real-mode investigations. Live events are demo-only.

Health checks: `GET /health` and `GET /api/health`

Never commit API keys. `.env` is gitignored.
