from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import SessionLocal
from app.models import Case
from app.models.lea_complaint_model import LeaComplaint


INTEGRATION_DISCLAIMER = (
    "NCRP/SAHYOG integration-ready architecture. This endpoint accepts complaint metadata "
    "so an authorized connector can be added later. It is not a live NCRP or SAHYOG integration."
)


class LeaComplaintService:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _serialize(row: LeaComplaint) -> dict[str, Any]:
        return {
            "complaint_id": row.complaint_id,
            "wallet_address": row.wallet_address,
            "blockchain": row.blockchain,
            "incident_type": row.incident_type,
            "reported_timestamp": row.reported_timestamp.isoformat() if row.reported_timestamp else None,
            "investigation_id": row.investigation_id,
            "status": row.status,
            "live_integration": False,
            "integration": INTEGRATION_DISCLAIMER,
        }

    def accept(self, payload: dict[str, Any]) -> dict[str, Any]:
        complaint_id = str(payload.get("complaint_id") or "").strip()
        wallet = str(payload.get("wallet_address") or "").strip().lower()
        chain = str(payload.get("blockchain") or "ethereum").strip().lower()
        if not complaint_id:
            raise ValueError("complaint_id is required.")
        if not wallet:
            raise ValueError("wallet_address is required.")
        investigation_id = str(payload.get("investigation_id") or complaint_id).strip()
        incident_type = (payload.get("incident_type") or None)
        reported = payload.get("reported_timestamp")
        status = str(payload.get("status") or "accepted").strip() or "accepted"

        with self.session_factory() as session:
            existing = session.query(LeaComplaint).filter(LeaComplaint.complaint_id == complaint_id).first()
            if existing is not None:
                return self._serialize(existing)

            case = session.query(Case).filter(Case.case_id == investigation_id).first()
            if case is None:
                case = Case(
                    case_id=investigation_id,
                    complaint_ref=complaint_id,
                    status="open",
                    current_stage="CREATED",
                    progress=0,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(case)
            elif not case.complaint_ref:
                case.complaint_ref = complaint_id

            row = LeaComplaint(
                complaint_id=complaint_id,
                wallet_address=wallet,
                blockchain=chain,
                incident_type=str(incident_type) if incident_type else None,
                reported_timestamp=reported,
                investigation_id=investigation_id,
                status=status,
                notes=INTEGRATION_DISCLAIMER,
                created_at=datetime.now(timezone.utc),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._serialize(row)

    def get(self, complaint_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            row = session.query(LeaComplaint).filter(LeaComplaint.complaint_id == complaint_id).first()
            if row is None:
                raise ValueError("Complaint not found.")
            return self._serialize(row)
