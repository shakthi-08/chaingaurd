from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import is_demo_mode_enabled, is_real_mode_enabled, settings
from app.database import SessionLocal
from app.models import Case, Transaction, Wallet
from app.services.blockchain_provider import BlockchainProvider
from app.services.case_lifecycle import set_case_stage
from app.services.demo_provider import DemoBlockchainProvider
from app.services.real_provider import RealBlockchainProvider
from app.services.transaction_normalizer import normalize_transaction_record
from app.services.protocol_registry import OPERATIONAL_CHAINS

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
SEED_LABELS = {"seed", "reported"}


class WalletIngestionService:
    SUPPORTED_CHAINS = set(OPERATIONAL_CHAINS)
    MAX_INGEST_HOPS = 3
    MAX_VISITED_WALLETS = 25
    MAX_COUNTERPARTIES_PER_HOP = 10

    def __init__(
        self,
        provider: BlockchainProvider | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.provider = provider or self._get_configured_provider()
        self.session_factory = session_factory

    @staticmethod
    def _get_configured_provider() -> BlockchainProvider:
        """Get blockchain provider based on configuration."""
        provider_type = (settings.blockchain_provider or "").strip().lower()

        if provider_type == "real":
            if not settings.etherscan_api_key and not settings.polygonscan_api_key:
                raise ValueError("Real mode requires blockchain API keys to be configured.")
            return RealBlockchainProvider()

        if provider_type == "demo":
            return DemoBlockchainProvider()

        if is_demo_mode_enabled():
            return DemoBlockchainProvider()

        if is_real_mode_enabled():
            if not settings.etherscan_api_key and not settings.polygonscan_api_key:
                raise ValueError("Real mode requires blockchain API keys to be configured.")
            return RealBlockchainProvider()

        raise ValueError("No supported blockchain provider is configured. Set BLOCKCHAIN_PROVIDER to 'demo' or 'real'.")

    @staticmethod
    def validate_wallet_address(wallet_address: str) -> str:
        normalized = wallet_address.strip().lower()
        if not normalized:
            raise ValueError("Wallet address is required.")
        if not re.fullmatch(r"^0x[0-9a-f]+$", normalized):
            raise ValueError("Wallet address must be a valid hexadecimal address starting with 0x.")
        return normalized

    @classmethod
    def is_valid_counterparty(cls, wallet_address: str) -> bool:
        try:
            normalized = cls.validate_wallet_address(wallet_address)
        except ValueError:
            return False
        if normalized == ZERO_ADDRESS:
            return False
        if set(normalized[2:]) == {"0"}:
            return False
        return True

    def _provider_for_chain(self, chain: str) -> BlockchainProvider:
        provider = self.provider
        if provider.chain == chain:
            return provider
        if isinstance(provider, RealBlockchainProvider):
            return RealBlockchainProvider(chain)
        if isinstance(provider, DemoBlockchainProvider):
            return DemoBlockchainProvider(chain)
        return provider

    def _is_real_provider(self, provider: BlockchainProvider | None = None) -> bool:
        return isinstance(provider or self.provider, RealBlockchainProvider)

    def _wallet_labels(self, chain: str, *, is_seed: bool, hop: int, provider: BlockchainProvider | None = None) -> list[str]:
        base = ["real", chain] if self._is_real_provider(provider) else ["synthetic-demo", chain]
        if is_seed:
            return [*base, "seed", "reported"]
        return [*base, "discovered", f"hop:{hop}"]

    def _get_or_create_case(self, session: Session, case_id: str, provider: BlockchainProvider | None = None) -> Case:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is not None:
            return case

        case = Case(
            case_id=case_id,
            complaint_ref=(
                f"real-{case_id}" if self._is_real_provider(provider) else f"synthetic-demo-{case_id}"
            ),
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        session.add(case)
        session.flush()
        return case

    def _get_or_create_wallet(
        self,
        session: Session,
        case: Case,
        wallet_address: str,
        chain: str,
        *,
        is_seed: bool,
        hop: int,
        provider: BlockchainProvider | None = None,
    ) -> Wallet:
        normalized_wallet = wallet_address.strip().lower()
        wallet = (
            session.query(Wallet)
            .filter(Wallet.case_id == case.id)
            .filter(func.lower(Wallet.address) == normalized_wallet)
            .first()
        )
        existing_labels = set(wallet.labels or []) if wallet is not None else set()
        preserve_seed = bool(existing_labels & SEED_LABELS) or is_seed
        labels = self._wallet_labels(chain, is_seed=preserve_seed, hop=0 if preserve_seed else hop, provider=provider)

        if wallet is not None:
            wallet.address = normalized_wallet
            if preserve_seed:
                wallet.chain = chain if not wallet.chain else wallet.chain
            else:
                wallet.chain = chain
            wallet.labels = labels
            wallet.last_seen = datetime.now(timezone.utc)
            return wallet

        wallet = Wallet(
            address=normalized_wallet,
            chain=chain,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            labels=labels,
            case=case,
        )
        session.add(wallet)
        session.flush()
        return wallet

    def _fetch_activity(
        self,
        provider: BlockchainProvider,
        wallet_address: str,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[dict[str, Any]]:
        try:
            records = provider.get_wallet_activity(
                wallet_address,
                start_time=start_time,
                end_time=end_time,
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Unable to fetch wallet activity for {wallet_address}: {exc}") from exc
        return records if isinstance(records, list) else []

    @staticmethod
    def _normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for record in records:
            if not isinstance(record, dict):
                continue
            tx_hash = str(record.get("tx_hash", "")).strip()
            if not tx_hash:
                continue
            try:
                normalized.append(normalize_transaction_record(record))
            except (KeyError, TypeError, ValueError):
                continue
        return normalized

    def _store_transactions(self, session: Session, normalized: list[dict[str, Any]]) -> int:
        if not normalized:
            return 0
        hashes = [tx["tx_hash"] for tx in normalized]
        existing = {
            row[0]
            for row in session.query(Transaction.tx_hash).filter(Transaction.tx_hash.in_(hashes)).all()
        }
        stored_count = 0
        for tx in normalized:
            if tx["tx_hash"] in existing:
                continue
            session.add(
                Transaction(
                    tx_hash=tx["tx_hash"],
                    chain=tx["chain"],
                    from_address=tx["from_address"],
                    to_address=tx["to_address"],
                    value=tx["value"],
                    token=tx["token"],
                    timestamp=tx["timestamp"],
                    block=tx["block"],
                    contract_address=tx.get("contract_address"),
                    tx_type=tx.get("tx_type"),
                )
            )
            existing.add(tx["tx_hash"])
            stored_count += 1
        return stored_count

    def _new_counterparties(self, normalized: list[dict[str, Any]], *, visited: set[tuple[str, str]], chain: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for tx in normalized:
            for address in (tx["from_address"], tx["to_address"]):
                if address in seen or not self.is_valid_counterparty(address):
                    continue
                if (address, chain) in visited:
                    continue
                seen.add(address)
                found.append(address)
        return found[: self.MAX_COUNTERPARTIES_PER_HOP]

    @staticmethod
    def _clamp_hops(max_hops: int | None, investigation_depth: int | None) -> int:
        depth = investigation_depth if investigation_depth is not None else max_hops
        if depth is None:
            return 1
        return max(1, min(int(depth), WalletIngestionService.MAX_INGEST_HOPS))

    def ingest_wallet(
        self,
        case_id: str,
        wallet_address: str,
        chain: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_hops: int | None = None,
        investigation_depth: int | None = None,
    ) -> dict[str, Any]:
        wallet_address = self.validate_wallet_address(wallet_address)
        normalized_chain = chain.strip().lower()
        if normalized_chain not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")

        ingest_hops = self._clamp_hops(max_hops, investigation_depth)
        provider = self._provider_for_chain(normalized_chain)
        hop_errors: list[dict[str, str]] = []
        truncated = False

        try:
            seed_records = self._fetch_activity(
                provider,
                wallet_address,
                start_time=start_time,
                end_time=end_time,
            )
        except ValueError:
            raise

        truncated = any(bool(item.get("truncated")) for item in seed_records if isinstance(item, dict))
        seed_normalized = self._normalize_records(seed_records)
        visited: set[tuple[str, str]] = {(wallet_address, normalized_chain)}
        wallets_ingested = 1

        with self.session_factory() as session:
            case = self._get_or_create_case(session, case_id, provider)
            case.current_stage = "INGESTING"
            case.progress = 10
            case.error_message = None
            case.status = "open"
            wallet = self._get_or_create_wallet(
                session,
                case,
                wallet_address,
                normalized_chain,
                is_seed=True,
                hop=0,
                provider=provider,
            )
            stored_count = self._store_transactions(session, seed_normalized)
            session.commit()
            persisted_case_id = case.case_id
            persisted_wallet = wallet.address
            persisted_chain = wallet.chain

        frontier = seed_normalized
        hop = 1
        while hop < ingest_hops and len(visited) < self.MAX_VISITED_WALLETS:
            candidates = self._new_counterparties(frontier, visited=visited, chain=normalized_chain)
            next_frontier: list[dict[str, Any]] = []
            hop_batch: list[tuple[str, list[dict[str, Any]]]] = []
            for address in candidates:
                if len(visited) >= self.MAX_VISITED_WALLETS:
                    break
                if (address, normalized_chain) in visited:
                    continue
                visited.add((address, normalized_chain))
                try:
                    hop_records = self._fetch_activity(
                        provider,
                        address,
                        start_time=start_time,
                        end_time=end_time,
                    )
                except ValueError as exc:
                    hop_errors.append({"wallet": address, "error": str(exc), "hop": str(hop)})
                    continue
                truncated = truncated or any(bool(item.get("truncated")) for item in hop_records if isinstance(item, dict))
                hop_normalized = self._normalize_records(hop_records)
                hop_batch.append((address, hop_normalized))
                next_frontier.extend(hop_normalized)

            if hop_batch:
                with self.session_factory() as session:
                    case = session.query(Case).filter(Case.case_id == persisted_case_id).first()
                    if case is None:
                        break
                    for address, hop_normalized in hop_batch:
                        self._get_or_create_wallet(
                            session,
                            case,
                            address,
                            normalized_chain,
                            is_seed=False,
                            hop=hop,
                            provider=provider,
                        )
                        stored_count += self._store_transactions(session, hop_normalized)
                        wallets_ingested += 1
                    session.commit()
            frontier = next_frontier
            hop += 1

        set_case_stage(persisted_case_id, "INGESTED", session_factory=self.session_factory)
        return {
            "case_id": persisted_case_id,
            "wallet_address": persisted_wallet,
            "chain": persisted_chain,
            "stored_transactions": stored_count,
            "transaction_count": len(seed_normalized),
            "max_hops": ingest_hops,
            "wallets_ingested": wallets_ingested,
            "seed_wallet": True,
            "truncated": truncated,
            "hop_errors": hop_errors,
            "provider_empty": len(seed_normalized) == 0 and not hop_errors,
            "status": "INGESTED",
            "progress": 25,
        }

    def get_case_wallets(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []
            wallets = sorted(case.wallets, key=lambda item: (0 if (item.labels and SEED_LABELS.intersection(item.labels)) else 1, item.address))
            return [
                {
                    "address": wallet.address,
                    "chain": wallet.chain,
                    "labels": wallet.labels or [],
                    "is_seed": bool(set(wallet.labels or []) & SEED_LABELS),
                    "first_seen": wallet.first_seen.isoformat() if wallet.first_seen else None,
                    "last_seen": wallet.last_seen.isoformat() if wallet.last_seen else None,
                }
                for wallet in wallets
            ]

    def get_case_transactions(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []

            wallet_addresses = {wallet.address.lower() for wallet in case.wallets}
            if not wallet_addresses:
                return []

            transactions = (
                session.query(Transaction)
                .filter(
                    func.lower(Transaction.from_address).in_(wallet_addresses)
                    | func.lower(Transaction.to_address).in_(wallet_addresses)
                )
                .order_by(Transaction.timestamp.asc())
                .all()
            )

            return [
                {
                    "tx_hash": tx.tx_hash,
                    "from": tx.from_address,
                    "to": tx.to_address,
                    "value": tx.value,
                    "token": tx.token,
                    "chain": tx.chain,
                    "timestamp": tx.timestamp.isoformat(),
                    "block": tx.block,
                    "contract_address": getattr(tx, "contract_address", None),
                    "tx_type": getattr(tx, "tx_type", None),
                }
                for tx in transactions
            ]
