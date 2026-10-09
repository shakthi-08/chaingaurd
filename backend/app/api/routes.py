from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.transaction_graph_service import TransactionGraphService
from app.services.risk_analysis_service import RiskAnalysisService
from app.services.attribution_service import AttributionService
from app.services.evidence_service import EvidenceService
from app.services.report_service import ReportService
from app.services.ai_service import AIService
from app.services.cross_chain_service import CrossChainService
from app.services.wallet_ingestion_service import WalletIngestionService
from app.services.case_lifecycle import get_case_status, set_case_stage
from app.services.alert_service import AlertService
from app.services.protocol_detection_service import ProtocolDetectionService

router = APIRouter(prefix="/cases", tags=["cases"])


class WalletIngestionRequest(BaseModel):
    wallet_address: str = Field(..., min_length=1)
    chain: str = Field(default="ethereum", min_length=1, max_length=64)
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_hops: int | None = Field(default=None, ge=1, le=3)
    investigation_depth: int | None = Field(default=None, ge=1, le=3)


@router.post("/{case_id}/wallets")
def attach_wallet_to_case(case_id: str, payload: WalletIngestionRequest):
    service = WalletIngestionService()
    try:
        result = service.ingest_wallet(
            case_id,
            payload.wallet_address,
            payload.chain,
            start_time=payload.start_time,
            end_time=payload.end_time,
            max_hops=payload.max_hops,
            investigation_depth=payload.investigation_depth,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{case_id}/status")
def get_investigation_status(case_id: str):
    return get_case_status(case_id)


@router.get("/{case_id}/wallets")
def list_case_wallets(case_id: str):
    return WalletIngestionService().get_case_wallets(case_id)


@router.get("/{case_id}/transactions")
def list_case_transactions(case_id: str):
    return WalletIngestionService().get_case_transactions(case_id)


@router.get("/{case_id}/graph")
def get_case_graph(case_id: str):
    """Return persisted graph edges when available; otherwise build from transactions without writing."""
    return TransactionGraphService().get_persisted_graph(case_id)


@router.post("/{case_id}/graph")
def rebuild_case_graph(case_id: str):
    graph = TransactionGraphService().build_case_graph(case_id)
    set_case_stage(case_id, "GRAPH_READY")
    return graph


@router.get("/{case_id}/paths")
def get_case_paths(
    case_id: str,
    start_wallet: str = Query(..., min_length=1),
    max_hops: int = Query(default=TransactionGraphService.DEFAULT_MAX_HOPS, ge=1),
    direction: str = Query(default="both"),
    min_value: str | None = Query(default=None),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    parsed_min_value = None
    if min_value is not None:
        try:
            parsed_min_value = Decimal(min_value)
        except InvalidOperation as exc:
            raise HTTPException(status_code=400, detail="min_value must be numeric") from exc

    try:
        return TransactionGraphService().trace_case_paths(
            case_id,
            start_wallet,
            direction=direction,
            max_hops=max_hops,
            start_time=start_time,
            end_time=end_time,
            min_value=parsed_min_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{case_id}/risk")
def get_case_risk(case_id: str):
    persisted = RiskAnalysisService().get_persisted_risk(case_id)
    if persisted is not None:
        return persisted
    return {
        "overall_score": 0,
        "risk_level": "LOW",
        "indicators": [],
        "findings": [],
        "explanations": [],
        "evidence_refs": [],
        "persisted": False,
    }


@router.post("/{case_id}/analyze")
def analyze_case(case_id: str):
    """Explicit compute path: graph → risk/evidence → attribution, sequentially."""
    set_case_stage(case_id, "ANALYZING")
    try:
        graph = TransactionGraphService().build_case_graph(case_id)
        set_case_stage(case_id, "GRAPH_READY")
        risk = RiskAnalysisService().analyze_case(case_id)
        set_case_stage(case_id, "RISK_READY")
        attributions = AttributionService().attribute_case(case_id)
        set_case_stage(case_id, "ATTRIBUTION_READY")
        evidence = EvidenceService().list_case(case_id)
        alerts: list = []
        advanced: dict = {"defi": [], "bridges": [], "mixers": [], "unknown_contract_label": "Unknown Contract"}
        try:
            from sqlalchemy import func

            from app.database import SessionLocal
            from app.models import Case, Transaction

            with SessionLocal() as session:
                case = session.query(Case).filter(Case.case_id == case_id).first()
                addresses = {w.address.lower() for w in case.wallets} if case else set()
                transactions = (
                    session.query(Transaction)
                    .filter(
                        (func.lower(Transaction.from_address).in_(addresses))
                        | (func.lower(Transaction.to_address).in_(addresses))
                    )
                    .all()
                    if addresses
                    else []
                )
                session.expunge_all()
            detections = ProtocolDetectionService.detect_transactions(transactions)
            advanced = {
                "defi": [d for d in detections if d.get("category") in {"dex", "lending", "staking", "liquidity", "other_defi"}],
                "bridges": [d for d in detections if d.get("category") == "bridge"],
                "mixers": [d for d in detections if d.get("category") == "mixer"],
                "unknown_contract_label": "Unknown Contract",
            }
            alerts = AlertService().generate_for_case(
                case_id,
                risk=risk,
                attributions=attributions if isinstance(attributions, list) else [],
                detections=detections,
                transactions=transactions,
            )
        except Exception:
            alerts = AlertService().list_case(case_id)
        set_case_stage(case_id, "COMPLETED")
        return {
            "graph": graph,
            "risk": risk,
            "attributions": attributions,
            "evidence": evidence,
            "alerts": alerts,
            "advanced_indicators": advanced,
            "status": get_case_status(case_id),
        }
    except Exception as exc:
        set_case_stage(case_id, "FAILED", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@router.get("/{case_id}/alerts")
def get_case_alerts(case_id: str):
    return AlertService().list_case(case_id)


@router.get("/{case_id}/advanced-indicators")
def get_advanced_indicators(case_id: str):
    try:
        from sqlalchemy import func

        from app.database import SessionLocal
        from app.models import Case, Transaction

        with SessionLocal() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return {
                    "defi": [],
                    "bridges": [],
                    "mixers": [],
                    "unknown_contract_label": "Unknown Contract",
                }
            addresses = {w.address.lower() for w in case.wallets}
            transactions = (
                session.query(Transaction)
                .filter(
                    (func.lower(Transaction.from_address).in_(addresses))
                    | (func.lower(Transaction.to_address).in_(addresses))
                )
                .all()
                if addresses
                else []
            )
            session.expunge_all()
        detections = ProtocolDetectionService.detect_transactions(transactions)
        return {
            "defi": [d for d in detections if d.get("category") in {"dex", "lending", "staking", "liquidity", "other_defi"}],
            "bridges": [d for d in detections if d.get("category") == "bridge"],
            "mixers": [d for d in detections if d.get("category") == "mixer"],
            "unknown_contract_label": "Unknown Contract",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Advanced indicators unavailable: {exc}") from exc


@router.get("/{case_id}/attributions")
def get_case_attributions(case_id: str):
    return AttributionService().list_case_attributions(case_id)


class EvidenceCreateRequest(BaseModel):
    type: str = Field(..., min_length=1, max_length=64)
    source: str = Field(..., min_length=1, max_length=255)
    timestamp: datetime
    description: str = Field(..., min_length=1, max_length=1000)
    transaction_ref: str | None = None
    wallet_ref: str | None = None
    reference: str | None = None


@router.get("/{case_id}/evidence")
def get_case_evidence(case_id: str):
    return EvidenceService().list_case(case_id)


@router.post("/{case_id}/evidence")
def create_case_evidence(case_id: str, payload: EvidenceCreateRequest):
    try:
        return EvidenceService().create_manual(
            case_id,
            evidence_type=payload.type,
            source=payload.source,
            timestamp=payload.timestamp,
            description=payload.description,
            transaction_ref=payload.transaction_ref,
            wallet_ref=payload.wallet_ref,
            reference=payload.reference,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{case_id}/report", response_class=FileResponse)
def generate_case_report(case_id: str):
    try:
        path, metadata = ReportService().generate(case_id)
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 500
        raise HTTPException(status_code=status, detail=detail) from exc
    set_case_stage(case_id, "REPORT_READY")
    return FileResponse(path, media_type="application/pdf", filename=metadata["filename"])


@router.get("/{case_id}/reports")
def list_case_reports(case_id: str):
    try:
        return ReportService().list_reports(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class AIPathRequest(BaseModel):
    path_rank: int | None = Field(default=None, ge=1)


class AIAttributionRequest(BaseModel):
    wallet: str | None = None


def _ai_response(callable):
    try:
        return callable()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{case_id}/ai/summary")
def ai_case_summary(case_id: str):
    return _ai_response(lambda: AIService().summary(case_id))


@router.post("/{case_id}/ai/explain-path")
def ai_explain_path(case_id: str, payload: AIPathRequest | None = None):
    return _ai_response(lambda: AIService().explain_path(case_id, payload.path_rank if payload else None))


@router.post("/{case_id}/ai/explain-risk")
def ai_explain_risk(case_id: str):
    return _ai_response(lambda: AIService().explain_risk(case_id))


@router.post("/{case_id}/ai/explain-attribution")
def ai_explain_attribution(case_id: str, payload: AIAttributionRequest | None = None):
    return _ai_response(lambda: AIService().explain_attribution(case_id, payload.wallet if payload else None))


@router.post("/{case_id}/ai/next-steps")
def ai_next_steps(case_id: str):
    return _ai_response(lambda: AIService().next_steps(case_id))


class AIAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


@router.post("/{case_id}/ai/ask")
def ai_ask(case_id: str, payload: AIAskRequest):
    return _ai_response(lambda: AIService().answer(case_id, payload.question))


@router.get("/{case_id}/cross-chain")
def get_cross_chain_movements(case_id: str):
    try:
        return CrossChainService().case_movements(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
