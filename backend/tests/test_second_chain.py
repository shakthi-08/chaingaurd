import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Transaction
from app.services.demo_provider import DemoBlockchainProvider
from app.services.transaction_graph_service import TransactionGraphService
from app.services.transaction_normalizer import normalize_transaction_record
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)
POLYGON_WALLET = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_second_chain_provider_returns_deterministic_synthetic_activity():
    provider = DemoBlockchainProvider("polygon")
    first = provider.get_wallet_activity(POLYGON_WALLET)
    second = DemoBlockchainProvider("polygon").get_wallet_activity(POLYGON_WALLET)

    assert first == second
    assert len(first) == 1
    assert first[0]["chain"] == "polygon"
    assert first[0]["synthetic"] is True


def test_normalization_preserves_chain_identity():
    normalized = normalize_transaction_record({
        "tx_hash": "polygon-tx",
        "from": POLYGON_WALLET,
        "to": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "value": "10",
        "token": "MATIC",
        "timestamp": "2024-02-02T10:00:00Z",
        "block": 10,
        "chain": "polygon",
    })

    assert normalized["chain"] == "polygon"
    assert normalized["timestamp"].tzinfo is not None


def test_second_chain_ingestion_persists_chain_and_api_returns_it():
    result = WalletIngestionService().ingest_wallet("CASE-POLYGON-01", POLYGON_WALLET, "polygon")

    assert result["chain"] == "polygon"
    with SessionLocal() as session:
        transaction = session.query(Transaction).filter(Transaction.tx_hash == "demo-polygon-001").one()
        assert transaction.chain == "polygon"

    response = client.get("/cases/CASE-POLYGON-01/transactions")
    assert response.status_code == 200
    assert response.json()[0]["chain"] == "polygon"


def test_second_chain_is_graph_compatible():
    service = WalletIngestionService()
    service.ingest_wallet("CASE-POLYGON-GRAPH", POLYGON_WALLET, "polygon")
    graph = TransactionGraphService().build_case_graph("CASE-POLYGON-GRAPH")

    assert {node["id"] for node in graph["nodes"]} == {
        POLYGON_WALLET,
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }
    assert graph["edges"][0]["chain"] == "polygon"


def test_unsupported_chain_is_rejected():
    with pytest.raises(ValueError, match="Unsupported chain"):
        DemoBlockchainProvider("bitcoin")
    with pytest.raises(ValueError, match="Unsupported chain"):
        WalletIngestionService().ingest_wallet("CASE-BAD-CHAIN", POLYGON_WALLET, "bitcoin")


def test_primary_chain_remains_default_and_supported():
    provider = DemoBlockchainProvider()
    records = provider.get_wallet_activity("0x1111111111111111111111111111111111111111")

    assert provider.chain == "ethereum"
    assert records
    assert all(record["chain"] == "ethereum" for record in records)
