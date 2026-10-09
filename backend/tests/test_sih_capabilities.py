from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import Transaction
from app.services.alert_service import AlertService
from app.services.cross_chain_service import CrossChainService
from app.services.lea_complaint_service import INTEGRATION_DISCLAIMER
from app.services.protocol_detection_service import ProtocolDetectionService
from app.services.protocol_registry import UNKNOWN_CONTRACT, lookup_protocol
from app.services.report_service import ReportService
from app.services.risk_analysis_service import RiskAnalysisService
from app.services.transaction_graph_service import TransactionGraphService
from app.services.transaction_normalizer import normalize_transaction_record
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)

TORNADO = "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc"
UNISWAP = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
POLYGON_BRIDGE = "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf"
WALLET = "0x1111111111111111111111111111111111111111"


def make_tx(tx_hash, source, dest, value="1", chain="ethereum", token="ETH"):
    return Transaction(
        tx_hash=tx_hash,
        chain=chain,
        from_address=source,
        to_address=dest,
        value=str(value),
        token=token,
        timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
        block=10,
        contract_address=None,
        tx_type="native",
    )


def test_multi_chain_normalization_keeps_contract_and_type():
    normalized = normalize_transaction_record(
        {
            "tx_hash": "token-1",
            "from": WALLET,
            "to": UNISWAP,
            "value": "10",
            "token": "USDC",
            "timestamp": "2024-01-02T10:00:00Z",
            "block": 12,
            "chain": "polygon",
            "contract_address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "tx_type": "token",
        }
    )
    assert normalized["chain"] == "polygon"
    assert normalized["contract_address"] == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert normalized["tx_type"] == "token"


def test_unknown_contract_is_not_guessed():
    classified = ProtocolDetectionService.classify_address("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef", "ethereum")
    assert classified["known"] is False
    assert classified["label"] == UNKNOWN_CONTRACT


def test_bridge_defi_and_mixer_detection_use_known_metadata_only():
    detections = ProtocolDetectionService.detect_transactions(
        [
            make_tx("br-1", WALLET, POLYGON_BRIDGE),
            make_tx("df-1", WALLET, UNISWAP),
            make_tx("mx-1", WALLET, TORNADO),
            make_tx("unk-1", WALLET, "0x9999999999999999999999999999999999999999"),
        ]
    )
    categories = {item["category"] for item in detections}
    assert categories == {"bridge", "dex", "mixer"}
    bridge = next(item for item in detections if item["category"] == "bridge")
    assert bridge["destination_confirmed"] is False
    assert "destination not confirmed" in bridge["note"].lower()
    assert lookup_protocol("0x9999999999999999999999999999999999999999", "ethereum") is None


def test_cross_chain_graph_relationships_include_relation_types():
    graph = TransactionGraphService.build_graph(
        [
            make_tx("br-1", WALLET, POLYGON_BRIDGE),
            make_tx("df-1", WALLET, UNISWAP),
            make_tx("mx-1", WALLET, TORNADO),
        ]
    )
    relations = {edge["relation_type"] for edge in graph["edges"]}
    assert {"BRIDGE", "DEFI_INTERACTION", "MIXER"} <= relations
    types = {node["type"] for node in graph["nodes"]}
    assert {"bridge", "defi", "mixer", "wallet"} <= types
    hops = TransactionGraphService.trace_paths_from_transactions(
        [make_tx("br-1", WALLET, POLYGON_BRIDGE)], WALLET, max_hops=1
    )
    assert hops[0]["hop_count"] == 1


def test_fraud_pattern_and_alert_generation():
    txs = [
        make_tx("br-1", WALLET, POLYGON_BRIDGE, "100"),
        make_tx("mx-1", WALLET, TORNADO, "50"),
        make_tx("df-1", WALLET, UNISWAP, "5"),
    ]
    assessment = RiskAnalysisService().analyze_transactions(txs)
    types = {item["type"] for item in assessment["indicators"]}
    assert {"mixer_exposure", "cross_chain_movement", "defi_interaction"} <= types
    alerts = AlertService().generate_for_case(
        "CASE-ALERT-UNIT",
        risk=assessment,
        attributions=[],
        detections=ProtocolDetectionService.detect_transactions(txs),
        transactions=txs,
    )
    categories = {item["category"] for item in alerts}
    assert "MIXER_EXPOSURE" in categories
    assert "CROSS_CHAIN_MOVEMENT" in categories
    assert "DEFI_INTERACTION" in categories


def test_real_mode_does_not_use_demo_bridge_events(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "blockchain_provider", "real")
    ethereum = make_tx("demo-eth-001", WALLET, "0x2222222222222222222222222222222222222222")
    polygon = make_tx(
        "demo-polygon-001",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        chain="polygon",
        token="MATIC",
    )
    assert CrossChainService.correlate_transactions([ethereum, polygon]) == []


def test_ingestion_is_idempotent_by_hash():
    service = WalletIngestionService()
    first = service.ingest_wallet("CASE-INDEX-01", WALLET, "ethereum")
    second = service.ingest_wallet("CASE-INDEX-01", WALLET, "ethereum")
    assert first["stored_transactions"] >= 1
    assert second["stored_transactions"] == 0


def test_lea_complaint_contract_is_integration_ready_not_live():
    payload = {
        "complaint_id": "NCRP-TEST-1",
        "wallet_address": WALLET,
        "blockchain": "ethereum",
        "incident_type": "cyber_fraud",
        "investigation_id": "CASE-LEA-1",
        "status": "accepted",
    }
    created = client.post("/integrations/ncrp/complaints", json=payload)
    assert created.status_code == 200
    body = created.json()
    assert body["live_integration"] is False
    assert "integration-ready" in body["integration"].lower()
    assert INTEGRATION_DISCLAIMER.split(".")[0] in body["integration"]
    fetched = client.get("/integrations/ncrp/complaints/NCRP-TEST-1")
    assert fetched.status_code == 200
    assert fetched.json()["complaint_id"] == "NCRP-TEST-1"
    capabilities = client.get("/integrations/capabilities")
    assert capabilities.json()["live_integration"] is False
    assert "ethereum" in capabilities.json()["operational_chains"]
    assert "bitcoin" in capabilities.json()["architectural_chains"]


def test_unsupported_chain_error_is_clear():
    response = client.post(
        "/cases/CASE-BAD-CHAIN/wallets",
        json={"wallet_address": WALLET, "chain": "bitcoin"},
    )
    assert response.status_code == 400
    assert "Unsupported chain" in response.json()["detail"]


def test_analyze_exposes_alerts_and_report_uses_persisted_data():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-SIH-REPORT", WALLET, "ethereum")
    analyzed = client.post("/cases/CASE-SIH-REPORT/analyze")
    assert analyzed.status_code == 200
    body = analyzed.json()
    assert "alerts" in body
    assert "advanced_indicators" in body
    alerts = client.get("/cases/CASE-SIH-REPORT/alerts")
    assert alerts.status_code == 200
    path, metadata = ReportService().generate("CASE-SIH-REPORT")
    assert path.exists()
    assert metadata["case_id"] == "CASE-SIH-REPORT"


def test_health_lists_operational_versus_architectural_chains():
    payload = client.get("/health").json()
    assert payload["operational_chains"] == ["ethereum", "polygon"]
    assert "bitcoin" in payload["architectural_chains"]
