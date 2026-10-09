from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.config import settings
from app.database import SessionLocal
from app.models import Attribution, Case, Evidence, Finding, RiskIndicator, Transaction
from app.services.ai_provider import (
    AIProvider,
    OpenAICompatibleProvider,
    ProviderUnavailableError,
    UnavailableAIProvider,
)
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

    @staticmethod
    def _configured_provider() -> AIProvider:
        provider_name = (settings.ai_provider or "").strip().lower()
        timeout = settings.ai_timeout if settings.ai_timeout and settings.ai_timeout > 0 else 60
        model = (settings.ai_model or "").strip() or None
        base_url = (settings.ai_base_url or "").strip() or None
        api_key = (settings.ai_api_key or "").strip()

        if provider_name in {"", "none", "unavailable", "off"}:
            return UnavailableAIProvider(
                "AI assistance is unavailable because no provider is configured (AI_PROVIDER=none). "
                "Set AI_PROVIDER=gemini and AI_API_KEY in backend/.env (optional AI_MODEL=gemini-2.5-flash), "
                "or use openai / ollama, then restart the backend."
            )

        if provider_name in {"openai", "openai-compatible"}:
            base_url = base_url or "https://api.openai.com/v1"
            model = model or "gpt-4o-mini"
            if provider_name == "openai" and not api_key:
                return UnavailableAIProvider(
                    "AI assistance is unavailable because AI_API_KEY is missing for AI_PROVIDER=openai. "
                    "Add AI_API_KEY to backend/.env and restart the backend."
                )
            return OpenAICompatibleProvider(api_key, model, base_url, timeout=timeout)

        if provider_name in {"gemini", "google"}:
            base_url = base_url or "https://generativelanguage.googleapis.com/v1beta/openai"
            model = model or "gemini-2.5-flash"
            if not api_key:
                return UnavailableAIProvider(
                    "AI assistance is unavailable because AI_API_KEY is missing for AI_PROVIDER=gemini. "
                    "Add a Google AI Studio API key as AI_API_KEY in backend/.env and restart the backend."
                )
            return OpenAICompatibleProvider(api_key, model, base_url, timeout=timeout)

        if provider_name in {"ollama", "local"}:
            base_url = base_url or "http://127.0.0.1:11434/v1"
            model = model or "llama3.2"
            return OpenAICompatibleProvider(api_key, model, base_url, timeout=timeout)

        return UnavailableAIProvider(
            f"AI assistance is unavailable because AI_PROVIDER={provider_name} is not supported. "
            "Use gemini, openai, or ollama."
        )

    @staticmethod
    def _timestamp(value: datetime | None) -> str | None:
        return value.astimezone(timezone.utc).isoformat() if value else None

    def build_context(self, case_id: str) -> dict[str, Any]:
        # Keep the DB session short: load persisted case data, then release before DFS/AI work.
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            wallets = list(case.wallets)
            addresses = {wallet.address.lower() for wallet in wallets}
            seed_wallets = [
                wallet for wallet in wallets if set(wallet.labels or []) & {"seed", "reported"}
            ]
            reported = seed_wallets[0] if seed_wallets else (wallets[0] if wallets else None)
            transactions = (
                session.query(Transaction)
                .filter(
                    (func.lower(Transaction.from_address).in_(addresses))
                    | (func.lower(Transaction.to_address).in_(addresses))
                )
                .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
                .all()
                if addresses
                else []
            )
            risk_indicators = session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).all()
            findings = session.query(Finding).filter(Finding.case_id == case_id).all()
            wallet_ids = [wallet.id for wallet in wallets]
            attributions = (
                session.query(Attribution).filter(Attribution.wallet_id.in_(wallet_ids)).all()
                if wallet_ids
                else []
            )
            # Materialize relationship fields before closing the session.
            attribution_rows = [
                {
                    "wallet": item.wallet.address if item.wallet else None,
                    "entity": item.entity.name if item.entity else "Unknown",
                    "confidence": item.confidence,
                    "reasons": list(item.reasons or []),
                    "source": item.source,
                    "status": item.status,
                    "attribution_type": item.attribution_type,
                    "confidence_factors": list(item.confidence_factors or []),
                    "evidence_refs": list(item.evidence_refs or []),
                    "conflicting_evidence": list(item.conflicting_evidence or []),
                    "provenance": item.provenance,
                }
                for item in attributions
            ]
            evidence = (
                session.query(Evidence)
                .filter(Evidence.case_id == case.id)
                .order_by(Evidence.created_at.asc())
                .all()
            )
            evidence_rows = [
                {
                    "evidence_id": item.id,
                    "type": item.type,
                    "source": item.source,
                    "transaction_ref": item.transaction_ref,
                    "wallet_ref": item.wallet_ref,
                    "timestamp": self._timestamp(item.timestamp),
                    "description": item.description,
                }
                for item in evidence[:40]
            ]
            case_row = {
                "case_id": case.case_id,
                "complaint_ref": case.complaint_ref,
                "status": case.status,
                "current_stage": getattr(case, "current_stage", None),
                "progress": getattr(case, "progress", None),
                "created_at": self._timestamp(case.created_at),
            }
            reported_row = (
                {"address": reported.address, "chain": reported.chain, "labels": list(reported.labels or [])}
                if reported
                else None
            )
            wallet_rows = [
                {
                    "address": wallet.address,
                    "chain": wallet.chain,
                    "labels": list(wallet.labels or []),
                    "is_seed": bool(set(wallet.labels or []) & {"seed", "reported"}),
                }
                for wallet in wallets
            ]
            transaction_rows = [
                {
                    "tx_hash": item.tx_hash,
                    "from": item.from_address,
                    "to": item.to_address,
                    "value": item.value,
                    "token": item.token,
                    "timestamp": self._timestamp(item.timestamp),
                    "block": item.block,
                }
                for item in transactions[:120]
            ]
            risk_rows = [
                {
                    "type": item.type,
                    "severity": item.severity,
                    "score": item.score,
                    "confidence": item.confidence,
                    "explanation": item.explanation,
                    "transaction_refs": list(item.transaction_refs or []),
                    "evidence_refs": list(item.evidence_refs or []),
                }
                for item in risk_indicators
            ]
            finding_rows = [
                {
                    "type": item.type,
                    "severity": item.severity,
                    "score": item.score,
                    "confidence": item.confidence,
                    "explanation": item.explanation,
                    "transaction_refs": list(item.transaction_refs or []),
                    "evidence_refs": list(item.evidence_refs or []),
                }
                for item in findings
            ]
            # Keep ORM objects only for path DFS (column attrs already loaded); drop session first.
            session.expunge_all()

        graph = TransactionGraphService.build_graph(transactions)
        paths: list[dict[str, Any]] = []
        seed_addresses = [row["address"] for row in wallet_rows if row.get("is_seed")] or [
            row["address"] for row in wallet_rows[:1]
        ]
        for wallet in seed_addresses[:1]:
            paths.extend(
                TransactionGraphService.trace_paths_from_transactions(
                    transactions,
                    wallet,
                    max_hops=TransactionGraphService.DEFAULT_MAX_HOPS,
                    max_paths=min(TransactionGraphService.MAX_PATHS, 50),
                    max_neighbors=TransactionGraphService.MAX_NEIGHBORS_PER_NODE,
                )
            )

        suspicious_transactions = []
        seen_hashes: set[str] = set()
        tx_by_hash = {item.tx_hash: item for item in transactions}
        for indicator in list(risk_indicators) + list(findings):
            for tx_hash in indicator.transaction_refs or []:
                if tx_hash in seen_hashes:
                    continue
                tx = tx_by_hash.get(tx_hash)
                if tx is not None:
                    suspicious_transactions.append(
                        {
                            "tx_hash": tx.tx_hash,
                            "from": tx.from_address,
                            "to": tx.to_address,
                            "value": tx.value,
                            "token": tx.token,
                            "timestamp": self._timestamp(tx.timestamp),
                            "block": tx.block,
                            "indicator_type": indicator.type,
                            "indicator_severity": indicator.severity,
                            "indicator_score": indicator.score,
                        }
                    )
                    seen_hashes.add(tx_hash)

        return {
            "case": case_row,
            "reported_wallet": reported_row,
            "wallets": wallet_rows,
            "transactions": transaction_rows,
            "graph": {
                "nodes": (graph.get("nodes") or [])[:80],
                "edges": (graph.get("edges") or [])[:80],
            },
            "paths": paths[:12],
            "risk_indicators": risk_rows,
            "findings": finding_rows,
            "suspicious_transactions": suspicious_transactions[:40],
            "attributions": attribution_rows,
            "evidence": evidence_rows,
        }

    @staticmethod
    def _compact_context(context: dict[str, Any]) -> dict[str, Any]:
        compacted = dict(context)
        transactions = list(compacted.get("transactions") or [])
        if len(transactions) > 80:
            compacted["transactions"] = [*transactions[:40], *transactions[-40:]]
            compacted["transaction_note"] = f"Context truncated to 80 of {len(transactions)} transactions."
        paths = list(compacted.get("paths") or [])
        if len(paths) > 12:
            compacted["paths"] = paths[:12]
            compacted["path_note"] = f"Context truncated to 12 of {len(paths)} paths."
        graph = compacted.get("graph") or {}
        edges = list(graph.get("edges") or [])
        if len(edges) > 80:
            compacted["graph"] = {
                **graph,
                "edges": edges[:80],
                "transactions": (graph.get("transactions") or [])[:80],
            }
        evidence = list(compacted.get("evidence") or [])
        if len(evidence) > 40:
            compacted["evidence"] = evidence[:40]
        return compacted

    @staticmethod
    def _references(context: dict[str, Any]) -> list[str]:
        return sorted({item["evidence_id"] for item in context.get("evidence") or [] if item.get("evidence_id")})

    def answer(self, case_id: str, request: str, focus: str | None = None) -> dict[str, Any]:
        # Context is built from persisted investigation data only. Provider I/O happens afterward.
        context = self._compact_context(self.build_context(case_id))
        request = f"Focus: {focus}. {request}" if focus else request
        try:
            generated = self.provider.generate(SYSTEM_PROMPT, context, request)
            answer = generated
            provider_status = "available"
            limitations = [
                "AI output is grounded in supplied ChainGuard context and requires investigator review."
            ]
        except ProviderUnavailableError as exc:
            answer = str(exc)
            provider_status = "unavailable"
            limitations = [str(exc), "Deterministic ChainGuard analysis remains available."]
        except Exception as exc:
            answer = f"AI assistance failed: {exc}. Deterministic ChainGuard data remains available."
            provider_status = "error"
            limitations = [str(exc)]
        model = getattr(self.provider, "model", None) if provider_status == "available" else settings.ai_model
        return {
            "answer": answer,
            "evidence_refs": self._references(context),
            "provider": self.provider.name,
            "model": model if provider_status == "available" else None,
            "ai_assisted": provider_status == "available",
            "provider_status": provider_status,
            "limitations": limitations,
        }

    def summary(self, case_id: str) -> dict[str, Any]:
        return self.answer(
            case_id,
            "Provide a concise case summary using observed facts and deterministic findings.",
        )

    def explain_path(self, case_id: str, path_rank: int | None = None) -> dict[str, Any]:
        return self.answer(
            case_id,
            "Explain the selected important fund-flow path and why it was highlighted. Do not infer facts beyond its records.",
            f"path rank {path_rank}" if path_rank is not None else None,
        )

    def explain_risk(self, case_id: str) -> dict[str, Any]:
        return self.answer(
            case_id,
            "Explain the existing deterministic risk indicators and their recorded contributions. Do not calculate a new score.",
        )

    def explain_attribution(self, case_id: str, wallet: str | None = None) -> dict[str, Any]:
        return self.answer(
            case_id,
            "Explain the existing attribution hypotheses and confidence values. Do not create new attribution claims.",
            f"wallet {wallet}" if wallet else None,
        )

    def next_steps(self, case_id: str) -> dict[str, Any]:
        return self.answer(
            case_id,
            "Suggest reasonable investigative next steps as recommendations based only on available evidence.",
        )
