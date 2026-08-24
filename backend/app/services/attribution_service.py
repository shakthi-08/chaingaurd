from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Attribution, Case, Entity, Wallet
from app.services.demo_entity_dataset import DEMO_ENTITY_DATASET


class AttributionService:
    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory
        init_db()

    @staticmethod
    def seed_demo_entities(session: Session) -> list[Entity]:
        entities = []
        for record in DEMO_ENTITY_DATASET:
            entity = session.query(Entity).filter(Entity.entity_id == record["entity_id"]).first()
            if entity is None:
                entity = Entity(entity_id=record["entity_id"])
                session.add(entity)
            entity.name = record["name"]
            entity.type = record["type"]
            entity.known_wallet = record["known_wallet"]
            entity.chain = record["chain"]
            entity.source = record["source"]
            entity.source_reliability = record["source_reliability"]
            entity.confidence_metadata = record["confidence_metadata"]
            entities.append(entity)
        session.flush()
        return entities

    @staticmethod
    def calculate_confidence(entity: Entity, *, exact_match: bool = True) -> tuple[float, list[str]]:
        reasons = []
        score = 0.0
        if exact_match:
            score += 60.0
            reasons.append("exact seeded address match")
        match_strength = float((entity.confidence_metadata or {}).get("match_strength", 0.0))
        if match_strength:
            score += 20.0 * match_strength
            reasons.append("known entity/address relationship")
        if entity.source_reliability:
            score += 15.0 * entity.source_reliability
            reasons.append(f"synthetic dataset source reliability {entity.source_reliability:.0%}")
        score += 5.0
        reasons.append("supporting evidence is the seeded demo reference")
        return round(min(100.0, score), 2), reasons

    @classmethod
    def _serialize(cls, wallet: Wallet, entity: Entity, confidence: float, reasons: list[str]) -> dict[str, Any]:
        evidence_refs = [
            f"entity-dataset:{entity.entity_id}",
            f"wallet-address:{wallet.address}",
        ]
        return {
            "wallet": wallet.address,
            "entity": entity.name,
            "entity_id": entity.entity_id,
            "entity_type": entity.type,
            "chain": entity.chain,
            "confidence": confidence,
            "reasons": reasons,
            "source": "DEMO/SAMPLE attribution from SYNTHETIC_DEMO dataset",
            "evidence_refs": evidence_refs,
            "explanation": f"Likely associated with {entity.name}, confidence {confidence:.2f}%, based on {', '.join(reasons)}. Blockchain data alone does not prove ownership.",
        }

    @classmethod
    def attribute_wallets(
        cls,
        wallets: Iterable[Wallet],
        entities: Iterable[Entity],
    ) -> list[dict[str, Any]]:
        results = []
        entities_by_address: dict[tuple[str | None, str | None], list[Entity]] = {}
        for entity in entities:
            entities_by_address.setdefault((entity.known_wallet, entity.chain), []).append(entity)
        for wallet in sorted(wallets, key=lambda item: item.address):
            matches = entities_by_address.get((wallet.address, wallet.chain), [])
            for entity in sorted(matches, key=lambda item: item.entity_id):
                confidence, reasons = cls.calculate_confidence(entity)
                results.append(cls._serialize(wallet, entity, confidence, reasons))
        return results

    def attribute_case(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []
            entities = self.seed_demo_entities(session)
            results = self.attribute_wallets(case.wallets, entities)
            session.query(Attribution).filter(Attribution.wallet_id.in_([wallet.id for wallet in case.wallets])).delete(
                synchronize_session=False
            )
            entity_by_id = {entity.entity_id: entity for entity in entities}
            for result in results:
                wallet = next(wallet for wallet in case.wallets if wallet.address == result["wallet"])
                entity = entity_by_id[result["entity_id"]]
                session.add(
                    Attribution(
                        wallet_id=wallet.id,
                        entity_id=entity.id,
                        confidence=result["confidence"],
                        reasons=result["reasons"],
                        source=result["source"],
                    )
                )
            session.commit()
            return results