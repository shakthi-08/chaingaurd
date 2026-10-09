from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

from app.api.routes import router as case_router
from app.api.integrations import router as integration_router
from app.config import is_demo_mode_enabled, is_real_mode_enabled, settings
from app.database import init_db
from app.schemas.health import HealthResponse
from app.services.demo_case_seeder import seed_demo_case
from app.services.protocol_registry import ARCHITECTURAL_CHAINS, OPERATIONAL_CHAINS
from app.services.demo_event_provider import DemoEventProvider
from app.services.event_processing_service import EventProcessingService

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ChainGuard investigation-intelligence foundation for crypto-fraud attribution workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(case_router, prefix=settings.api_prefix)
app.include_router(case_router)
app.include_router(integration_router, prefix=settings.api_prefix)
app.include_router(integration_router)


@app.websocket("/cases/{case_id}/events")
async def case_events(websocket: WebSocket, case_id: str) -> None:
    await websocket.accept()
    if is_real_mode_enabled():
        await websocket.send_json({"error": "Real mode does not stream demo events.", "source": "REAL_MODE"})
        await websocket.close(code=1008)
        return

    provider = DemoEventProvider()
    processor = EventProcessingService()
    try:
        for event in provider.get_events(case_id):
            processed = processor.process(event)
            await websocket.send_text(json.dumps(processed.to_dict()))
        await websocket.close(code=1000)
    except (ValueError, WebSocketDisconnect) as exc:
        if isinstance(exc, ValueError):
            await websocket.send_json({"error": str(exc), "source": "SYNTHETIC_DEMO"})
            await websocket.close(code=1008)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    if is_demo_mode_enabled() and not is_real_mode_enabled():
        seed_demo_case()


def _health_payload() -> HealthResponse:
    provider = (settings.ai_provider or "none").strip().lower() or "none"
    model = (settings.ai_model or "").strip() or None
    has_key = bool((settings.ai_api_key or "").strip())
    ai_configured = (
        (provider in {"openai", "gemini", "google"} and has_key)
        or (provider in {"ollama", "local", "openai-compatible"} and bool(model or provider == "ollama"))
    )
    if provider in {"", "none", "unavailable", "off"}:
        ai_configured = False
        display_model = None
    elif provider == "openai":
        display_model = model or "gpt-4o-mini"
    elif provider in {"gemini", "google"}:
        display_model = model or "gemini-2.5-flash"
    elif provider in {"ollama", "local"}:
        display_model = model or "llama3.2"
    else:
        display_model = model

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        blockchain_provider=settings.blockchain_provider,
        demo_mode=is_demo_mode_enabled() and not is_real_mode_enabled(),
        real_mode=is_real_mode_enabled(),
        operational_chains=list(OPERATIONAL_CHAINS),
        architectural_chains=list(ARCHITECTURAL_CHAINS),
        ai_provider=provider,
        ai_configured=ai_configured,
        ai_model=display_model if ai_configured else None,
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return _health_payload()


@app.get("/api/health", response_model=HealthResponse)
def api_health_check() -> HealthResponse:
    return _health_payload()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "message": "ChainGuard backend is running.",
    }
