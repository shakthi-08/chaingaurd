from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Case, Finding, RiskIndicator, Transaction
from app.services.transaction_graph_service import TransactionGraphService


DEFAULT_RISK_WEIGHTS: dict[str, float] = {
    "rapid_forwarding": 20.0,
    "fan_in": 20.0,
    "fan_out": 20.0,
    "high_hop_velocity": 20.0,
    "value_fragmentation": 20.0,
}


class RiskAnalysisService:
    RAPID_FORWARDING_WINDOW = timedelta(hours=24)
    HIGH_HOP_WINDOW = timedelta(hours=24)
    FAN_THRESHOLD = 2
    FRAGMENTATION_THRESHOLD = 3

    def __init__(self, session_factory=SessionLocal, weights: dict[str, float] | None = None) -> None:
        self.session_factory = session_factory
        self.weights = {**DEFAULT_RISK_WEIGHTS, **(weights or {})}
        init_db()

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _indicator(
        pattern_type: str,
        severity: str,
        score: float,
        confidence: float,
        explanation: str,
        transactions: Iterable[str],
        wallets: Iterable[str],
    ) -> dict[str, Any]:
        transaction_refs = list(dict.fromkeys(transactions))
        wallet_addresses = list(dict.fromkeys(wallets))
        evidence_refs = [f"transaction:{reference}" for reference in transaction_refs]
        return {
            "type": pattern_type,
            "severity": severity,
            "score": round(score, 2),
            "weight": round(score, 2),
            "confidence": round(confidence, 2),
            "explanation": explanation,
            "transaction_refs": transaction_refs,
            "wallet_addresses": wallet_addresses,
            "evidence_refs": evidence_refs,
        }

    def _rapid_forwarding(self, transactions: list[Transaction]) -> list[dict[str, Any]]:
        incoming: dict[str, list[Transaction]] = defaultdict(list)
        outgoing: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            incoming[transaction.to_address].append(transaction)
            outgoing[transaction.from_address].append(transaction)

        indicators = []
        for wallet, received in incoming.items():
            for inbound in received:
                for outbound in outgoing.get(wallet, []):
                    elapsed = self._utc(outbound.timestamp) - self._utc(inbound.timestamp)
                    if timedelta(0) <= elapsed <= self.RAPID_FORWARDING_WINDOW:
                        indicators.append(
                            self._indicator(
                                "rapid_forwarding",
                                "medium",
                                self.weights["rapid_forwarding"],
                                0.9,
                                f"Suspicious pattern detected: wallet {wallet} received funds and forwarded them within {elapsed}. Requires further investigation.",
                                [inbound.tx_hash, outbound.tx_hash],
                                [inbound.from_address, wallet, outbound.to_address],
                            )
                        )
        return indicators

    def _fan_patterns(self, transactions: list[Transaction]) -> list[dict[str, Any]]:
        sources_by_destination: dict[str, set[str]] = defaultdict(set)
        refs_by_destination: dict[str, list[str]] = defaultdict(list)
        destinations_by_source: dict[str, set[str]] = defaultdict(set)
        refs_by_source: dict[str, list[str]] = defaultdict(list)
        for transaction in transactions:
            sources_by_destination[transaction.to_address].add(transaction.from_address)
            refs_by_destination[transaction.to_address].append(transaction.tx_hash)
            destinations_by_source[transaction.from_address].add(transaction.to_address)
            refs_by_source[transaction.from_address].append(transaction.tx_hash)

        indicators = []
        for destination, sources in sorted(sources_by_destination.items()):
            if len(sources) >= self.FAN_THRESHOLD:
                indicators.append(
                    self._indicator(
                        "fan_in",
                        "medium",
                        self.weights["fan_in"],
                        0.85,
                        f"Suspicious pattern detected: {len(sources)} source wallets sent funds to {destination}. Requires further investigation.",
                        refs_by_destination[destination],
                        [*sorted(sources), destination],
                    )
                )
        for source, destinations in sorted(destinations_by_source.items()):
            if len(destinations) >= self.FAN_THRESHOLD:
                indicators.append(
                    self._indicator(
                        "fan_out",
                        "medium",
                        self.weights["fan_out"],
                        0.85,
                        f"Suspicious pattern detected: wallet {source} distributed funds to {len(destinations)} destination wallets. Requires further investigation.",
                        refs_by_source[source],
                        [source, *sorted(destinations)],
                    )
                )
        return indicators

    def _high_hop_velocity(self, transactions: list[Transaction], paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
        indicators = []
        for path in paths:
            if path["hop_count"] < 2:
                continue
            timestamps = [datetime.fromisoformat(item) for item in path["timestamps"]]
            if max(timestamps) - min(timestamps) <= self.HIGH_HOP_WINDOW:
                indicators.append(
                    self._indicator(
                        "high_hop_velocity",
                        "medium",
                        self.weights["high_hop_velocity"],
                        0.75,
                        f"Suspicious pattern detected: {path['hop_count']} hops occurred within {max(timestamps) - min(timestamps)}. Requires further investigation.",
                        path["transactions"],
                        path["wallets"],
                    )
                )
                break
        return indicators

    def _value_fragmentation(self, transactions: list[Transaction]) -> list[dict[str, Any]]:
        outgoing: dict[str, list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            outgoing[transaction.from_address].append(transaction)

        indicators = []
        for source, transfers in sorted(outgoing.items()):
            if len(transfers) < self.FRAGMENTATION_THRESHOLD:
                continue
            total = sum((self._decimal(item.value) for item in transfers), Decimal("0"))
            if total <= 0 or not all(self._decimal(item.value) < total / 2 for item in transfers):
                continue
            indicators.append(
                self._indicator(
                    "value_fragmentation",
                    "medium",
                    self.weights["value_fragmentation"],
                    0.7,
                    f"Suspicious pattern detected: wallet {source} split {total} across {len(transfers)} smaller transfers. Requires further investigation.",
                    [item.tx_hash for item in transfers],
                    [source, *[item.to_address for item in transfers]],
                )
            )
        return indicators

    def analyze_transactions(
        self,
        transactions: Iterable[Transaction],
        *,
        paths: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        transaction_list = list(transactions)
        if paths is None:
            start_wallets = sorted({item.from_address for item in transaction_list})
            paths = []
            for wallet in start_wallets:
                paths.extend(TransactionGraphService.trace_paths_from_transactions(transaction_list, wallet))

        indicators = [
            *self._rapid_forwarding(transaction_list),
            *self._fan_patterns(transaction_list),
            *self._high_hop_velocity(transaction_list, paths),
            *self._value_fragmentation(transaction_list),
        ]
        overall_score = min(100.0, round(sum(item["score"] for item in indicators), 2))
        risk_level = "LOW" if overall_score <= 30 else "MEDIUM" if overall_score <= 70 else "HIGH"
        findings = [
            {
                "type": item["type"],
                "title": "Suspicious pattern detected",
                "severity": item["severity"],
                "score": item["score"],
                "confidence": item["confidence"],
                "explanation": item["explanation"],
                "transaction_refs": item["transaction_refs"],
                "wallet_addresses": item["wallet_addresses"],
                "evidence_refs": item["evidence_refs"],
            }
            for item in indicators
        ]
        return {
            "overall_score": overall_score,
            "risk_level": risk_level,
            "indicators": indicators,
            "findings": findings,
            "explanations": [item["explanation"] for item in indicators],
            "evidence_refs": sorted({ref for item in indicators for ref in item["evidence_refs"]}),
        }

    @staticmethod
    def _case_transactions(session: Session, case_id: str) -> list[Transaction]:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            return []
        addresses = [wallet.address for wallet in case.wallets]
        if not addresses:
            return []
        return (
            session.query(Transaction)
            .filter((Transaction.from_address.in_(addresses)) | (Transaction.to_address.in_(addresses)))
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
            .all()
        )

    def analyze_case(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            transactions = self._case_transactions(session, case_id)
            paths = []
            for wallet in sorted({item.from_address for item in transactions}):
                paths.extend(TransactionGraphService.trace_paths_from_transactions(transactions, wallet))
            assessment = self.analyze_transactions(transactions, paths=paths)
            session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).delete()
            session.query(Finding).filter(Finding.case_id == case_id).delete()
            for indicator in assessment["indicators"]:
                session.add(
                    RiskIndicator(
                        case_id=case_id,
                        type=indicator["type"],
                        severity=indicator["severity"],
                        score=indicator["score"],
                        weight=indicator["weight"],
                        confidence=indicator["confidence"],
                        explanation=indicator["explanation"],
                        transaction_refs=indicator["transaction_refs"],
                        wallet_addresses=indicator["wallet_addresses"],
                        evidence_refs=indicator["evidence_refs"],
                        evidence_ref=indicator["evidence_refs"][0] if indicator["evidence_refs"] else None,
                    )
                )
            for finding in assessment["findings"]:
                session.add(
                    Finding(
                        case_id=case_id,
                        type=finding["type"],
                        title=finding["title"],
                        severity=finding["severity"],
                        score=finding["score"],
                        confidence=finding["confidence"],
                        explanation=finding["explanation"],
                        transaction_refs=finding["transaction_refs"],
                        wallet_addresses=finding["wallet_addresses"],
                        evidence_refs=finding["evidence_refs"],
                        evidence=", ".join(finding["evidence_refs"]),
                    )
                )
            session.commit()
            from app.services.evidence_service import EvidenceService

            EvidenceService(self.session_factory).collect_case(case_id)
            return assessment