from __future__ import annotations

from typing import Any, Iterable

from app.models import Transaction
from app.services.protocol_registry import (
    UNCONFIRMED_DESTINATION,
    UNKNOWN_CONTRACT,
    lookup_protocol,
)


class ProtocolDetectionService:
    """Classify observed counterparties against the public known-address registry."""

    @staticmethod
    def classify_address(address: str | None, chain: str | None) -> dict[str, Any]:
        match = lookup_protocol(address, chain)
        if match is None:
            return {
                "known": False,
                "label": UNKNOWN_CONTRACT,
                "name": UNKNOWN_CONTRACT,
                "category": None,
                "relation": "TRANSFER",
                "destination_chain": None,
            }
        return {
            "known": True,
            "label": match["name"],
            "name": match["name"],
            "category": match["category"],
            "relation": match["relation"],
            "destination_chain": match.get("destination_chain"),
            "source": match.get("source"),
        }

    @classmethod
    def detect_transactions(cls, transactions: Iterable[Transaction]) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for tx in transactions:
            chain = getattr(tx, "chain", None) or "ethereum"
            for role, address in (("from", tx.from_address), ("to", tx.to_address)):
                match = lookup_protocol(address, chain)
                if match is None:
                    continue
                key = (tx.tx_hash, match["name"], role)
                if key in seen:
                    continue
                seen.add(key)
                destination_chain = match.get("destination_chain")
                destination_confirmed = False
                note = None
                if match["category"] == "bridge":
                    note = UNCONFIRMED_DESTINATION
                detections.append(
                    {
                        "tx_hash": tx.tx_hash,
                        "chain": chain,
                        "block": getattr(tx, "block", None),
                        "timestamp": tx.timestamp.isoformat() if getattr(tx, "timestamp", None) else None,
                        "wallet": tx.from_address if role == "to" else tx.to_address,
                        "counterparty": address,
                        "role": role,
                        "protocol": match["name"],
                        "category": match["category"],
                        "relation": match["relation"],
                        "destination_chain": destination_chain,
                        "destination_confirmed": destination_confirmed,
                        "destination_wallet": None,
                        "destination_transaction": None,
                        "note": note,
                        "confidence": 0.8,
                        "evidence_refs": [f"transaction:{tx.tx_hash}"],
                        "source": match.get("source") or "public_reference_registry",
                    }
                )
        return detections

    @classmethod
    def by_category(cls, detections: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
        return [item for item in detections if item.get("category") == category]
