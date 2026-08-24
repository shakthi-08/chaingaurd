from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models import Transaction
from app.services.transaction_graph_service import TransactionGraphService
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def make_transaction(tx_hash, source, destination, value, timestamp):
    return Transaction(
        tx_hash=tx_hash,
        from_address=source,
        to_address=destination,
        value=str(value),
        token="ETH",
        timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
        block=1,
    )


def graph_transactions():
    return [
        make_transaction("tx-1", "A", "B", "10", "2024-01-01T00:00:00"),
        make_transaction("tx-2", "B", "C", "8", "2024-01-02T00:00:00"),
        make_transaction("tx-3", "C", "D", "6", "2024-01-03T00:00:00"),
        make_transaction("tx-4", "A", "E", "2", "2024-01-04T00:00:00"),
        make_transaction("tx-5", "D", "A", "1", "2024-01-05T00:00:00"),
    ]


def test_graph_creates_unique_nodes_and_edges():
    transactions = graph_transactions()
    graph = TransactionGraphService.build_graph([*transactions, transactions[0]])

    assert {node["id"] for node in graph["nodes"]} == {"A", "B", "C", "D", "E"}
    assert len(graph["edges"]) == 5
    assert graph["edges"][0]["source"] == "A"
    assert graph["edges"][0]["target"] == "B"
    assert graph["edges"][0]["tx_ref"] == "tx-1"
    assert graph["edges"][0]["value"] == "10"


def test_one_hop_and_multi_hop_tracing():
    paths = TransactionGraphService.trace_paths_from_transactions(graph_transactions(), "A", max_hops=4)

    assert any(path["wallets"] == ["A", "B"] for path in paths)
    assert any(path["wallets"] == ["A", "B", "C", "D"] for path in paths)


def test_max_hops_and_cycle_prevention():
    paths = TransactionGraphService.trace_paths_from_transactions(graph_transactions(), "A", max_hops=2)

    assert all(path["hop_count"] <= 2 for path in paths)
    assert all(len(path["wallets"]) == len(set(path["wallets"])) for path in paths)


def test_direction_filtering():
    outgoing = TransactionGraphService.trace_paths_from_transactions(
        graph_transactions(), "A", direction="outgoing", max_hops=1
    )
    incoming = TransactionGraphService.trace_paths_from_transactions(
        graph_transactions(), "A", direction="incoming", max_hops=1
    )

    assert {path["end_wallet"] for path in outgoing} == {"B", "E"}
    assert {path["end_wallet"] for path in incoming} == {"D"}


def test_min_value_and_time_window_filters():
    value_paths = TransactionGraphService.trace_paths_from_transactions(
        graph_transactions(), "A", direction="outgoing", max_hops=1, min_value=Decimal("5")
    )
    time_paths = TransactionGraphService.trace_paths_from_transactions(
        graph_transactions(),
        "A",
        direction="outgoing",
        max_hops=1,
        start_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 3, tzinfo=timezone.utc),
    )

    assert {path["end_wallet"] for path in value_paths} == {"B"}
    assert time_paths == []


def test_path_ranking_prefers_total_value_then_hop_count():
    paths = TransactionGraphService.trace_paths_from_transactions(
        graph_transactions(), "A", direction="outgoing", max_hops=1
    )

    assert paths[0]["end_wallet"] == "B"
    assert [path["rank"] for path in paths] == [1, 2]


def test_graph_and_paths_api():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-GRAPH-API", "0x1111111111111111111111111111111111111111", "ethereum")
    ingestion.ingest_wallet("CASE-GRAPH-API", "0x2222222222222222222222222222222222222222", "ethereum")

    graph_response = client.get("/cases/CASE-GRAPH-API/graph")
    paths_response = client.get(
        "/cases/CASE-GRAPH-API/paths",
        params={
            "start_wallet": "0x1111111111111111111111111111111111111111",
            "max_hops": 2,
            "direction": "outgoing",
        },
    )

    assert graph_response.status_code == 200
    assert {node["id"] for node in graph_response.json()["nodes"]}
    assert graph_response.json()["edges"]
    assert paths_response.status_code == 200
    assert paths_response.json()