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

router = APIRouter(prefix="/cases", tags=["cases"])


class WalletIngestionRequest(BaseModel):
    wallet_address: str = Field(..., min_length=1)
    chain: str = Field(default="ethereum", min_length=1, max_length=64)
    start_time: datetime | None = None
    end_time: datetime | None = None


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
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{case_id}/transactions")
def list_case_transactions(case_id: str):
    service = WalletIngestionService()
    return service.get_case_transactions(case_id)


@router.get("/{case_id}/graph")
def get_case_graph(case_id: str):
    return TransactionGraphService().build_case_graph(case_id)


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
    return RiskAnalysisService().analyze_case(case_id)


@router.post("/{case_id}/analyze")
def analyze_case(case_id: str):
    return RiskAnalysisService().analyze_case(case_id)


@router.get("/{case_id}/attributions")
def get_case_attributions(case_id: str):
    return AttributionService().attribute_case(case_id)


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
    try:
        return EvidenceService().list_case(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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


@router.get("/{case_id}/cross-chain")
def get_cross_chain_movements(case_id: str):
    try:
        return CrossChainService().case_movements(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
