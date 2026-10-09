from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Case, Entity, Evidence, Transaction, Wallet
from app.services.attribution_service import AttributionService
from app.services.demo_entity_dataset import DEMO_ENTITY_DATASET
from app.services.reference_entity_dataset import REFERENCE_ENTITY_DATASET
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def _set_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "environment", "demo")
    monkeypatch.setattr(settings, "blockchain_provider", "demo")


def _set_real_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "blockchain_provider", "real")
    monkeypatch.setattr(settings, "etherscan_api_key", "test-key")
    monkeypatch.setattr(settings, "polygonscan_api_key", "test-key")


def make_wallet(address, chain="ethereum"):
    return Wallet(address=address, chain=chain, first_seen=datetime.now(timezone.utc))


def make_entities():
    return [Entity(**record) for record in DEMO_ENTITY_DATASET]


# ---------------------------------------------------------------------------
# DEMO MODE TESTS
# ---------------------------------------------------------------------------


def test_exact_address_match_returns_attribution(monkeypatch):
    _set_demo_mode(monkeypatch)
    results = AttributionService.attribute_wallets(
        [make_wallet("0x1111111111111111111111111111111111111111")], make_entities()
    )

    assert len(results) == 1
    assert results[0]["entity"] == "Demo Exchange Alpha"
    assert results[0]["entity_type"] == "vasp"
    assert results[0]["confidence"] == 98.5


def test_no_match_wallet_returns_no_attribution(monkeypatch):
    _set_demo_mode(monkeypatch)
    results = AttributionService.attribute_wallets(
        [make_wallet("0x9999999999999999999999999999999999999999")], make_entities()
    )

    assert results == []


def test_confidence_and_reasons_explain_the_match(monkeypatch):
    _set_demo_mode(monkeypatch)
    results = AttributionService.attribute_wallets(
        [make_wallet("0x1111111111111111111111111111111111111111")], make_entities()
    )

    result = results[0]
    assert "exact seeded address match" in result["reasons"]
    assert "known entity/address relationship" in result["reasons"]
    assert "source reliability" in " ".join(result["reasons"])
    assert "Demo Exchange Alpha" in result["explanation"]
    assert "does not prove ownership" in result["explanation"]


def test_multiple_possible_entities_are_returned_deterministically(monkeypatch):
    _set_demo_mode(monkeypatch)
    results = AttributionService.attribute_wallets(
        [make_wallet("0x2222222222222222222222222222222222222222")], make_entities()
    )

    assert [result["entity_id"] for result in results] == ["DEMO-VASP-002", "DEMO-VASP-003"]
    assert results == AttributionService.attribute_wallets(
        [make_wallet("0x2222222222222222222222222222222222222222")], make_entities()
    )


def test_demo_attribution_is_persisted_and_api_exposes_evidence(monkeypatch):
    _set_demo_mode(monkeypatch)
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-ATTRIBUTION-API", "0x1111111111111111111111111111111111111111", "ethereum")

    analyze = client.post("/cases/CASE-ATTRIBUTION-API/analyze")
    response = client.get("/cases/CASE-ATTRIBUTION-API/attributions")
    repeat_response = client.get("/cases/CASE-ATTRIBUTION-API/attributions")

    assert analyze.status_code == 200
    assert response.status_code == 200
    assert response.json() == repeat_response.json()
    assert response.json()[0]["source"].startswith("DEMO/SAMPLE")
    assert response.json()[0]["evidence_refs"]


# ---------------------------------------------------------------------------
# REAL MODE EVIDENCE-DRIVEN ATTRIBUTION TESTS
# ---------------------------------------------------------------------------


def test_real_mode_wallet_with_no_identification_evidence_returns_no_attribution(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-NO-ATTR", complaint_ref="ref-none", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0x8888888888888888888888888888888888888888",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-NO-ATTR")
    assert results == []


def test_real_mode_authoritative_registry_match(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-AUTH-MATCH", complaint_ref="auth-match", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity = Entity(
            entity_id="REAL-AUTH-001",
            type="vasp",
            name="Authoritative Exchange Co",
            known_wallet="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain="ethereum",
            source="sanctions_registry",
            source_reliability=0.95,
            confidence_metadata={"match_strength": 1.0},
        )
        session.add(entity)
        session.add(
            Evidence(
                id="EV-REGISTRY-AUTH-001",
                case_id=case.id,
                type="registry_entry",
                source="sanctions_registry",
                wallet_ref="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                hash="REAL-AUTH-001",
                description="Officially verified entity registry entry for Authoritative Exchange Co.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.add(
            Evidence(
                id="EV-SWEEP-AUTH-002",
                case_id=case.id,
                type="deposit_sweep",
                source="onchain_sweep_tracer",
                wallet_ref="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                hash="REAL-AUTH-001",
                description="Observed deposit sweep confirming active exchange wallet operations.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-AUTH-MATCH")

    assert len(results) == 1
    attr = results[0]
    assert attr["entity"] == "Authoritative Exchange Co"
    assert attr["status"] == "verified"
    assert attr["attribution_type"] == "observed_fact"
    assert attr["confidence"] >= 85.0
    assert "EV-REGISTRY-AUTH-001" in attr["evidence_refs"]
    factors_by_name = {f["name"]: f for f in attr["confidence_factors"]}
    assert factors_by_name["authoritative_registry_match"]["score_contribution"] == 50.0
    assert factors_by_name["source_reliability_weight"]["score_contribution"] > 20.0
    assert factors_by_name["chain_consistency"]["score_contribution"] == 5.0


def test_real_mode_deterministic_deposit_sweep_increases_confidence(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-SWEEP", complaint_ref="sweep", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity = Entity(
            entity_id="REAL-SWEEP-001",
            type="vasp",
            name="Sweep Exchange",
            known_wallet="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            chain="ethereum",
            source="verified_registry",
            source_reliability=0.9,
        )
        session.add(entity)
        session.add(
            Evidence(
                id="EV-SWEEP-001",
                case_id=case.id,
                type="deposit_sweep",
                source="onchain_sweep_tracer",
                wallet_ref="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                transaction_ref="0xsweep123",
                description="Observed automated deposit sweep from intermediate address into exchange main wallet.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-SWEEP")
    assert len(results) == 1
    attr = results[0]
    factors_by_name = {f["name"]: f for f in attr["confidence_factors"]}
    assert factors_by_name["deterministic_onchain_linkage"]["score_contribution"] == 20.0
    assert "EV-SWEEP-001" in attr["evidence_refs"]


def test_real_mode_conflicting_attributions_penalized(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-CONFLICT", complaint_ref="conflict", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xcccccccccccccccccccccccccccccccccccccccc",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity1 = Entity(
            entity_id="REAL-CONFLICT-001",
            type="vasp",
            name="Claimant Entity One",
            known_wallet="0xcccccccccccccccccccccccccccccccccccccccc",
            chain="ethereum",
            source="osint_lead",
            source_reliability=0.6,
        )
        entity2 = Entity(
            entity_id="REAL-CONFLICT-002",
            type="vasp",
            name="Claimant Entity Two",
            known_wallet="0xcccccccccccccccccccccccccccccccccccccccc",
            chain="ethereum",
            source="osint_lead",
            source_reliability=0.6,
        )
        session.add_all([entity1, entity2])
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-CONFLICT")
    assert len(results) == 2
    for attr in results:
        assert len(attr["conflicting_evidence"]) > 0
        factors_by_name = {f["name"]: f for f in attr["confidence_factors"]}
        assert factors_by_name["conflicting_evidence_penalty"]["score_contribution"] < 0
        assert attr["confidence"] < 60.0


def test_confidence_calculation_deterministic(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-DETERM", complaint_ref="determ", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xdddddddddddddddddddddddddddddddddddddddd",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity = Entity(
            entity_id="REAL-DETERM-001",
            type="vasp",
            name="Deterministic Exchange",
            known_wallet="0xdddddddddddddddddddddddddddddddddddddddd",
            chain="ethereum",
            source="wallet_registry",
            source_reliability=0.8,
        )
        session.add(entity)
        session.commit()

    service = AttributionService()
    run1 = service.attribute_case("CASE-REAL-DETERM")
    run2 = service.attribute_case("CASE-REAL-DETERM")

    assert len(run1) == 1
    assert run1 == run2
    assert run1[0]["confidence"] == run2[0]["confidence"]
    assert run1[0]["confidence_factors"] == run2[0]["confidence_factors"]


def test_behavior_alone_does_not_produce_entity_attribution(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-BEHAVIOR-ONLY", complaint_ref="behavior", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        # Add 10 transactions and high velocity/fan-out activity
        for i in range(10):
            session.add(
                Transaction(
                    tx_hash=f"0xbehavior-tx-{i:03d}",
                    chain="ethereum",
                    from_address="0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                    to_address=f"0xrecipient{i:04d}0000000000000000000000000000000",
                    value="1000000000000000000",
                    token="ETH",
                    timestamp=datetime.now(timezone.utc),
                    block=1000 + i,
                )
            )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-BEHAVIOR-ONLY")
    # Behavior alone MUST NEVER produce a VASP attribution
    assert results == []


def test_independent_corroboration_increases_confidence(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-CORROB", complaint_ref="corrob", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0xffffffffffffffffffffffffffffffffffffffff",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity = Entity(
            entity_id="REAL-CORROB-001",
            type="vasp",
            name="Corroborated Custodian",
            known_wallet="0xffffffffffffffffffffffffffffffffffffffff",
            chain="ethereum",
            source="verified_registry",
            source_reliability=0.9,
        )
        session.add(entity)
        session.add(
            Evidence(
                id="EV-CORROB-SOURCE-1",
                case_id=case.id,
                type="registry_entry",
                source="regulatory_filing",
                wallet_ref="0xffffffffffffffffffffffffffffffffffffffff",
                hash="REAL-CORROB-001",
                description="Regulatory registry disclosure.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.add(
            Evidence(
                id="EV-CORROB-SOURCE-2",
                case_id=case.id,
                type="deposit_sweep",
                source="onchain_sweep_tracer",
                wallet_ref="0xffffffffffffffffffffffffffffffffffffffff",
                hash="REAL-CORROB-001",
                description="Direct onchain deposit sweep confirmation.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-CORROB")
    assert len(results) == 1
    attr = results[0]
    factors_by_name = {f["name"]: f for f in attr["confidence_factors"]}
    assert factors_by_name["independent_corroboration"]["score_contribution"] > 0
    assert attr["status"] == "verified"
    assert attr["attribution_type"] == "observed_fact"


def test_real_mode_never_uses_demo_dataset(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-DEMO-GUARD", complaint_ref="demo-guard", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        session.add(
            Wallet(
                address="0x1111111111111111111111111111111111111111",
                chain="ethereum",
                first_seen=case.created_at,
                last_seen=case.created_at,
                case=case,
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-DEMO-GUARD")
    with SessionLocal() as session:
        demo_entities = session.query(Entity).filter(Entity.entity_id.like("DEMO-%")).count()
        reference_entities = session.query(Entity).filter(Entity.entity_id.like("REF-%")).count()

    assert results == []
    assert demo_entities == 0
    assert reference_entities == len(REFERENCE_ENTITY_DATASET)


def test_real_mode_public_reference_registry_matches_known_address(monkeypatch):
    _set_real_mode(monkeypatch)
    known = REFERENCE_ENTITY_DATASET[0]
    with SessionLocal() as session:
        case = Case(
            case_id="CASE-REAL-REF-MATCH",
            complaint_ref="ref-match",
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        session.add(case)
        session.flush()
        session.add(
            Wallet(
                address=known["known_wallet"],
                chain=known["chain"],
                first_seen=case.created_at,
                last_seen=case.created_at,
                case=case,
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-REF-MATCH")
    assert len(results) == 1
    assert results[0]["entity_id"] == known["entity_id"]
    assert results[0]["entity_type"] == "vasp"
    assert results[0]["provenance"] == "public_reference_registry"
    assert "not proof of ownership" in results[0]["source"].lower()
    assert results[0]["confidence"] >= 25
    assert results[0]["status"] != "verified"


def test_real_mode_attribution_uses_observed_evidence_and_explainable_confidence(monkeypatch):
    _set_real_mode(monkeypatch)
    with SessionLocal() as session:
        case = Case(case_id="CASE-REAL-ATTR-EVIDENCE", complaint_ref="real-attr", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        wallet = Wallet(
            address="0x3333333333333333333333333333333333333333",
            chain="ethereum",
            first_seen=case.created_at,
            last_seen=case.created_at,
            case=case,
        )
        session.add(wallet)
        session.flush()
        entity = Entity(
            entity_id="REAL-ENTITY-001",
            type="exchange",
            name="Real Exchange Ltd",
            known_wallet="0x3333333333333333333333333333333333333333",
            chain="ethereum",
            source="wallet_registry",
            source_reliability=0.9,
            confidence_metadata={"match_strength": 1.0},
        )
        session.add(entity)
        session.add(
            Transaction(
                tx_hash="0xreal-attr-tx-001",
                chain="ethereum",
                from_address="0x3333333333333333333333333333333333333333",
                to_address="0x4444444444444444444444444444444444444444",
                value="500000000000000000",
                token="ETH",
                timestamp=datetime.now(timezone.utc),
                block=100,
            )
        )
        session.add(
            Evidence(
                id="EV-REAL-ATTR-001",
                case_id=case.id,
                type="registry_entry",
                source="wallet_registry",
                transaction_ref="0xreal-attr-tx-001",
                wallet_ref="0x3333333333333333333333333333333333333333",
                description="Wallet appears in observed chain activity for Real Exchange Ltd.",
                timestamp=datetime.now(timezone.utc),
            )
        )
        session.commit()

    results = AttributionService().attribute_case("CASE-REAL-ATTR-EVIDENCE")

    assert len(results) == 1
    assert results[0]["provenance"] == "case_observed_evidence"
    assert results[0]["attribution_type"] in {"observed_fact", "deterministic_analysis"}
    assert results[0]["confidence"] > 0
    assert results[0]["evidence_refs"]
    assert any("authoritative_registry_match" in factor["name"] for factor in results[0]["confidence_factors"])
