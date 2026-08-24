from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Attribution, Case, Evidence, Finding, RiskIndicator, Transaction
from app.services.ai_provider import AIProvider, OpenAICompatibleProvider, ProviderUnavailableError, UnavailableAIProvider
from app.services.transaction_graph_service import TransactionGraphService


SYSTEM_PROMPT = """You are the ChainGuard Investigator Assistant. Use only the supplied investigation context.
Distinguish observed blockchain facts from deterministic analytical findings and attribution hypotheses.
Never invent transaction hashes, wallet addresses, evidence, VASP relationships, or missing facts.
Never change or recalculate deterministic risk scores. State when information is unavailable.
Use evidence references for factual claims where possible. Attribution is a hypothesis, not proof of ownership.
Do not claim criminality. Provide recommendations as recommendations requiring investigator review.
"""


class AIService:
    def __init__(self, session_factory=SessionLocal, provider: AIProvider | None = None) -> None:
        self.session_factory = session_factory
        self.provider = provider or self._configured_provider()
        init_db()

    @staticmethod
    def _configured_provider() -> AIProvider:
        if settings.ai_provider.lower() in {"openai", "openai-compatible", "local"} and settings.ai_api_key and settings.ai_model and settings.ai_base_url:
            return OpenAICompatibleProvider(settings.ai_api_key, settings.ai_model, settings.ai_base_url)
        return UnavailableAIProvider()

    @staticmethod
    def _timestamp(value: datetime | None) -> str | None:
        return value.astimezone(timezone.utc).isoformat() if value else None

    def build_context(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            addresses = [wallet.address for wallet in case.wallets]
            transactions = session.query(Transaction).filter(
                (Transaction.from_address.in_(addresses)) | (Transaction.to_address.in_(addresses))
            ).order_by(Transaction.timestamp.asc(), Transaction.id.asc()).all() if addresses else []
            graph = TransactionGraphService.build_graph(transactions)
            paths = []
            for wallet in sorted({item.from_address for item in transactions}):
                paths.extend(TransactionGraphService.trace_paths_from_transactions(transactions, wallet))
            risk_indicators = session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).all()
            findings = session.query(Finding).filter(Finding.case_id == case_id).all()
            wallet_ids = [wallet.id for wallet in case.wallets]
            attributions = session.query(Attribution).filter(Attribution.wallet_id.in_(wallet_ids)).all() if wallet_ids else []
            evidence = session.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.created_at.asc()).all()
            return {
                "case": {"case_id": case.case_id, "complaint_ref": case.complaint_ref, "status": case.status, "created_at": self._timestamp(case.created_at)},
                "wallets": [{"address": wallet.address, "chain": wallet.chain, "labels": wallet.labels or []} for wallet in case.wallets],
                "transactions": [{"tx_hash": item.tx_hash, "from": item.from_address, "to": item.to_address, "value": item.value, "token": item.token, "timestamp": self._timestamp(item.timestamp), "block": item.block} for item in transactions],
                "graph": graph,
                "paths": paths,
                "risk_indicators": [{"type": item.type, "severity": item.severity, "score": item.score, "confidence": item.confidence, "explanation": item.explanation, "transaction_refs": item.transaction_refs or [], "evidence_refs": item.evidence_refs or []} for item in risk_indicators],
                "findings": [{"type": item.type, "severity": item.severity, "score": item.score, "confidence": item.confidence, "explanation": item.explanation, "transaction_refs": item.transaction_refs or [], "evidence_refs": item.evidence_refs or []} for item in findings],
                "attributions": [{"wallet": item.wallet.address, "entity": item.entity.name, "confidence": item.confidence, "reasons": item.reasons or [], "source": item.source} for item in attributions],
                "evidence": [{"evidence_id": item.id, "type": item.type, "source": item.source, "transaction_ref": item.transaction_ref, "wallet_ref": item.wallet_ref, "timestamp": self._timestamp(item.timestamp), "description": item.description} for item in evidence],
            }

    @staticmethod
    def _references(context: dict[str, Any]) -> list[str]:
        return sorted({item["evidence_id"] for item in context["evidence"]})

    def answer(self, case_id: str, request: str, focus: str | None = None) -> dict[str, Any]:
        context = self.build_context(case_id)
        request = f"Focus: {focus}. {request}" if focus else request
        try:
            generated = self.provider.generate(SYSTEM_PROMPT, context, request)
            answer = generated
            provider_status = "available"
            limitations = ["AI output is grounded in supplied ChainGuard context and requires investigator review."]
        except ProviderUnavailableError as exc:
            answer = str(exc)
            provider_status = "unavailable"
            limitations = ["Configure an AI provider and credentials to enable generated explanations.", "Deterministic ChainGuard analysis remains available."]
        except Exception:
            answer = "AI assistance is temporarily unavailable. The deterministic ChainGuard data remains available."
            provider_status = "error"
            limitations = ["The configured provider could not be reached."]
        return {"answer": answer, "evidence_refs": self._references(context), "provider": self.provider.name, "model": settings.ai_model if provider_status == "available" else None, "ai_assisted": provider_status == "available", "provider_status": provider_status, "limitations": limitations}

    def summary(self, case_id: str) -> dict[str, Any]:
        return self.answer(case_id, "Provide a concise case summary using observed facts and deterministic findings.")

    def explain_path(self, case_id: str, path_rank: int | None = None) -> dict[str, Any]:
        return self.answer(case_id, "Explain the selected important fund-flow path and why it was highlighted. Do not infer facts beyond its records.", f"path rank {path_rank}" if path_rank is not None else None)

    def explain_risk(self, case_id: str) -> dict[str, Any]:
        return self.answer(case_id, "Explain the existing deterministic risk indicators and their recorded contributions. Do not calculate a new score.")

    def explain_attribution(self, case_id: str, wallet: str | None = None) -> dict[str, Any]:
        return self.answer(case_id, "Explain the existing attribution hypotheses and confidence values. Do not create new attribution claims.", f"wallet {wallet}" if wallet else None)

    def next_steps(self, case_id: str) -> dict[str, Any]:
        return self.answer(case_id, "Suggest reasonable investigative next steps as recommendations based only on available evidence.")