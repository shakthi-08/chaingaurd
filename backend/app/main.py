from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

from app.api.routes import router as case_router
from app.config import settings
from app.database import init_db
from app.schemas.health import HealthResponse
from app.services.demo_case_seeder import seed_demo_case
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


@app.websocket("/cases/{case_id}/events")
async def case_events(websocket: WebSocket, case_id: str) -> None:
    await websocket.accept()
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
    if settings.demo_mode or settings.environment.lower() == "demo":
        seed_demo_case()


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "message": "ChainGuard backend is running.",
    }
