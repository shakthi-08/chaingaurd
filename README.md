# ChainGuard

ChainGuard is a synthetic-data-first investigation intelligence demo for
crypto-fraud analysis. It organizes normalized transactions, graph paths,
deterministic risk indicators, attribution hypotheses, evidence, reports,
AI explanations, cross-chain correlations, and real-time demo events.

This is a hackathon/demo application, not a production system. Synthetic
wallets, transactions, entities, bridge events, and AI responses must not be
presented as real-world investigative evidence. Attribution is a hypothesis;
blockchain analysis alone does not prove ownership or criminal activity.

## Architecture

```text
React + TypeScript + Vite dashboard
								|
						 FastAPI
								|
			Investigation services
								|
			 SQLAlchemy + SQLite
```

- Ingestion uses a provider abstraction and deterministic Ethereum/Polygon
  demo providers.
- The graph engine turns normalized transactions into directed wallet edges
  and bounded multi-hop paths.
- The risk engine applies deterministic, explainable fraud-pattern rules.
- Attribution compares wallets with a clearly synthetic entity/VASP dataset.
- Evidence collection creates deterministic, deduplicated references for
  transactions, paths, findings, indicators, relationships, and hypotheses.
- ReportLab generates investigator-ready PDF reports.
- The AI layer is read-only, context-grounded, provider-configurable, and
  explicitly unavailable when no provider is configured.
- Cross-chain correlation is limited to deterministic synthetic bridge data.
- A WebSocket streams deterministic demo events to the dashboard.

## Requirements

- Python 3.12+
- Node.js 20+
- npm

## Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
cd ..\frontend
npm ci
```

Never put real credentials in `.env.example`, source files, or commits.

## Demo mode

Set these values in `backend/.env`:

```text
ENVIRONMENT=demo
DEMO_MODE=true
DATABASE_URL=sqlite:///./chainguard.db
AI_PROVIDER=none
EVENT_PROVIDER=demo
```

Demo seeding is deterministic, idempotent, and does not overwrite an
existing `CASE-DEMO-001` case.

Start the backend in one terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. The dashboard loads `CASE-DEMO-001` and marks
the investigation as `DEMO / SYNTHETIC DATA`.

## APIs

All case routes use `/cases/{case_id}`.

- `GET /health`
- `POST /cases/{case_id}/wallets`
- `GET /cases/{case_id}/transactions`
- `GET /cases/{case_id}/graph`
- `GET /cases/{case_id}/paths?start_wallet=...`
- `GET /cases/{case_id}/risk`
- `POST /cases/{case_id}/analyze`
- `GET /cases/{case_id}/attributions`
- `GET /cases/{case_id}/evidence`
- `POST /cases/{case_id}/evidence`
- `POST /cases/{case_id}/report`
- `GET /cases/{case_id}/reports`
- `POST /cases/{case_id}/ai/summary`
- `POST /cases/{case_id}/ai/explain-path`
- `POST /cases/{case_id}/ai/explain-risk`
- `POST /cases/{case_id}/ai/explain-attribution`
- `POST /cases/{case_id}/ai/next-steps`
- `GET /cases/{case_id}/cross-chain`
- WebSocket `/cases/{case_id}/events`

There is intentionally no `/timeline` endpoint. The dashboard derives its
timeline from the transaction endpoint.

## Tests and builds

Backend tests:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

Frontend tests and production build:

```powershell
cd frontend
npm test -- --run
npm run build
```

## Demo report

With the backend running in demo mode, generate a real PDF from PowerShell:

```powershell
Invoke-WebRequest -Method Post `
	-Uri http://localhost:8000/cases/CASE-DEMO-001/report `
	-OutFile .\demo-report.pdf
```

The response is an actual PDF. Generated reports are local runtime artifacts
and are ignored by Git.

## Scope and limitations

This repository intentionally does not implement real blockchain providers,
real bridge APIs, production-scale event infrastructure, cross-chain
correlation beyond the synthetic demo workflow, ML, autonomous investigator
actions, or production readiness guarantees.
