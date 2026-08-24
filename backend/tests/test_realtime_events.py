from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Case, Transaction
from app.models.investigation_event import InvestigationEvent
from app.services.demo_event_provider import DemoEventProvider
from app.services.event_processing_service import EventProcessingService
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def make_case(case_id="CASE-EVENTS"):
    WalletIngestionService().ingest_wallet(case_id, "0x1111111111111111111111111111111111111111", "ethereum")


def test_event_model_and_demo_provider_are_deterministic():
    first = DemoEventProvider().get_events("CASE-DEMO-001")
    second = DemoEventProvider().get_events("CASE-DEMO-001")

    assert first == second
    assert first[0].event_type == "new_transaction"
    assert first[0].source == "SYNTHETIC_DEMO"
    assert first[0].to_dict()["timestamp"].endswith("+00:00")


def test_event_validation_rejects_malformed_events():
    base = DemoEventProvider().get_events("CASE-EVENTS")[0]
    invalid_cases = [
        InvestigationEvent(**{**base.__dict__, "case_id": ""}),
        InvestigationEvent(**{**base.__dict__, "chain": "bitcoin"}),
        InvestigationEvent(**{**base.__dict__, "event_type": "unknown"}),
        InvestigationEvent(**{**base.__dict__, "transaction_ref": None}),
    ]

    for event in invalid_cases:
        with pytest.raises(ValueError):
            EventProcessingService.validate(event)


def test_event_processing_adds_new_transaction_without_overwriting_existing():
    make_case()
    event = DemoEventProvider().get_events("CASE-EVENTS")[0]
    service = EventProcessingService()

    service.process(event)
    service.process(event)

    with SessionLocal() as session:
        matching = session.query(Transaction).filter(Transaction.tx_hash == event.transaction_ref).all()
        assert len(matching) == 1
        assert matching[0].chain == "ethereum"


def test_websocket_delivers_deterministic_demo_events():
    make_case("CASE-WS")
    with client.websocket_connect("/cases/CASE-WS/events") as websocket:
        first = websocket.receive_json()
        second = websocket.receive_json()

    assert first["event_type"] == "new_transaction"
    assert first["source"] == "SYNTHETIC_DEMO"
    assert second["event_type"] == "analysis_update"
    assert second["case_id"] == "CASE-WS"


def test_event_processing_rejects_unknown_case():
    event = DemoEventProvider().get_events("CASE-MISSING")[0]

    with pytest.raises(ValueError, match="Case not found"):
        EventProcessingService().process(event)
