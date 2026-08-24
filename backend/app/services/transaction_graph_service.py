from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Case, GraphEdge, Transaction


class TransactionGraphService:
    DEFAULT_MAX_HOPS = 4
    VALID_DIRECTIONS = {"incoming", "outgoing", "both"}

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory
        init_db()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _as_decimal(value: str | int | float | Decimal) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @classmethod
    def _case_transactions(cls, session: Session, case_id: str) -> list[Transaction]:
        case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            return []

        wallet_addresses = [wallet.address for wallet in case.wallets]
        if not wallet_addresses:
            return []

        return (
            session.query(Transaction)
            .filter(
                (Transaction.from_address.in_(wallet_addresses))
                | (Transaction.to_address.in_(wallet_addresses))
            )
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
            .all()
        )

    @classmethod
    def build_graph(cls, transactions: Iterable[Transaction]) -> dict[str, Any]:
        nodes: set[str] = set()
        edges: list[dict[str, Any]] = []
        seen_transactions: set[str] = set()

        for transaction in transactions:
            nodes.add(transaction.from_address)
            nodes.add(transaction.to_address)
            if transaction.tx_hash in seen_transactions:
                continue
            seen_transactions.add(transaction.tx_hash)
            edges.append(
                {
                    "id": transaction.tx_hash,
                    "source": transaction.from_address,
                    "target": transaction.to_address,
                    "tx_ref": transaction.tx_hash,
                    "chain": transaction.chain,
                    "value": transaction.value,
                    "timestamp": cls._as_utc(transaction.timestamp).isoformat(),
                    "token": transaction.token,
                }
            )

        return {
            "nodes": [{"id": address, "type": "wallet"} for address in sorted(nodes)],
            "edges": edges,
            "transactions": edges,
        }

    @classmethod
    def _filtered_transactions(
        cls,
        transactions: Iterable[Transaction],
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        min_value: Decimal | None,
    ) -> list[Transaction]:
        start = cls._as_utc(start_time) if start_time else None
        end = cls._as_utc(end_time) if end_time else None
        filtered = []
        for transaction in transactions:
            timestamp = cls._as_utc(transaction.timestamp)
            if start and timestamp < start:
                continue
            if end and timestamp > end:
                continue
            if min_value is not None and cls._as_decimal(transaction.value) < min_value:
                continue
            filtered.append(transaction)
        return filtered

    @classmethod
    def trace_paths_from_transactions(
        cls,
        transactions: Iterable[Transaction],
        start_wallet: str,
        *,
        direction: str = "both",
        max_hops: int = DEFAULT_MAX_HOPS,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_value: Decimal | None = None,
    ) -> list[dict[str, Any]]:
        if direction not in cls.VALID_DIRECTIONS:
            raise ValueError("direction must be incoming, outgoing, or both")
        if max_hops < 1:
            raise ValueError("max_hops must be at least 1")

        filtered = cls._filtered_transactions(
            transactions,
            start_time=start_time,
            end_time=end_time,
            min_value=min_value,
        )
        adjacency: dict[str, list[tuple[str, Transaction]]] = defaultdict(list)
        for transaction in filtered:
            if direction in {"outgoing", "both"}:
                adjacency[transaction.from_address].append((transaction.to_address, transaction))
            if direction in {"incoming", "both"}:
                adjacency[transaction.to_address].append((transaction.from_address, transaction))

        paths: list[dict[str, Any]] = []
        seen_paths: set[tuple[str, ...]] = set()

        def visit(current: str, wallets: list[str], path_transactions: list[Transaction]) -> None:
            if len(path_transactions) >= max_hops:
                return
            for next_wallet, transaction in adjacency.get(current, []):
                if next_wallet in wallets:
                    continue
                transaction_sequence = tuple(item.tx_hash for item in (*path_transactions, transaction))
                if transaction_sequence in seen_paths:
                    continue
                seen_paths.add(transaction_sequence)
                next_wallets = [*wallets, next_wallet]
                next_transactions = [*path_transactions, transaction]
                timestamps = [cls._as_utc(item.timestamp).isoformat() for item in next_transactions]
                total_value = sum((cls._as_decimal(item.value) for item in next_transactions), Decimal("0"))
                paths.append(
                    {
                        "start_wallet": start_wallet,
                        "end_wallet": next_wallet,
                        "wallets": next_wallets,
                        "transactions": list(transaction_sequence),
                        "hop_count": len(next_transactions),
                        "total_value": str(total_value),
                        "values": [item.value for item in next_transactions],
                        "timestamps": timestamps,
                    }
                )
                visit(next_wallet, next_wallets, next_transactions)

        visit(start_wallet, [start_wallet], [])
        paths.sort(
            key=lambda path: (
                -cls._as_decimal(path["total_value"]),
                -(
                    datetime.fromisoformat(max(path["timestamps"])).timestamp()
                    if path["timestamps"]
                    else float("-inf")
                ),
                path["hop_count"],
            )
        )
        for rank, path in enumerate(paths, start=1):
            path["rank"] = rank
        return paths

    def build_case_graph(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            transactions = self._case_transactions(session, case_id)
            graph = self.build_graph(transactions)
            existing_edges = {
                edge.tx_ref for edge in session.query(GraphEdge).filter(GraphEdge.tx_ref.in_([tx.tx_hash for tx in transactions])).all()
            }
            for transaction in transactions:
                if transaction.tx_hash in existing_edges:
                    continue
                session.add(
                    GraphEdge(
                        source=transaction.from_address,
                        destination=transaction.to_address,
                        tx_ref=transaction.tx_hash,
                        chain=transaction.chain,
                        value=transaction.value,
                        timestamp=transaction.timestamp,
                    )
                )
            session.commit()
            from app.services.cross_chain_service import CrossChainService

            graph["cross_chain"] = CrossChainService(self.session_factory).case_movements(case_id)
            return graph

    def trace_case_paths(
        self,
        case_id: str,
        start_wallet: str,
        *,
        direction: str = "both",
        max_hops: int = DEFAULT_MAX_HOPS,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_value: Decimal | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            transactions = self._case_transactions(session, case_id)
            return self.trace_paths_from_transactions(
                transactions,
                start_wallet,
                direction=direction,
                max_hops=max_hops,
                start_time=start_time,
                end_time=end_time,
                min_value=min_value,
            )