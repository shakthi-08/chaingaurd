from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.database import SessionLocal
from app.models import InvestigationAlert
from app.services.protocol_registry import UNCONFIRMED_DESTINATION


class AlertService:
    HIGH_VALUE_WEI = Decimal("10000000000000000000")  # 10 native units in wei

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _serialize(alert: InvestigationAlert) -> dict[str, Any]:
        return {
            "id": alert.id,
            "case_id": alert.case_id,
            "category": alert.category,
            "severity": alert.severity,
            "title": alert.title,
            "explanation": alert.explanation,
            "wallet_ref": alert.wallet_ref,
            "transaction_ref": alert.transaction_ref,
            "evidence_refs": alert.evidence_refs or [],
            "timestamp": alert.created_at.isoformat() if alert.created_at else None,
        }

    def list_case(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = (
                session.query(InvestigationAlert)
                .filter(InvestigationAlert.case_id == case_id)
                .order_by(InvestigationAlert.id.asc())
                .all()
            )
            return [self._serialize(item) for item in rows]

    def generate_for_case(
        self,
        case_id: str,
        *,
        risk: dict[str, Any] | None = None,
        attributions: list[dict[str, Any]] | None = None,
        detections: list[dict[str, Any]] | None = None,
        transactions: list | None = None,
    ) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        indicators = list((risk or {}).get("indicators") or [])
        indicator_types = {str(item.get("type") or "") for item in indicators}
        detections = list(detections or [])
        attributions = list(attributions or [])

        def add(
            category: str,
            severity: str,
            title: str,
            explanation: str,
            *,
            wallet: str | None = None,
            tx: str | None = None,
            evidence: list[str] | None = None,
        ) -> None:
            alerts.append(
                {
                    "case_id": case_id,
                    "category": category,
                    "severity": severity,
                    "title": title,
                    "explanation": explanation,
                    "wallet_ref": wallet,
                    "transaction_ref": tx,
                    "evidence_refs": evidence or [],
                    "created_at": now,
                }
            )

        if str((risk or {}).get("risk_level") or "").upper() == "HIGH":
            first = indicators[0] if indicators else {}
            add(
                "HIGH_RISK_WALLET",
                "high",
                "High-risk wallet indicators",
                "Overall risk level is HIGH based on persisted deterministic indicators. This is not a finding of criminal activity.",
                wallet=(first.get("wallet_addresses") or [None])[0],
                tx=(first.get("transaction_refs") or [None])[0],
                evidence=list(first.get("evidence_refs") or []),
            )

        vasps = [
            item
            for item in attributions
            if str(item.get("entity_type") or item.get("type") or "").lower() in {"vasp", "exchange"}
            or "vasp" in str(item.get("entity") or "").lower()
            or str(item.get("attribution_type") or "").lower() in {"vasp", "exchange"}
        ]
        if not vasps:
            vasps = [item for item in attributions if item.get("entity") and item.get("entity") != "Unknown"]
        if vasps:
            lead = vasps[0]
            add(
                "VASP_EXPOSURE",
                "medium",
                "Exchange exposure identified",
                f"VASP/exchange attribution lead recorded for {lead.get('wallet') or 'a case wallet'} "
                f"({lead.get('entity')}). Attribution is a hypothesis, not proof of ownership.",
                wallet=lead.get("wallet"),
                evidence=list(lead.get("evidence_refs") or []),
            )

        mixers = [item for item in detections if item.get("category") == "mixer"]
        if mixers or "mixer_exposure" in indicator_types:
            item = mixers[0] if mixers else next((i for i in indicators if i.get("type") == "mixer_exposure"), {})
            add(
                "MIXER_EXPOSURE",
                "high",
                "Mixer exposure detected",
                "Interaction with a known mixer/tumbler address was observed. This is an investigative risk indicator "
                "and does not automatically mean criminal activity.",
                wallet=item.get("wallet") or (item.get("wallet_addresses") or [None])[0],
                tx=item.get("tx_hash") or (item.get("transaction_refs") or [None])[0],
                evidence=list(item.get("evidence_refs") or []),
            )

        bridges = [item for item in detections if item.get("category") == "bridge"]
        if bridges or "cross_chain_movement" in indicator_types:
            item = bridges[0] if bridges else {}
            dest = item.get("destination_chain")
            explanation = UNCONFIRMED_DESTINATION
            if dest and not item.get("destination_confirmed"):
                explanation = (
                    f"Cross-chain movement detected toward {dest}. {UNCONFIRMED_DESTINATION}"
                )
            add(
                "CROSS_CHAIN_MOVEMENT",
                "medium",
                "Cross-chain movement detected",
                explanation,
                wallet=item.get("wallet"),
                tx=item.get("tx_hash"),
                evidence=list(item.get("evidence_refs") or []),
            )

        defi = [item for item in detections if item.get("category") in {"dex", "lending", "staking", "liquidity", "other_defi"}]
        if defi or "defi_interaction" in indicator_types:
            item = defi[0] if defi else {}
            add(
                "DEFI_INTERACTION",
                "low",
                "DeFi interaction identified",
                f"Known DeFi protocol interaction recorded"
                + (f" ({item.get('protocol')}, {item.get('category')})." if item.get("protocol") else "."),
                wallet=item.get("wallet"),
                tx=item.get("tx_hash"),
                evidence=list(item.get("evidence_refs") or []),
            )

        if "rapid_forwarding" in indicator_types:
            item = next(i for i in indicators if i.get("type") == "rapid_forwarding")
            add(
                "RAPID_FUND_MOVEMENT",
                "medium",
                "Potential rapid fund movement detected",
                item.get("explanation") or "Funds were received and forwarded within a short window.",
                wallet=(item.get("wallet_addresses") or [None])[0],
                tx=(item.get("transaction_refs") or [None])[0],
                evidence=list(item.get("evidence_refs") or []),
            )

        if "high_hop_velocity" in indicator_types or "value_fragmentation" in indicator_types:
            item = next(
                (i for i in indicators if i.get("type") in {"high_hop_velocity", "value_fragmentation"}),
                {},
            )
            add(
                "LAYERING_PATTERN",
                "medium",
                "Potential layering pattern detected",
                item.get("explanation") or "Multi-hop or fragmented transfers are consistent with a layering pattern.",
                wallet=(item.get("wallet_addresses") or [None])[0],
                tx=(item.get("transaction_refs") or [None])[0],
                evidence=list(item.get("evidence_refs") or []),
            )

        for tx in transactions or []:
            token = str(getattr(tx, "token", "") or "native").lower()
            if token not in {"native", "eth", "matic"}:
                continue
            try:
                value = Decimal(str(getattr(tx, "value", "0") or "0"))
            except (InvalidOperation, ValueError):
                continue
            if value >= self.HIGH_VALUE_WEI:
                add(
                    "HIGH_VALUE_TRANSFER",
                    "medium",
                    "High-value native transfer observed",
                    f"A native-asset transfer of {value} units was recorded on {getattr(tx, 'chain', 'unknown')}.",
                    wallet=getattr(tx, "from_address", None),
                    tx=getattr(tx, "tx_hash", None),
                    evidence=[f"transaction:{getattr(tx, 'tx_hash', '')}"],
                )
                break

        with self.session_factory() as session:
            session.query(InvestigationAlert).filter(InvestigationAlert.case_id == case_id).delete()
            persisted = []
            for item in alerts:
                row = InvestigationAlert(**item)
                session.add(row)
                persisted.append(row)
            session.commit()
            return [self._serialize(item) for item in persisted]
