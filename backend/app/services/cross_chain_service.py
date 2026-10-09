from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import is_real_mode_enabled
from app.database import SessionLocal
from app.models import Case, Transaction
from app.services.demo_bridge_dataset import DEMO_BRIDGE_EVENTS
from app.services.protocol_detection_service import ProtocolDetectionService
from app.services.protocol_registry import UNCONFIRMED_DESTINATION


@dataclass(frozen=True)
class CrossChainMovement:
    source_chain: str
    source_transaction: str
    source_wallet: str
    destination_chain: str
    destination_transaction: str
    destination_wallet: str
    bridge_service: str
    timestamp: str
    transferred_value: str
    confidence: float
    reasons: list[str]
    evidence_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_chain": self.source_chain,
            "source_transaction": self.source_transaction,
            "source_wallet": self.source_wallet,
            "destination_chain": self.destination_chain,
            "destination_transaction": self.destination_transaction,
            "destination_wallet": self.destination_wallet,
            "bridge_service": self.bridge_service,
            "timestamp": self.timestamp,
            "transferred_value": self.transferred_value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "evidence_refs": self.evidence_refs,
            "source": "DEMO/SAMPLE synthetic correlation; not a real bridge finding",
            "bridge_detected": True,
            "destination_confirmed": True,
            "note": None,
        }


class CrossChainService:
    MAX_TIME_DELTA_SECONDS = 3600
    VALUE_TOLERANCE = Decimal("0.01")

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("-1")

    @staticmethod
    def _utc(value: datetime | str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

    @classmethod
    def correlate(cls, source: Transaction, destination: Transaction, event: dict[str, Any]) -> CrossChainMovement | None:
        reasons: list[str] = []
        if source.chain != event["source_chain"] or destination.chain != event["destination_chain"]:
            return None
        if source.tx_hash != event["source_transaction"] or destination.tx_hash != event["destination_transaction"]:
            return None
        if source.from_address != event["source_wallet"] or destination.from_address != event["destination_wallet"]:
            return None
        elapsed = abs((cls._utc(destination.timestamp) - cls._utc(source.timestamp)).total_seconds())
        if elapsed > cls.MAX_TIME_DELTA_SECONDS:
            return None
        reasons.append(f"compatible chains: {source.chain} -> {destination.chain}")
        reasons.append(f"temporal proximity: {int(elapsed)} seconds")
        if cls._decimal(source.value) != cls._decimal(destination.value):
            return None
        reasons.append("compatible transferred value")
        reasons.append(f"known synthetic bridge identifier: {event['bridge_service']}")
        reasons.append("source and destination wallets match the synthetic bridge workflow")
        evidence_refs = [f"transaction:{source.tx_hash}", f"transaction:{destination.tx_hash}"]
        return CrossChainMovement(
            source_chain=source.chain,
            source_transaction=source.tx_hash,
            source_wallet=source.from_address,
            destination_chain=destination.chain,
            destination_transaction=destination.tx_hash,
            destination_wallet=destination.from_address,
            bridge_service=event["bridge_service"],
            timestamp=event["timestamp"],
            transferred_value=source.value,
            confidence=98.0,
            reasons=reasons,
            evidence_refs=evidence_refs,
        )

    @classmethod
    def correlate_transactions(cls, transactions: Iterable[Transaction]) -> list[dict[str, Any]]:
        if is_real_mode_enabled():
            return []

        by_hash = {transaction.tx_hash: transaction for transaction in transactions}
        movements = []
        for event in DEMO_BRIDGE_EVENTS:
            source = by_hash.get(event["source_transaction"])
            destination = by_hash.get(event["destination_transaction"])
            if source is None or destination is None:
                continue
            movement = cls.correlate(source, destination, event)
            if movement is not None:
                movements.append(movement.to_dict())
        return movements

    def case_movements(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            addresses = {wallet.address.lower() for wallet in case.wallets}
            transactions = session.query(Transaction).filter(
                (func.lower(Transaction.from_address).in_(addresses)) | (func.lower(Transaction.to_address).in_(addresses))
            ).all() if addresses else []
            session.expunge_all()

        movements: list[dict[str, Any]] = []
        if not is_real_mode_enabled():
            movements.extend(self.correlate_transactions(transactions))

        try:
            detections = ProtocolDetectionService.detect_transactions(transactions)
        except Exception:
            detections = []
        for item in detections:
            if item.get("category") != "bridge":
                continue
            movements.append(
                {
                    "bridge_detected": True,
                    "source_chain": item.get("chain"),
                    "source_transaction": item.get("tx_hash"),
                    "source_wallet": item.get("wallet"),
                    "destination_chain": item.get("destination_chain") or "unconfirmed",
                    "destination_transaction": item.get("destination_transaction") or "",
                    "destination_wallet": item.get("destination_wallet") or "",
                    "bridge_service": item.get("protocol"),
                    "timestamp": item.get("timestamp"),
                    "transferred_value": "",
                    "confidence": round(float(item.get("confidence") or 0.8) * 100, 2),
                    "reasons": [
                        f"known bridge contract {item.get('counterparty')}",
                        item.get("note") or UNCONFIRMED_DESTINATION,
                    ],
                    "evidence_refs": item.get("evidence_refs") or [],
                    "source": item.get("source") or "public_reference_registry",
                    "destination_confirmed": False,
                    "note": item.get("note") or UNCONFIRMED_DESTINATION,
                }
            )
        return movements