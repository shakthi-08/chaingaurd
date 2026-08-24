from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Attribution, Case, Evidence, Finding, GraphEdge, RiskIndicator, Transaction, Wallet


class EvidenceService:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory
        init_db()

    @staticmethod
    def evidence_id(*parts: str) -> str:
        payload = "|".join(parts).encode("utf-8")
        return f"EV-{hashlib.sha256(payload).hexdigest()[:20]}"

    @staticmethod
    def _create(
        session: Session,
        *,
        case_id: int,
        evidence_type: str,
        source: str,
        timestamp: datetime,
        description: str,
        transaction_ref: str | None = None,
        wallet_ref: str | None = None,
        reference: str | None = None,
    ) -> Evidence:
        identifier = EvidenceService.evidence_id(
            str(case_id), evidence_type, transaction_ref or "", wallet_ref or "", reference or ""
        )
        evidence = session.query(Evidence).filter(Evidence.id == identifier).first()
        if evidence is not None:
            return evidence
        evidence = Evidence(
            id=identifier,
            case_id=case_id,
            type=evidence_type,
            source=source,
            transaction_ref=transaction_ref,
            wallet_ref=wallet_ref,
            description=description,
            hash=reference,
            timestamp=timestamp,
            created_at=datetime.now(timezone.utc),
        )
        session.add(evidence)
        return evidence

    @staticmethod
    def serialize(evidence: Evidence) -> dict[str, Any]:
        return {
            "evidence_id": evidence.id,
            "case_id": evidence.case_id,
            "type": evidence.type,
            "source": evidence.source,
            "transaction_ref": evidence.transaction_ref,
            "wallet_ref": evidence.wallet_ref,
            "timestamp": evidence.timestamp.isoformat(),
            "hash": evidence.hash,
            "description": evidence.description,
            "created_at": evidence.created_at.isoformat(),
        }

    def create_manual(
        self,
        case_id: str,
        *,
        evidence_type: str,
        source: str,
        timestamp: datetime,
        description: str,
        transaction_ref: str | None = None,
        wallet_ref: str | None = None,
        reference: str | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            wallet_addresses = {wallet.address for wallet in case.wallets}
            transaction_hashes = {
                transaction.tx_hash
                for transaction in session.query(Transaction).filter(
                    (Transaction.from_address.in_(wallet_addresses))
                    | (Transaction.to_address.in_(wallet_addresses))
                )
            } if wallet_addresses else set()
            if transaction_ref and transaction_ref not in transaction_hashes:
                raise ValueError("Transaction reference is not associated with this case.")
            if wallet_ref and wallet_ref not in wallet_addresses:
                raise ValueError("Wallet reference is not associated with this case.")
            evidence = self._create(
                session,
                case_id=case.id,
                evidence_type=evidence_type,
                source=source,
                timestamp=timestamp,
                description=description,
                transaction_ref=transaction_ref,
                wallet_ref=wallet_ref,
                reference=reference,
            )
            session.commit()
            return self.serialize(evidence)

    def collect_case(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []
            now = datetime.now(timezone.utc)
            for wallet in sorted(case.wallets, key=lambda item: item.address):
                self._create(
                    session, case_id=case.id, evidence_type="wallet_relationship", source="deterministic_analysis",
                    timestamp=wallet.last_seen or wallet.first_seen or now, wallet_ref=wallet.address,
                    description=f"Wallet observed in case {case_id}; relationship requires investigator validation.",
                )
            addresses = {wallet.address for wallet in case.wallets}
            transactions = session.query(Transaction).filter(
                (Transaction.from_address.in_(addresses)) | (Transaction.to_address.in_(addresses))
            ).order_by(Transaction.timestamp.asc()).all() if addresses else []
            for transaction in transactions:
                self._create(
                    session, case_id=case.id, evidence_type="transaction", source="normalized_transaction",
                    timestamp=transaction.timestamp, transaction_ref=transaction.tx_hash,
                    description=f"Observed transaction from {transaction.from_address} to {transaction.to_address} for {transaction.value} {transaction.token or 'native'}.",
                    reference=transaction.tx_hash,
                )
            for edge in session.query(GraphEdge).filter(GraphEdge.tx_ref.in_([item.tx_hash for item in transactions])).all():
                self._create(
                    session, case_id=case.id, evidence_type="graph_edge", source="transaction_graph",
                    timestamp=edge.timestamp, transaction_ref=edge.tx_ref,
                    description=f"Directed relationship {edge.source} to {edge.destination} in the transaction graph.",
                    reference=edge.tx_ref,
                )
            for indicator in session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).all():
                for transaction_ref in indicator.transaction_refs or [None]:
                    self._create(
                        session, case_id=case.id, evidence_type="risk_indicator", source="deterministic_risk_engine",
                        timestamp=now, transaction_ref=transaction_ref, reference=indicator.type,
                        description=indicator.explanation or f"Investigative indicator: {indicator.type}.",
                    )
            for finding in session.query(Finding).filter(Finding.case_id == case_id).all():
                for transaction_ref in finding.transaction_refs or [None]:
                    self._create(
                        session, case_id=case.id, evidence_type="finding", source="deterministic_risk_engine",
                        timestamp=now, transaction_ref=transaction_ref, reference=finding.type or finding.title,
                        description=finding.explanation or finding.title,
                    )
            wallet_ids = [wallet.id for wallet in case.wallets]
            for attribution in session.query(Attribution).filter(Attribution.wallet_id.in_(wallet_ids)).all() if wallet_ids else []:
                wallet = session.query(Wallet).filter(Wallet.id == attribution.wallet_id).first()
                entity_name = attribution.entity.name if attribution.entity else "seeded entity"
                self._create(
                    session, case_id=case.id, evidence_type="attribution_hypothesis", source=attribution.source or "DEMO/SAMPLE",
                    timestamp=now, wallet_ref=wallet.address if wallet else None, reference=str(attribution.entity_id),
                    description=f"Likely association with {entity_name} at {attribution.confidence:.2f}% confidence; this is a hypothesis, not proof of ownership.",
                )
            session.commit()
            evidence = session.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.created_at.asc(), Evidence.id.asc()).all()
            return [self.serialize(item) for item in evidence]

    def list_case(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            evidence = session.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.created_at.asc(), Evidence.id.asc()).all()
            return [self.serialize(item) for item in evidence]