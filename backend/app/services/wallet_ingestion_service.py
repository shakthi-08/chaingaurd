from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Case, Transaction, Wallet
from app.services.blockchain_provider import BlockchainProvider
from app.services.demo_provider import DemoBlockchainProvider
from app.services.transaction_normalizer import normalize_transaction_record


class WalletIngestionService:
    def __init__(
        self,
        provider: BlockchainProvider | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.provider = provider or DemoBlockchainProvider()
        self.session_factory = session_factory
        init_db()

    @staticmethod
    def validate_wallet_address(wallet_address: str) -> str:
        normalized = wallet_address.strip()
        if not normalized:
            raise ValueError("Wallet address is required.")
        if not re.fullmatch(r"^0x[0-9a-fA-F]+$", normalized):
            raise ValueError("Wallet address must be a valid hexadecimal address starting with 0x.")
        return normalized

    def _get_or_create_case(self, session: Session, case_id: str) -> Case:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is not None:
            return case

        case = Case(
            case_id=case_id,
            complaint_ref=f"synthetic-demo-{case_id}",
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        session.add(case)
        session.flush()
        return case

    def _get_or_create_wallet(self, session: Session, case: Case, wallet_address: str, chain: str) -> Wallet:
        wallet = (
            session.query(Wallet)
            .filter(Wallet.case_id == case.id, Wallet.address == wallet_address)
            .first()
        )
        if wallet is not None:
            wallet.chain = chain
            wallet.labels = ["synthetic-demo", chain]
            wallet.last_seen = datetime.now(timezone.utc)
            return wallet

        wallet = Wallet(
            address=wallet_address,
            chain=chain,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            labels=["synthetic-demo", chain],
            case=case,
        )
        session.add(wallet)
        session.flush()
        return wallet

    def ingest_wallet(
        self,
        case_id: str,
        wallet_address: str,
        chain: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        init_db()
        wallet_address = self.validate_wallet_address(wallet_address)
        normalized_chain = chain.strip().lower()
        if normalized_chain not in DemoBlockchainProvider.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")

        provider = self.provider
        if isinstance(provider, DemoBlockchainProvider) and provider.chain != normalized_chain:
            provider = DemoBlockchainProvider(normalized_chain)

        with self.session_factory() as session:
            case = self._get_or_create_case(session, case_id)
            wallet = self._get_or_create_wallet(session, case, wallet_address, chain)

            records = provider.get_wallet_activity(
                wallet_address,
                start_time=start_time,
                end_time=end_time,
            )

            normalized = [normalize_transaction_record(record) for record in records]
            stored_count = 0

            for tx in normalized:
                existing = session.query(Transaction).filter(Transaction.tx_hash == tx["tx_hash"]).first()
                if existing is not None:
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
                    )
                )
                stored_count += 1

            session.commit()

            return {
                "case_id": case.case_id,
                "wallet_address": wallet.address,
                "chain": wallet.chain,
                "stored_transactions": stored_count,
                "transaction_count": len(normalized),
            }

    def get_case_transactions(self, case_id: str) -> list[dict[str, Any]]:
        init_db()
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return []

            wallet_addresses = [wallet.address for wallet in case.wallets]
            if not wallet_addresses:
                return []

            transactions = (
                session.query(Transaction)
                .filter(
                    (Transaction.from_address.in_(wallet_addresses))
                    | (Transaction.to_address.in_(wallet_addresses))
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
                }
                for tx in transactions
            ]
