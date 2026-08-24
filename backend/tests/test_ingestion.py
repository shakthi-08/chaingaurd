from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_provider import DemoBlockchainProvider
from app.services.transaction_normalizer import normalize_transaction_record
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def test_provider_interface_returns_demo_activity():
    provider = DemoBlockchainProvider()
    data = provider.get_wallet_activity("0x1111111111111111111111111111111111111111")
    assert isinstance(data, list)
    assert data
    assert all("tx_hash" in item for item in data)
    assert all(item.get("synthetic") is True for item in data)


def test_normalization_returns_utc_timestamp():
    record = {
        "tx_hash": "demo-tx-1",
        "from": "0x1111111111111111111111111111111111111111",
        "to": "0x2222222222222222222222222222222222222222",
        "value": "100",
        "token": "ETH",
        "timestamp": "2024-01-02T10:00:00Z",
        "block": 123,
    }
    normalized = normalize_transaction_record(record)
    assert normalized["timestamp"].tzinfo is not None
    assert normalized["timestamp"].utcoffset() == timezone.utc.utcoffset(datetime.now())


def test_wallet_ingestion_service_stores_transactions():
    service = WalletIngestionService()
    result = service.ingest_wallet(
        "CASE-INGEST-01",
        "0x1111111111111111111111111111111111111111",
        "ethereum",
    )

    assert result["stored_transactions"] >= 1
    assert result["wallet_address"] == "0x1111111111111111111111111111111111111111"


def test_invalid_wallet_input_raises():
    service = WalletIngestionService()
    try:
        service.ingest_wallet("CASE-BAD", "invalid-address", "ethereum")
        assert False, "Expected ValueError for invalid wallet address"
    except ValueError:
        pass


def test_empty_transaction_results_are_handled():
    provider = DemoBlockchainProvider()
    records = provider.get_wallet_activity("0xdeadbeef")
    assert records == []


def test_case_wallet_endpoint_ingests_transactions():
    payload = {"wallet_address": "0x1111111111111111111111111111111111111111", "chain": "ethereum"}
    response = client.post("/cases/CASE-API-01/wallets", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "CASE-API-01"
    assert body["stored_transactions"] >= 1

    transactions = client.get("/cases/CASE-API-01/transactions")
    assert transactions.status_code == 200
    payload = transactions.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
