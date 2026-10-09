from __future__ import annotations

from typing import Any

from app.database import SessionLocal
from app.models import Case

# Deterministic investigation stages for the local prototype.
STAGE_PROGRESS: dict[str, int] = {
    "CREATED": 0,
    "INGESTING": 10,
    "INGESTED": 25,
    "ANALYZING": 30,
    "GRAPH_READY": 50,
    "RISK_READY": 65,
    "ATTRIBUTION_READY": 80,
    "AI_READY": 90,
    "REPORT_READY": 95,
    "COMPLETED": 100,
    "FAILED": 0,
}


def set_case_stage(
    case_id: str,
    stage: str,
    *,
    error: str | None = None,
    session_factory=SessionLocal,
) -> dict[str, Any]:
    progress = STAGE_PROGRESS.get(stage, 0)
    with session_factory() as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            return {"case_id": case_id, "status": "FAILED", "progress": 0, "current_stage": "FAILED", "error": "Case not found."}
        case.current_stage = stage
        case.progress = progress if stage != "FAILED" else case.progress
        case.error_message = error
        if stage == "FAILED":
            case.status = "FAILED"
        elif stage == "COMPLETED":
            case.status = "COMPLETED"
        elif stage in {"CREATED", "INGESTING", "INGESTED", "ANALYZING"}:
            case.status = "open"
        else:
            case.status = stage
        session.commit()
        return serialize_case_status(case)


def serialize_case_status(case: Case) -> dict[str, Any]:
    stage = case.current_stage or "CREATED"
    return {
        "case_id": case.case_id,
        "status": case.status,
        "progress": int(case.progress or STAGE_PROGRESS.get(stage, 0)),
        "current_stage": stage,
        "error": case.error_message,
    }


def get_case_status(case_id: str, session_factory=SessionLocal) -> dict[str, Any]:
    with session_factory() as session:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            return {
                "case_id": case_id,
                "status": "FAILED",
                "progress": 0,
                "current_stage": "FAILED",
                "error": "Case not found.",
            }
        return serialize_case_status(case)
