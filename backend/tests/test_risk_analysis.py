from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import Transaction
from app.services.risk_analysis_service import RiskAnalysisService
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


def risk_transactions():
    return [
        make_transaction("in-1", "source-1", "hub", 100, "2024-01-01T00:00:00"),
        make_transaction("in-2", "source-2", "hub", 90, "2024-01-01T01:00:00"),
        make_transaction("forward", "hub", "next", 180, "2024-01-01T02:00:00"),
        make_transaction("split-1", "splitter", "dest-1", 10, "2024-01-02T00:00:00"),
        make_transaction("split-2", "splitter", "dest-2", 10, "2024-01-02T01:00:00"),
        make_transaction("split-3", "splitter", "dest-3", 10, "2024-01-02T02:00:00"),
        make_transaction("hop-1", "fast", "hop-a", 5, "2024-01-03T00:00:00"),
        make_transaction("hop-2", "hop-a", "hop-b", 5, "2024-01-03T01:00:00"),
    ]


def indicator_types(assessment):
    return {indicator["type"] for indicator in assessment["indicators"]}


def test_all_fraud_patterns_are_detected():
    assessment = RiskAnalysisService().analyze_transactions(risk_transactions())

    assert {
        "rapid_forwarding",
        "fan_in",
        "fan_out",
        "high_hop_velocity",
        "value_fragmentation",
    } <= indicator_types(assessment)


def test_indicators_include_explanations_and_evidence_references():
    assessment = RiskAnalysisService().analyze_transactions(risk_transactions())

    for indicator in assessment["indicators"]:
        assert indicator["explanation"].startswith("Suspicious pattern detected")
        assert indicator["transaction_refs"]
        assert indicator["wallet_addresses"]
        assert indicator["evidence_refs"]
    assert assessment["findings"]


def test_risk_score_and_levels_are_deterministic_and_configurable():
    transactions = risk_transactions()
    low = RiskAnalysisService(weights={pattern: 0 for pattern in {
        "rapid_forwarding", "fan_in", "fan_out", "high_hop_velocity", "value_fragmentation"
    }}).analyze_transactions(transactions)
    high = RiskAnalysisService(weights={pattern: 40 for pattern in {
        "rapid_forwarding", "fan_in", "fan_out", "high_hop_velocity", "value_fragmentation"
    }}).analyze_transactions(transactions)
    repeat = RiskAnalysisService().analyze_transactions(transactions)

    assert low["overall_score"] == 0
    assert low["risk_level"] == "LOW"
    assert high["overall_score"] == 100
    assert high["risk_level"] == "HIGH"
    assert repeat == RiskAnalysisService().analyze_transactions(transactions)


def test_demo_dataset_supports_fan_in_and_fan_out_via_analyze_api():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-RISK-API", "0x1111111111111111111111111111111111111111", "ethereum")
    ingestion.ingest_wallet("CASE-RISK-API", "0x2222222222222222222222222222222222222222", "ethereum")
    ingestion.ingest_wallet("CASE-RISK-API", "0x5555555555555555555555555555555555555555", "ethereum")

    analyze_response = client.post("/cases/CASE-RISK-API/analyze")
    risk_response = client.get("/cases/CASE-RISK-API/risk")

    assert analyze_response.status_code == 200
    assert {"fan_in", "fan_out"} <= indicator_types(analyze_response.json())
    assert risk_response.status_code == 200
    assert risk_response.json() == analyze_response.json()