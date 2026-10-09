from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Case, Transaction, Wallet
from app.services.demo_provider import DemoBlockchainProvider
from app.services.real_provider import RealBlockchainProvider
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


def test_real_provider_case_creation_is_not_marked_synthetic_demo():
    provider = RealBlockchainProvider("ethereum")
    service = WalletIngestionService(provider=provider)

    with patch.object(provider, "get_wallet_activity", return_value=[]):
        result = service.ingest_wallet(
            "CASE-REAL-001",
            "0x0925D347f811d264879271D2905f54309EAcCB93",
            "ethereum",
        )

    assert result["case_id"] == "CASE-REAL-001"
    with service.session_factory() as session:
        case = session.query(Case).filter_by(case_id="CASE-REAL-001").first()
        wallet = session.query(Wallet).filter_by(case_id=case.id).first()
        assert case.complaint_ref != "synthetic-demo-CASE-REAL-001"
        assert "synthetic-demo" not in (wallet.labels or [])
        assert "real" in (wallet.labels or [])


def test_wallet_addresses_are_case_insensitive_for_case_transactions():
    case_id = "CASE-CASE-INSENSITIVE-01"
    with SessionLocal() as session:
        case = Case(case_id=case_id, complaint_ref="case-insensitive", status="open", created_at=datetime.now(timezone.utc))
        session.add(case)
        session.flush()
        session.add(
            Wallet(
                address="0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD",
                chain="ethereum",
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                labels=["real", "ethereum"],
                case=case,
            )
        )
        session.add(
            Transaction(
                tx_hash="0xcaseinsensitivehash",
                chain="ethereum",
                from_address="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                to_address="0x1234567890abcdef1234567890abcdef12345678",
                value="100",
                token="native",
                timestamp=datetime.now(timezone.utc),
                block=123,
            )
        )
        session.commit()

    service = WalletIngestionService()
    transactions = service.get_case_transactions(case_id)
    assert len(transactions) == 1
    assert transactions[0]["from"] == "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"


def test_invalid_wallet_input_raises():
    service = WalletIngestionService()
    try:
        service.ingest_wallet("CASE-BAD", "invalid-address", "ethereum")
        assert False, "Expected ValueError for invalid wallet address"
    except ValueError:
        pass


def test_real_provider_failures_do_not_leave_partial_case_records():
    service = WalletIngestionService(provider=RealBlockchainProvider("ethereum"))

    with patch.object(service.provider, "get_wallet_activity", side_effect=ValueError("API timeout")):
        with pytest.raises(ValueError, match="API timeout"):
            service.ingest_wallet("CASE-REAL-FAIL-01", "0x0925D347f811d264879271D2905f54309EAcCB93", "ethereum")

    with SessionLocal() as session:
        case = session.query(Case).filter_by(case_id="CASE-REAL-FAIL-01").first()
        assert case is None
        assert session.query(Wallet).filter_by(case_id=None).count() == 0


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


def test_default_ingest_depth_does_not_create_counterparty_wallets():
    service = WalletIngestionService()
    result = service.ingest_wallet(
        "CASE-DEPTH-1",
        "0x1111111111111111111111111111111111111111",
        "ethereum",
    )
    assert result["max_hops"] == 1
    wallets = service.get_case_wallets("CASE-DEPTH-1")
    assert len(wallets) == 1
    assert wallets[0]["address"] == "0x1111111111111111111111111111111111111111"
    assert wallets[0]["is_seed"] is True


def test_bounded_multi_hop_ingest_discovers_same_chain_counterparties():
    class GraphProvider(DemoBlockchainProvider):
        def __init__(self) -> None:
            super().__init__("ethereum")
            self.calls: list[str] = []

        def get_wallet_activity(self, wallet_address, *, start_time=None, end_time=None):
            self.calls.append(wallet_address.lower())
            return super().get_wallet_activity(wallet_address, start_time=start_time, end_time=end_time)

    provider = GraphProvider()
    service = WalletIngestionService(provider=provider)
    seed = "0x1111111111111111111111111111111111111111"
    service.ingest_wallet("CASE-DEPTH-2", seed, "ethereum", max_hops=2)

    wallets = {item["address"]: item for item in service.get_case_wallets("CASE-DEPTH-2")}
    assert seed in wallets
    assert wallets[seed]["is_seed"] is True
    assert "0x2222222222222222222222222222222222222222" in wallets
    assert wallets["0x2222222222222222222222222222222222222222"]["is_seed"] is False
    assert seed in provider.calls
    assert len(provider.calls) == len(set(provider.calls))


def test_ingest_skips_zero_and_invalid_counterparties_and_respects_caps():
    class CappedProvider:
        name = "capped"
        chain = "ethereum"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def get_native_transactions(self, wallet_address, **kwargs):
            return self.get_wallet_activity(wallet_address, **kwargs)

        def get_token_transactions(self, wallet_address, **kwargs):
            return []

        def get_wallet_activity(self, wallet_address, *, start_time=None, end_time=None):
            wallet = wallet_address.lower()
            self.calls.append(wallet)
            if wallet == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa":
                counterparties = [f"0x{str(index).zfill(40)}" for index in range(1, 16)]
                counterparties[0] = "0x0000000000000000000000000000000000000000"
                counterparties[1] = "not-an-address"
                return [
                    {
                        "tx_hash": f"cap-{index}",
                        "from": wallet,
                        "to": address,
                        "value": "1",
                        "token": "ETH",
                        "timestamp": "2024-01-02T10:00:00Z",
                        "block": 1,
                        "chain": "ethereum",
                    }
                    for index, address in enumerate(counterparties)
                ]
            return [
                {
                    "tx_hash": f"leaf-{wallet[-4:]}",
                    "from": wallet,
                    "to": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                    "value": "1",
                    "token": "ETH",
                    "timestamp": "2024-01-02T11:00:00Z",
                    "block": 2,
                    "chain": "ethereum",
                }
            ]

    provider = CappedProvider()
    service = WalletIngestionService(provider=provider)
    service.ingest_wallet(
        "CASE-CAPS",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "ethereum",
        max_hops=2,
    )
    wallets = service.get_case_wallets("CASE-CAPS")
    addresses = {item["address"] for item in wallets}
    assert "0x0000000000000000000000000000000000000000" not in addresses
    assert len(wallets) <= 1 + WalletIngestionService.MAX_COUNTERPARTIES_PER_HOP
    assert all(item["chain"] == "ethereum" for item in wallets)


def test_investigation_depth_alias_matches_max_hops():
    service = WalletIngestionService()
    result = service.ingest_wallet(
        "CASE-DEPTH-ALIAS",
        "0x1111111111111111111111111111111111111111",
        "ethereum",
        investigation_depth=1,
    )
    assert result["max_hops"] == 1
