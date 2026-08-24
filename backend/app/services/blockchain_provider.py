from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Iterable


class BlockchainProvider(ABC):
    """Abstract blockchain provider interface for wallet activity ingestion."""

    name: str = "base"
    chain: str = "unknown"

    @abstractmethod
    def get_native_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return native asset transactions for the wallet."""

    @abstractmethod
    def get_token_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return token transfers for the wallet."""

    @abstractmethod
    def get_wallet_activity(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return normalized provider activity records for the wallet."""

    def get_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience method to fetch all wallet activity records."""
        return self.get_wallet_activity(wallet_address, start_time=start_time, end_time=end_time)
