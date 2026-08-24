from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import Entity, Wallet
from app.services.attribution_service import AttributionService
from app.services.demo_entity_dataset import DEMO_ENTITY_DATASET
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def make_wallet(address, chain="ethereum"):
    return Wallet(address=address, chain=chain, first_seen=datetime.now(timezone.utc))


def make_entities():
    return [Entity(**record) for record in DEMO_ENTITY_DATASET]


def test_exact_address_match_returns_attribution():
    results = AttributionService.attribute_wallets(
        [make_wallet("0x1111111111111111111111111111111111111111")], make_entities()
    )

    assert len(results) == 1
    assert results[0]["entity"] == "Demo Exchange Alpha"
    assert results[0]["entity_type"] == "vasp"
    assert results[0]["confidence"] == 98.5


def test_no_match_wallet_returns_no_attribution():
    results = AttributionService.attribute_wallets([make_wallet("0x9999999999999999999999999999999999999999")], make_entities())

    assert results == []


def test_confidence_and_reasons_explain_the_match():
    results = AttributionService.attribute_wallets(
        [make_wallet("0x1111111111111111111111111111111111111111")], make_entities()
    )

    result = results[0]
    assert "exact seeded address match" in result["reasons"]
    assert "known entity/address relationship" in result["reasons"]
    assert "source reliability" in " ".join(result["reasons"])
    assert "Likely associated with Demo Exchange Alpha" in result["explanation"]
    assert "does not prove ownership" in result["explanation"]


def test_multiple_possible_entities_are_returned_deterministically():
    results = AttributionService.attribute_wallets(
        [make_wallet("0x2222222222222222222222222222222222222222")], make_entities()
    )

    assert [result["entity_id"] for result in results] == ["DEMO-VASP-002", "DEMO-VASP-003"]
    assert results == AttributionService.attribute_wallets(
        [make_wallet("0x2222222222222222222222222222222222222222")], make_entities()
    )


def test_demo_attribution_is_persisted_and_api_exposes_evidence():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-ATTRIBUTION-API", "0x1111111111111111111111111111111111111111", "ethereum")

    response = client.get("/cases/CASE-ATTRIBUTION-API/attributions")
    repeat_response = client.get("/cases/CASE-ATTRIBUTION-API/attributions")

    assert response.status_code == 200
    assert response.json() == repeat_response.json()
    assert response.json()[0]["source"].startswith("DEMO/SAMPLE")
    assert response.json()[0]["evidence_refs"]