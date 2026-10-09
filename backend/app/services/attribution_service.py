from __future__ import annotations

import threading
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import is_real_mode_enabled
from app.database import SessionLocal
from app.models import Attribution, Case, Entity, Evidence, Transaction, Wallet
from app.services.demo_entity_dataset import DEMO_ENTITY_DATASET
from app.services.reference_entity_dataset import REFERENCE_ENTITY_DATASET

AUTHORITATIVE_SOURCES = {
    "wallet_registry",
    "sanctions_registry",
    "ofac_sdn",
    "verified_registry",
    "etherscan_verified",
    "polygonscan_verified",
    "regulatory_filing",
    "court_order",
    "exchange_attestation",
}

AUTHORITATIVE_EVIDENCE_TYPES = {
    "registry_entry",
    "sanction_list",
    "verified_registry",
    "contract_creator",
}

DETERMINISTIC_LINKAGE_TYPES = {
    "deposit_sweep",
    "consolidated_sweep",
    "sweeper_relationship",
    "contract_creator",
}


class AttributionService:
    _persistence_locks: dict[tuple[int, ...], threading.Lock] = {}
    _persistence_locks_guard = threading.Lock()

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

    @classmethod
    def _persistence_lock(cls, wallet_ids: list[int]) -> threading.Lock:
        lock_key = tuple(sorted(wallet_ids))
        with cls._persistence_locks_guard:
            return cls._persistence_locks.setdefault(lock_key, threading.Lock())

    @staticmethod
    def seed_reference_entities(session: Session) -> list[Entity]:
        """Load the public known-address reference list for real investigations."""
        entities = []
        for record in REFERENCE_ENTITY_DATASET:
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
    def seed_demo_entities(session: Session) -> list[Entity]:
        if is_real_mode_enabled():
            return []

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

    @staticmethod
    def _status_for_score(score: float, *, has_authoritative: bool = False, has_deterministic: bool = False) -> tuple[str, str]:
        if score >= 85.0 and (has_authoritative or has_deterministic):
            return "observed_fact", "verified"
        if score >= 60.0 and (has_authoritative or has_deterministic):
            return "deterministic_analysis", "provisional"
        if score >= 25.0:
            return "inferred_hypothesis", "lead"
        return "unverified_lead", "unverified"

    @staticmethod
    def _factor(
        name: str,
        weight: float,
        score_contribution: float,
        evidence_ref: str | None,
        reason: str,
        factor_type: str,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "weight": round(weight, 2),
            "score_contribution": round(score_contribution, 2),
            "evidence_ref": evidence_ref,
            "reason": reason,
            "type": factor_type,
        }

    @classmethod
    def _real_confidence_for_wallet(
        cls,
        session: Session | None,
        wallet: Wallet,
        entity: Entity,
        case_id: int | None = None,
        *,
        evidence_list: list[Evidence] | None = None,
        competing_entities: list[Entity] | None = None,
        existing_attributions: list[Attribution] | None = None,
    ) -> tuple[float, list[dict[str, Any]], list[str], list[str], str, str] | None:
        wallet_address = (wallet.address or "").strip().lower()
        entity_wallet = (entity.known_wallet or "").strip().lower()

        # Must have an address match with candidate entity
        if not entity_wallet or wallet_address != entity_wallet:
            return None

        # Fetch case-specific evidence directly referencing this wallet or entity
        if evidence_list is None:
            evidence_query = session.query(Evidence).filter(
                (func.lower(Evidence.wallet_ref) == wallet_address)
                | (Evidence.hash == entity.entity_id)
                | (Evidence.hash == entity.name)
            )
            if case_id is not None:
                evidence_query = evidence_query.filter(Evidence.case_id == case_id)
            evidence_list = evidence_query.order_by(Evidence.timestamp.asc()).all()
        else:
            evidence_list = sorted(evidence_list, key=lambda item: item.timestamp)

        factors: list[dict[str, Any]] = []
        evidence_refs: list[str] = []
        conflicting_evidence: list[str] = []
        independent_sources: set[str] = set()

        has_authoritative = False
        has_deterministic = False

        # 1. Authoritative registry / identification match (0 to +50)
        source_normalized = (entity.source or "").strip().lower()
        is_entity_authoritative = source_normalized in AUTHORITATIVE_SOURCES or (
            source_normalized not in {"public_reference_registry", "osint", "osint_lead", "synthetic_demo"}
            and any(kw in source_normalized for kw in ["registry", "sanction", "ofac", "verified", "attestation", "court", "subpoena"])
        )

        registry_evidence = next(
            (ev for ev in evidence_list if ev.type in AUTHORITATIVE_EVIDENCE_TYPES),
            None,
        )

        if is_entity_authoritative or registry_evidence is not None:
            has_authoritative = True
            contrib = 50.0
            ref = registry_evidence.id if registry_evidence else f"entity:{entity.entity_id}"
            src_desc = registry_evidence.source if registry_evidence else entity.source or "verified_registry"
            factors.append(
                cls._factor(
                    "authoritative_registry_match",
                    50.0,
                    contrib,
                    ref,
                    f"Direct match in authoritative identification registry ({src_desc}).",
                    "observed_fact",
                )
            )
            evidence_refs.append(ref)
            independent_sources.add(src_desc)
        elif source_normalized in {"osint", "osint_lead", "public_reference_registry"} or any(ev.type == "osint_lead" for ev in evidence_list):
            contrib = 30.0
            osint_ev = next((ev for ev in evidence_list if ev.type == "osint_lead"), None)
            ref = osint_ev.id if osint_ev else f"entity:{entity.entity_id}"
            src_desc = "public known-address reference" if source_normalized == "public_reference_registry" else "public OSINT/investigator registry"
            factors.append(
                cls._factor(
                    "authoritative_registry_match",
                    50.0,
                    contrib,
                    ref,
                    f"Match in {src_desc}; this is a lead requiring corroboration, not proof of ownership.",
                    "inferred_hypothesis",
                )
            )
            evidence_refs.append(ref)
            independent_sources.add("osint")
        elif entity.source_reliability > 0:
            contrib = 15.0
            ref = f"entity:{entity.entity_id}"
            factors.append(
                cls._factor(
                    "authoritative_registry_match",
                    50.0,
                    contrib,
                    ref,
                    f"Candidate entity registered from source '{entity.source or 'unspecified'}'.",
                    "inferred_hypothesis",
                )
            )
            evidence_refs.append(ref)
            if entity.source:
                independent_sources.add(entity.source)
        else:
            factors.append(
                cls._factor(
                    "authoritative_registry_match",
                    50.0,
                    0.0,
                    None,
                    "No authoritative registry or identification match found.",
                    "unverified_lead",
                )
            )

        # 2. Source reliability weight (0 to +25)
        reliability = max(0.0, min(1.0, float(entity.source_reliability or 0.0)))
        source_contrib = round(25.0 * reliability, 2)
        if source_contrib > 0:
            factors.append(
                cls._factor(
                    "source_reliability_weight",
                    25.0,
                    source_contrib,
                    f"entity:{entity.entity_id}",
                    f"Entity provenance source reliability evaluated at {reliability:.2f}.",
                    "deterministic_analysis",
                )
            )
            evidence_refs.append(f"entity:{entity.entity_id}")
        else:
            factors.append(
                cls._factor(
                    "source_reliability_weight",
                    25.0,
                    0.0,
                    f"entity:{entity.entity_id}",
                    "Source reliability is unrated or zero.",
                    "unverified_lead",
                )
            )

        # 3. Deterministic on-chain linkage (0 to +20)
        linkage_evidence = [ev for ev in evidence_list if ev.type in DETERMINISTIC_LINKAGE_TYPES]
        if linkage_evidence:
            has_deterministic = True
            linkage_ref = linkage_evidence[0].id
            factors.append(
                cls._factor(
                    "deterministic_onchain_linkage",
                    20.0,
                    20.0,
                    linkage_ref,
                    f"Observed deterministic on-chain relationship ({linkage_evidence[0].type.replace('_', ' ')}).",
                    "deterministic_analysis",
                )
            )
            evidence_refs.extend(ev.id for ev in linkage_evidence)
            for ev in linkage_evidence:
                if ev.source:
                    independent_sources.add(ev.source)
        else:
            factors.append(
                cls._factor(
                    "deterministic_onchain_linkage",
                    20.0,
                    0.0,
                    None,
                    "No deterministic on-chain deposit sweep or contract creator link observed.",
                    "deterministic_analysis",
                )
            )

        # 4. Independent corroboration (0 to +10)
        # Genuinely independent distinct evidence sources (distinct source strings)
        distinct_source_count = len(independent_sources)
        if distinct_source_count >= 3:
            corrob_contrib = 10.0
            corrob_reason = f"{distinct_source_count} distinct independent evidence sources corroborate this attribution."
        elif distinct_source_count == 2:
            corrob_contrib = 5.0
            corrob_reason = "2 distinct independent evidence sources corroborate this attribution."
        else:
            corrob_contrib = 0.0
            corrob_reason = "Attribution relies on a single source without independent corroboration."

        factors.append(
            cls._factor(
                "independent_corroboration",
                10.0,
                corrob_contrib,
                evidence_refs[0] if evidence_refs else None,
                corrob_reason,
                "deterministic_analysis",
            )
        )

        # 5. Chain consistency (0 to +5)
        if entity.chain and wallet.chain and entity.chain.lower() == wallet.chain.lower():
            factors.append(
                cls._factor(
                    "chain_consistency",
                    5.0,
                    5.0,
                    f"entity:{entity.entity_id}",
                    f"Candidate entity is native to the observed {wallet.chain} blockchain.",
                    "observed_fact",
                )
            )
            evidence_refs.append(f"entity:{entity.entity_id}")
        elif not entity.chain:
            factors.append(
                cls._factor(
                    "chain_consistency",
                    5.0,
                    5.0,
                    f"entity:{entity.entity_id}",
                    "Candidate entity is multi-chain or chain-agnostic.",
                    "observed_fact",
                )
            )
        else:
            factors.append(
                cls._factor(
                    "chain_consistency",
                    5.0,
                    0.0,
                    f"entity:{entity.entity_id}",
                    f"Chain mismatch: entity ({entity.chain}) does not match wallet ({wallet.chain}).",
                    "observed_fact",
                )
            )

        # 6. Conflicting evidence penalty (0 to -40)
        if competing_entities is None:
            competing_entities = (
                session.query(Entity)
                .filter(
                    func.lower(Entity.known_wallet) == wallet_address,
                    Entity.entity_id != entity.entity_id,
                )
                .all()
            )
        for comp in competing_entities:
            conflicting_evidence.append(f"entity:{comp.entity_id}")

        if existing_attributions is None:
            existing_attributions = (
                session.query(Attribution)
                .filter(
                    Attribution.wallet_id == wallet.id,
                    Attribution.entity_id != entity.id,
                )
                .all()
            )
        for attr in existing_attributions:
            conflicting_evidence.append(f"attribution:{attr.entity_id}")

        conflicting_set = sorted(set(conflicting_evidence))
        conflict_count = len(conflicting_set)
        if conflict_count > 0:
            conflict_penalty = min(40.0, 20.0 + (conflict_count - 1) * 10.0)
            factors.append(
                cls._factor(
                    "conflicting_evidence_penalty",
                    -40.0,
                    -conflict_penalty,
                    f"wallet:{wallet.address}",
                    f"Detected {conflict_count} conflicting entity attribution(s) for this wallet.",
                    "deterministic_analysis",
                )
            )
        else:
            factors.append(
                cls._factor(
                    "conflicting_evidence_penalty",
                    -40.0,
                    0.0,
                    None,
                    "No conflicting entity attributions detected for this wallet.",
                    "deterministic_analysis",
                )
            )

        raw_score = sum(f["score_contribution"] for f in factors)
        score = max(0.0, min(100.0, raw_score))
        attribution_type, status = cls._status_for_score(
            score,
            has_authoritative=has_authoritative,
            has_deterministic=has_deterministic,
        )

        return (
            round(score, 2),
            factors,
            sorted(set(evidence_refs)),
            conflicting_set,
            attribution_type,
            status,
        )

    @classmethod
    def _serialize(
        cls,
        wallet: Wallet,
        entity: Entity,
        confidence: float,
        reasons: list[str],
        *,
        confidence_factors: list[dict[str, Any]] | None = None,
        evidence_refs: list[str] | None = None,
        conflicting_evidence: list[str] | None = None,
        attribution_type: str = "inferred_hypothesis",
        status: str = "provisional",
        provenance: str = "demo",
    ) -> dict[str, Any]:
        return {
            "wallet": wallet.address,
            "entity": entity.name,
            "entity_id": entity.entity_id,
            "entity_type": entity.type,
            "chain": entity.chain,
            "confidence": confidence,
            "reasons": reasons,
            "source": (
                "DEMO/SAMPLE attribution from SYNTHETIC_DEMO dataset"
                if provenance == "demo"
                else (
                    "Public known-address reference dataset; address match is a lead, not proof of ownership"
                    if provenance == "public_reference_registry"
                    else (entity.source or "case_observed_evidence")
                )
            ),
            "evidence_refs": evidence_refs or [f"entity-dataset:{entity.entity_id}", f"wallet-address:{wallet.address}"],
            "confidence_factors": confidence_factors or [],
            "conflicting_evidence": conflicting_evidence or [],
            "attribution_type": attribution_type,
            "status": status,
            "provenance": provenance,
            "explanation": (
                f"Candidate {entity.name} received attribution confidence of {confidence:.2f}% "
                f"({status}, {attribution_type}). This is an investigative attribution and does not prove ownership."
            ),
        }

    @classmethod
    def attribute_wallets(
        cls,
        wallets: Iterable[Wallet],
        entities: Iterable[Entity],
        *,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        if is_real_mode_enabled() and session is not None:
            results: list[dict[str, Any]] = []
            for wallet in sorted(wallets, key=lambda item: item.address):
                matches = [
                    entity
                    for entity in entities
                    if entity.known_wallet and wallet.address.lower() == entity.known_wallet.lower()
                ]
                for entity in sorted(matches, key=lambda item: item.entity_id):
                    scored = cls._real_confidence_for_wallet(session, wallet, entity, case_id=wallet.case_id)
                    if scored is None:
                        continue
                    confidence, factors, evidence_refs, conflicting, attribution_type, status = scored
                    active_reasons = [f["reason"] for f in factors if f["score_contribution"] != 0]
                    results.append(
                        cls._serialize(
                            wallet,
                            entity,
                            confidence,
                            active_reasons or [factor["reason"] for factor in factors],
                            confidence_factors=factors,
                            evidence_refs=evidence_refs,
                            conflicting_evidence=conflicting,
                            attribution_type=attribution_type,
                            status=status,
                            provenance="case_observed_evidence",
                        )
                    )
            return results

        if is_real_mode_enabled():
            return []

        results = []
        entities_by_address: dict[tuple[str | None, str | None], list[Entity]] = {}
        for entity in entities:
            known_addr = entity.known_wallet.lower() if entity.known_wallet else None
            chain_val = entity.chain.lower() if entity.chain else None
            entities_by_address.setdefault((known_addr, chain_val), []).append(entity)

        for wallet in sorted(wallets, key=lambda item: item.address):
            wallet_addr = wallet.address.lower() if wallet.address else None
            wallet_chain = wallet.chain.lower() if wallet.chain else None
            matches = entities_by_address.get((wallet_addr, wallet_chain), [])
            if not matches and wallet_addr:
                matches = [e for (addr, _), ents in entities_by_address.items() if addr == wallet_addr for e in ents]

            for entity in sorted(matches, key=lambda item: item.entity_id):
                confidence, reasons = cls.calculate_confidence(entity)
                demo_factors = [
                    cls._factor("seeded_demo_address_match", 60.0, 60.0, f"entity:{entity.entity_id}", "exact seeded address match", "inferred_hypothesis"),
                    cls._factor(
                        "demo_match_strength",
                        20.0,
                        round(20.0 * float((entity.confidence_metadata or {}).get("match_strength", 0.0)), 2),
                        f"entity:{entity.entity_id}",
                        "known entity/address relationship",
                        "inferred_hypothesis",
                    ),
                    cls._factor(
                        "synthetic_source_reliability",
                        15.0,
                        round(15.0 * float(entity.source_reliability or 0.0), 2),
                        f"entity:{entity.entity_id}",
                        f"synthetic dataset source reliability {entity.source_reliability:.0%}",
                        "inferred_hypothesis",
                    ),
                    cls._factor("demo_reference_baseline", 5.0, 5.0, f"entity:{entity.entity_id}", "supporting evidence is the seeded demo reference", "inferred_hypothesis"),
                ]
                attribution_type, status = cls._status_for_score(confidence, has_authoritative=False, has_deterministic=True)
                results.append(
                    cls._serialize(
                        wallet,
                        entity,
                        confidence,
                        reasons,
                        confidence_factors=demo_factors,
                        evidence_refs=[f"entity-dataset:{entity.entity_id}", f"wallet-address:{wallet.address}"],
                        attribution_type=attribution_type,
                        status=status,
                        provenance="demo",
                    )
                )
        return results

    def _persist_case_attributions(
        self,
        wallet_ids: list[int],
        rows: list[tuple[int, int, dict[str, Any]]],
    ) -> None:
        with self._persistence_lock(wallet_ids):
            with self.session_factory() as session:
                try:
                    with session.begin():
                        if wallet_ids:
                            session.query(Attribution).filter(Attribution.wallet_id.in_(wallet_ids)).delete(
                                synchronize_session=False
                            )
                        for wallet_id, entity_id, result in rows:
                            session.add(
                                Attribution(
                                    wallet_id=wallet_id,
                                    entity_id=entity_id,
                                    confidence=result["confidence"],
                                    reasons=result["reasons"],
                                    source=result["source"],
                                    attribution_type=result.get("attribution_type"),
                                    status=result.get("status"),
                                    confidence_factors=result.get("confidence_factors"),
                                    evidence_refs=result.get("evidence_refs"),
                                    conflicting_evidence=result.get("conflicting_evidence"),
                                    provenance=result.get("provenance"),
                                )
                            )
                except Exception:
                    session.rollback()
                    raise

    @staticmethod
    def _evidence_for_match(
        evidence: list[Evidence],
        wallet: Wallet,
        entity: Entity,
        case_pk: int,
    ) -> list[Evidence]:
        wallet_address = (wallet.address or "").strip().lower()
        matched = []
        for item in evidence:
            if item.case_id != case_pk:
                continue
            wallet_ref = (item.wallet_ref or "").strip().lower()
            if wallet_ref == wallet_address or item.hash == entity.entity_id or item.hash == entity.name:
                matched.append(item)
        return matched

    def attribute_case(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []
            case_pk = case.id
            wallets = list(case.wallets)
            wallet_ids = [wallet.id for wallet in wallets]
            session.expunge_all()

        if is_real_mode_enabled():
            with self._persistence_lock(wallet_ids):
                with self.session_factory() as session:
                    try:
                        self.seed_reference_entities(session)
                        session.commit()
                    except Exception:
                        session.rollback()
                        raise

            with self.session_factory() as session:
                wallets = session.query(Wallet).filter(Wallet.id.in_(wallet_ids)).all() if wallet_ids else []
                entities = session.query(Entity).all()
                evidence = session.query(Evidence).filter(Evidence.case_id == case_pk).all()
                existing_attributions = (
                    session.query(Attribution).filter(Attribution.wallet_id.in_(wallet_ids)).all()
                    if wallet_ids
                    else []
                )
                session.expunge_all()

            results: list[dict[str, Any]] = []
            rows: list[tuple[int, int, dict[str, Any]]] = []
            for wallet in sorted(wallets, key=lambda item: item.address):
                matches = [
                    entity
                    for entity in entities
                    if (entity.known_wallet or "").strip().lower() == wallet.address.lower()
                ]
                for entity in sorted(matches, key=lambda item: item.entity_id):
                    if entity.chain and wallet.chain and entity.chain.lower() != wallet.chain.lower():
                        continue
                    competing = [
                        item
                        for item in entities
                        if (item.known_wallet or "").strip().lower() == wallet.address.lower()
                        and item.entity_id != entity.entity_id
                    ]
                    scored = self._real_confidence_for_wallet(
                        None,
                        wallet,
                        entity,
                        case_id=case_pk,
                        evidence_list=self._evidence_for_match(evidence, wallet, entity, case_pk),
                        competing_entities=competing,
                        existing_attributions=[
                            item
                            for item in existing_attributions
                            if item.wallet_id == wallet.id and item.entity_id != entity.id
                        ],
                    )
                    if scored is None:
                        continue
                    confidence, factors, evidence_refs, conflicting, attribution_type, status = scored
                    active_reasons = [f["reason"] for f in factors if f["score_contribution"] != 0]
                    provenance = (
                        "public_reference_registry"
                        if (entity.source or "") == "public_reference_registry"
                        else "case_observed_evidence"
                    )
                    result = self._serialize(
                        wallet,
                        entity,
                        confidence,
                        active_reasons or [factor["reason"] for factor in factors],
                        confidence_factors=factors,
                        evidence_refs=evidence_refs,
                        conflicting_evidence=conflicting,
                        attribution_type=attribution_type,
                        status=status,
                        provenance=provenance,
                    )
                    results.append(result)
                    rows.append((wallet.id, entity.id, result))
            self._persist_case_attributions(wallet_ids, rows)
            return results

        with self._persistence_lock(wallet_ids):
            with self.session_factory() as session:
                try:
                    entities = self.seed_demo_entities(session)
                    session.commit()
                    session.expunge_all()
                except Exception:
                    session.rollback()
                    raise

        results = self.attribute_wallets(wallets, entities)
        entity_by_id = {entity.entity_id: entity for entity in entities}
        wallet_by_address = {wallet.address: wallet for wallet in wallets}
        rows = []
        for result in results:
            wallet = wallet_by_address[result["wallet"]]
            entity = entity_by_id[result["entity_id"]]
            rows.append((wallet.id, entity.id, result))
        self._persist_case_attributions(wallet_ids, rows)
        return results

    def list_case_attributions(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []
            wallet_ids = [wallet.id for wallet in case.wallets]
            if not wallet_ids:
                return []
            attributions = (
                session.query(Attribution)
                .filter(Attribution.wallet_id.in_(wallet_ids))
                .order_by(Attribution.id.asc())
                .all()
            )
            results = []
            for item in attributions:
                wallet = item.wallet
                entity = item.entity
                if wallet is None or entity is None:
                    continue
                results.append(
                    self._serialize(
                        wallet,
                        entity,
                        item.confidence,
                        item.reasons or [],
                        confidence_factors=item.confidence_factors or [],
                        evidence_refs=item.evidence_refs or [],
                        conflicting_evidence=item.conflicting_evidence or [],
                        attribution_type=item.attribution_type or "inferred_hypothesis",
                        status=item.status or "unverified",
                        provenance=item.provenance or "case_observed_evidence",
                    )
                )
            return results
