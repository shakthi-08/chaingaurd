from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Case, Transaction, Wallet
from app.services.cross_chain_service import CrossChainService
from app.services.demo_provider import DemoBlockchainProvider
from app.services.transaction_normalizer import normalize_transaction_record
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)
ETH_WALLET = "0x1111111111111111111111111111111111111111"
POLYGON_WALLET = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def transaction_from_record(record):
    normalized = normalize_transaction_record(record)
    return Transaction(
        tx_hash=normalized["tx_hash"],
        chain=normalized["chain"],
        from_address=normalized["from_address"],
        to_address=normalized["to_address"],
        value=normalized["value"],
        token=normalized["token"],
        timestamp=normalized["timestamp"],
        block=normalized["block"],
    )


def test_demo_bridge_correlates_matching_cross_chain_transactions():
    ethereum = DemoBlockchainProvider("ethereum").get_wallet_activity(ETH_WALLET)[0]
    polygon = DemoBlockchainProvider("polygon").get_wallet_activity(POLYGON_WALLET)[0]
    source = transaction_from_record(ethereum)
    destination = transaction_from_record(polygon)

    result = CrossChainService.correlate_transactions([source, destination])

    assert len(result) == 1
    assert result[0]["source_chain"] == "ethereum"
    assert result[0]["destination_chain"] == "polygon"
    assert result[0]["bridge_service"] == "DEMO-BRIDGE-ALPHA"
    assert result[0]["confidence"] == 98.0
    assert result[0]["evidence_refs"] == ["transaction:demo-eth-001", "transaction:demo-polygon-001"]


def test_unrelated_transaction_is_not_correlated():
    ethereum = DemoBlockchainProvider("ethereum").get_wallet_activity(ETH_WALLET)[0]
    unrelated = dict(DemoBlockchainProvider("polygon").get_wallet_activity(POLYGON_WALLET)[0])
    unrelated["tx_hash"] = "unrelated-polygon"
    unrelated["value"] = "999"
    transactions = [
        transaction_from_record(ethereum),
        transaction_from_record(unrelated),
    ]

    assert CrossChainService.correlate_transactions(transactions) == []


def test_temporal_and_value_matching_are_required():
    ethereum = DemoBlockchainProvider("ethereum").get_wallet_activity(ETH_WALLET)[0]
    polygon = DemoBlockchainProvider("polygon").get_wallet_activity(POLYGON_WALLET)[0]
    source = transaction_from_record(ethereum)
    destination = transaction_from_record(polygon)

    destination.timestamp = datetime(2024, 2, 2, tzinfo=timezone.utc)
    assert CrossChainService.correlate_transactions([source, destination]) == []

    destination.timestamp = datetime.fromisoformat(polygon["timestamp"].replace("Z", "+00:00"))
    destination.value = "123"
    assert CrossChainService.correlate_transactions([source, destination]) == []


def test_cross_chain_api_and_graph_compatibility():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-CROSS-CHAIN", ETH_WALLET, "ethereum")
    ingestion.ingest_wallet("CASE-CROSS-CHAIN", POLYGON_WALLET, "polygon")

    response = client.get("/cases/CASE-CROSS-CHAIN/cross-chain")
    graph = client.get("/cases/CASE-CROSS-CHAIN/graph")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) == 3
    assert len(graph.json()["cross_chain"]) == 1


def test_case_without_cross_chain_movement_returns_empty():
    WalletIngestionService().ingest_wallet("CASE-ETH-ONLY", ETH_WALLET, "ethereum")

    assert client.get("/cases/CASE-ETH-ONLY/cross-chain").json() == []
