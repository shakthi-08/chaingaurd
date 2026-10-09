from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.lea_complaint_service import INTEGRATION_DISCLAIMER, LeaComplaintService
from app.services.protocol_registry import ARCHITECTURAL_CHAINS, OPERATIONAL_CHAINS

router = APIRouter(prefix="/integrations", tags=["integrations"])


class ComplaintIntakeRequest(BaseModel):
    complaint_id: str = Field(..., min_length=1, max_length=128)
    wallet_address: str = Field(..., min_length=1, max_length=255)
    blockchain: str = Field(default="ethereum", min_length=1, max_length=64)
    incident_type: str | None = Field(default=None, max_length=128)
    reported_timestamp: datetime | None = None
    investigation_id: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default="accepted", max_length=64)


@router.get("/capabilities")
def integration_capabilities():
    return {
        "live_integration": False,
        "integration": INTEGRATION_DISCLAIMER,
        "operational_chains": list(OPERATIONAL_CHAINS),
        "architectural_chains": list(ARCHITECTURAL_CHAINS),
        "complaint_fields": [
            "complaint_id",
            "wallet_address",
            "blockchain",
            "incident_type",
            "reported_timestamp",
            "investigation_id",
            "status",
        ],
    }


@router.post("/ncrp/complaints")
def accept_complaint(payload: ComplaintIntakeRequest):
    try:
        return LeaComplaintService().accept(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ncrp/complaints/{complaint_id}")
def get_complaint(complaint_id: str):
    try:
        return LeaComplaintService().get(complaint_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
