from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.blockchain_provider import BlockchainProvider


class DemoBlockchainProvider(BlockchainProvider):
    """Deterministic synthetic provider used to run the MVP without external API keys."""

    name = "demo"
    SUPPORTED_CHAINS = {"ethereum", "polygon"}

    def __init__(self, chain: str = "ethereum") -> None:
        normalized_chain = chain.strip().lower()
        if normalized_chain not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")
        self.chain = normalized_chain

    DEMO_TRANSACTIONS: list[dict[str, Any]] = [
        {
            "tx_hash": "demo-eth-001",
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "value": "1500000000000000000",
            "token": "ETH",
            "timestamp": "2024-01-02T10:00:00Z",
            "block": 18000001,
            "source": "demo",
            "synthetic": True,
        },
        {
            "tx_hash": "demo-eth-002",
            "from": "0x2222222222222222222222222222222222222222",
            "to": "0x3333333333333333333333333333333333333333",
            "value": "500000000000000000",
            "token": "ETH",
            "timestamp": "2024-01-03T12:30:00Z",
            "block": 18000015,
            "source": "demo",
            "synthetic": True,
        },
        {
            "tx_hash": "demo-usdc-003",
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x4444444444444444444444444444444444444444",
            "value": "2500000",
            "token": "USDC",
            "timestamp": "2024-01-04T08:45:00Z",
            "block": 18000120,
            "source": "demo",
            "synthetic": True,
        },
        {
            "tx_hash": "demo-eth-004",
            "from": "0x5555555555555555555555555555555555555555",
            "to": "0x2222222222222222222222222222222222222222",
            "value": "300000000000000000",
            "token": "ETH",
            "timestamp": "2024-01-02T11:00:00Z",
            "block": 18000005,
            "source": "demo",
            "synthetic": True,
        },
    ]
    SECONDARY_TRANSACTIONS: list[dict[str, Any]] = [
        {
            "tx_hash": "demo-polygon-001",
            "from": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "to": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "value": "1500000000000000000",
            "token": "MATIC",
            "timestamp": "2024-01-02T10:30:00Z",
            "block": 52000001,
            "chain": "polygon",
            "source": "demo",
            "synthetic": True,
        },
        {
            "tx_hash": "demo-polygon-002",
            "from": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "to": "0xcccccccccccccccccccccccccccccccccccccccc",
            "value": "700000000000000000",
            "token": "MATIC",
            "timestamp": "2024-01-03T12:30:00Z",
            "block": 52000020,
            "chain": "polygon",
            "source": "demo",
            "synthetic": True,
        },
    ]

    def _parse_time_range(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        records = []
        transactions = self.DEMO_TRANSACTIONS if self.chain == "ethereum" else self.SECONDARY_TRANSACTIONS
        for transaction in transactions:
            if transaction["from"] != wallet_address and transaction["to"] != wallet_address:
                continue

            ts = datetime.fromisoformat(transaction["timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc)
            if start_time and ts < start_time.astimezone(timezone.utc):
                continue
            if end_time and ts > end_time.astimezone(timezone.utc):
                continue
            record = dict(transaction)
            record["chain"] = self.chain
            record["synthetic"] = True
            records.append(record)

        return records

    def get_native_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        return [
            tx for tx in self._parse_time_range(wallet_address, start_time=start_time, end_time=end_time)
            if tx.get("token") in {"ETH", "MATIC", "BTC", None}
        ]

    def get_token_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        return [
            tx for tx in self._parse_time_range(wallet_address, start_time=start_time, end_time=end_time)
            if tx.get("token") and tx.get("token") not in {"ETH", "MATIC", "BTC", None}
        ]

    def get_wallet_activity(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        return self._parse_time_range(wallet_address, start_time=start_time, end_time=end_time)
