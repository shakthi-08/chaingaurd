from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Case, Finding, RiskIndicator, Transaction
from app.services.protocol_detection_service import ProtocolDetectionService
from app.services.protocol_registry import UNCONFIRMED_DESTINATION
from app.services.reference_entity_dataset import REFERENCE_ENTITY_DATASET
from app.services.transaction_graph_service import TransactionGraphService


DEFAULT_RISK_WEIGHTS: dict[str, float] = {
    "rapid_forwarding": 20.0,
    "fan_in": 20.0,
    "fan_out": 20.0,
    "high_hop_velocity": 20.0,
    "value_fragmentation": 20.0,
    "mixer_exposure": 25.0,
    "cross_chain_movement": 15.0,
    "defi_interaction": 8.0,
    "exchange_cash_out": 15.0,
    "repeated_counterparties": 10.0,
}

_VASP_ADDRESSES = {
    str(item["known_wallet"]).lower()
    for item in REFERENCE_ENTITY_DATASET
    if str(item.get("type") or "").lower() in {"vasp", "exchange"}
}


class RiskAnalysisService:
    RAPID_FORWARDING_WINDOW = timedelta(hours=24)
    HIGH_HOP_WINDOW = timedelta(hours=24)
    FAN_THRESHOLD = 2
    FRAGMENTATION_THRESHOLD = 3

    def __init__(self, session_factory=SessionLocal, weights: dict[str, float] | None = None) -> None:
        self.session_factory = session_factory
        self.weights = {**DEFAULT_RISK_WEIGHTS, **(weights or {})}

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
                                f"Potential rapid fund movement detected: wallet {wallet} received funds and forwarded them within {elapsed}. Risk indicators are consistent with rapid movement; this is not a determination of fraud.",
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
                        f"Potential intermediary wallet usage detected: {len(sources)} source wallets sent funds to {destination}. Risk indicators are consistent with concentration; this is not a determination of fraud.",
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
                        f"Potential intermediary wallet usage detected: wallet {source} distributed funds to {len(destinations)} destination wallets. This is not a determination of fraud.",
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
                        f"Potential layering pattern detected: {path['hop_count']} hops occurred within {max(timestamps) - min(timestamps)}. Risk indicators are consistent with layering; this is not a determination of fraud.",
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
                    f"Potential layering pattern detected: wallet {source} split {total} across {len(transfers)} smaller transfers. This is not a determination of fraud.",
                    [item.tx_hash for item in transfers],
                    [source, *[item.to_address for item in transfers]],
                )
            )
        return indicators

    def _repeated_counterparties(self, transactions: list[Transaction]) -> list[dict[str, Any]]:
        counts: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            pair = tuple(sorted((transaction.from_address, transaction.to_address)))
            counts[pair].append(transaction)
        indicators = []
        for pair, items in sorted(counts.items()):
            if len(items) < 3:
                continue
            indicators.append(
                self._indicator(
                    "repeated_counterparties",
                    "low",
                    self.weights.get("repeated_counterparties", 10.0),
                    0.7,
                    f"Repeated counterparties identified: {pair[0]} and {pair[1]} appear together in {len(items)} transfers.",
                    [item.tx_hash for item in items],
                    list(pair),
                )
            )
        return indicators

    def _known_entity_patterns(self, transactions: list[Transaction]) -> list[dict[str, Any]]:
        detections = ProtocolDetectionService.detect_transactions(transactions)
        indicators: list[dict[str, Any]] = []
        seen_mixer: set[str] = set()
        seen_bridge: set[str] = set()
        seen_defi: set[str] = set()
        seen_vasp: set[str] = set()

        for item in detections:
            category = item.get("category")
            tx_hash = item["tx_hash"]
            wallets = [item.get("wallet"), item.get("counterparty")]
            if category == "mixer" and tx_hash not in seen_mixer:
                seen_mixer.add(tx_hash)
                indicators.append(
                    self._indicator(
                        "mixer_exposure",
                        "high",
                        self.weights.get("mixer_exposure", 25.0),
                        0.85,
                        f"Mixer exposure detected: interaction with known mixer/tumbler {item.get('protocol')}. "
                        "This is an investigative risk indicator and does not automatically mean criminal activity.",
                        [tx_hash],
                        wallets,
                    )
                )
            elif category == "bridge" and tx_hash not in seen_bridge:
                seen_bridge.add(tx_hash)
                dest = item.get("destination_chain")
                extra = f" Reported destination chain {dest}." if dest else ""
                indicators.append(
                    self._indicator(
                        "cross_chain_movement",
                        "medium",
                        self.weights.get("cross_chain_movement", 15.0),
                        0.8,
                        f"Cross-chain movement detected: interaction with known bridge {item.get('protocol')}.{extra} {UNCONFIRMED_DESTINATION}",
                        [tx_hash],
                        wallets,
                    )
                )
            elif category in {"dex", "lending", "staking", "liquidity", "other_defi"} and tx_hash not in seen_defi:
                seen_defi.add(tx_hash)
                indicators.append(
                    self._indicator(
                        "defi_interaction",
                        "low",
                        self.weights.get("defi_interaction", 8.0),
                        0.8,
                        f"DeFi interaction identified: known {item.get('category')} protocol {item.get('protocol')}. Unknown contracts are not labeled.",
                        [tx_hash],
                        wallets,
                    )
                )

        for transaction in transactions:
            dest = (transaction.to_address or "").lower()
            if dest in _VASP_ADDRESSES and transaction.tx_hash not in seen_vasp:
                seen_vasp.add(transaction.tx_hash)
                indicators.append(
                    self._indicator(
                        "exchange_cash_out",
                        "medium",
                        self.weights.get("exchange_cash_out", 15.0),
                        0.7,
                        f"Exchange exposure identified: transfer toward a publicly labeled VASP address {transaction.to_address}. Attribution remains a hypothesis.",
                        [transaction.tx_hash],
                        [transaction.from_address, transaction.to_address],
                    )
                )
        return indicators

    def analyze_transactions(
        self,
        transactions: Iterable[Transaction],
        *,
        paths: list[dict[str, Any]] | None = None,
        start_wallets: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        transaction_list = list(transactions)
        if paths is None:
            seeds = list(start_wallets) if start_wallets is not None else sorted({item.from_address for item in transaction_list})
            if not seeds and transaction_list:
                seeds = sorted({item.from_address for item in transaction_list})[:1]
            paths = []
            for wallet in seeds[:3]:
                paths.extend(
                    TransactionGraphService.trace_paths_from_transactions(
                        transaction_list,
                        wallet,
                        max_hops=TransactionGraphService.DEFAULT_MAX_HOPS,
                        max_paths=TransactionGraphService.MAX_PATHS,
                        max_neighbors=TransactionGraphService.MAX_NEIGHBORS_PER_NODE,
                    )
                )

        indicators = [
            *self._rapid_forwarding(transaction_list),
            *self._fan_patterns(transaction_list),
            *self._high_hop_velocity(transaction_list, paths),
            *self._value_fragmentation(transaction_list),
            *self._repeated_counterparties(transaction_list),
            *self._known_entity_patterns(transaction_list),
        ]
        overall_score = min(100.0, round(sum(item["score"] for item in indicators), 2))
        risk_level = "LOW" if overall_score <= 30 else "MEDIUM" if overall_score <= 70 else "HIGH"
        findings = [
            {
                "type": item["type"],
                "title": {
                    "rapid_forwarding": "Potential rapid fund movement detected",
                    "fan_in": "Potential intermediary wallet usage detected",
                    "fan_out": "Potential intermediary wallet usage detected",
                    "high_hop_velocity": "Potential layering pattern detected",
                    "value_fragmentation": "Potential layering pattern detected",
                    "mixer_exposure": "Mixer exposure detected",
                    "cross_chain_movement": "Cross-chain movement detected",
                    "defi_interaction": "DeFi interaction identified",
                    "exchange_cash_out": "Exchange exposure identified",
                    "repeated_counterparties": "Repeated counterparties identified",
                }.get(item["type"], "Investigative risk indicator"),
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
        addresses = {wallet.address.lower() for wallet in case.wallets}
        if not addresses:
            return []
        return (
            session.query(Transaction)
            .filter(
                (func.lower(Transaction.from_address).in_(addresses))
                | (func.lower(Transaction.to_address).in_(addresses))
            )
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
            .all()
        )

    def get_persisted_risk(self, case_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            indicators = session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).all()
            findings = session.query(Finding).filter(Finding.case_id == case_id).all()
            if not indicators and not findings:
                return None
            serialized_indicators = [
                {
                    "type": item.type,
                    "severity": item.severity,
                    "score": item.score,
                    "weight": item.weight,
                    "confidence": item.confidence,
                    "explanation": item.explanation,
                    "transaction_refs": item.transaction_refs or [],
                    "wallet_addresses": item.wallet_addresses or [],
                    "evidence_refs": item.evidence_refs or [],
                }
                for item in indicators
            ]
            serialized_findings = [
                {
                    "type": item.type,
                    "title": item.title,
                    "severity": item.severity,
                    "score": item.score,
                    "confidence": item.confidence,
                    "explanation": item.explanation,
                    "transaction_refs": item.transaction_refs or [],
                    "wallet_addresses": item.wallet_addresses or [],
                    "evidence_refs": item.evidence_refs or [],
                }
                for item in findings
            ]
            overall_score = min(100.0, round(sum(item["score"] for item in serialized_indicators), 2))
            risk_level = "LOW" if overall_score <= 30 else "MEDIUM" if overall_score <= 70 else "HIGH"
            return {
                "overall_score": overall_score,
                "risk_level": risk_level,
                "indicators": serialized_indicators,
                "findings": serialized_findings,
                "explanations": [item["explanation"] for item in serialized_indicators if item.get("explanation")],
                "evidence_refs": sorted(
                    {ref for item in serialized_indicators for ref in (item.get("evidence_refs") or [])}
                ),
                "persisted": True,
            }

    def analyze_case(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            seed_wallets = []
            if case is not None:
                seed_wallets = [
                    wallet.address
                    for wallet in case.wallets
                    if set(wallet.labels or []) & {"seed", "reported"}
                ] or [wallet.address for wallet in case.wallets[:1]]
            transactions = self._case_transactions(session, case_id)
            session.expunge_all()

        paths = []
        for wallet in seed_wallets[:3]:
            paths.extend(
                TransactionGraphService.trace_paths_from_transactions(
                    transactions,
                    wallet,
                    max_hops=TransactionGraphService.DEFAULT_MAX_HOPS,
                    max_paths=TransactionGraphService.MAX_PATHS,
                    max_neighbors=TransactionGraphService.MAX_NEIGHBORS_PER_NODE,
                )
            )
        assessment = self.analyze_transactions(transactions, paths=paths, start_wallets=seed_wallets)

        with self.session_factory() as session:
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
        assessment["persisted"] = True
        return assessment