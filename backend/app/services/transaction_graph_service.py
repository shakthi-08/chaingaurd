from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Case, GraphEdge, Transaction
from app.services.protocol_registry import node_type_for_address, relation_for_counterparty
from app.services.reference_entity_dataset import REFERENCE_ENTITY_DATASET


_VASP_KEYS = {
    (str(item["known_wallet"]).lower(), str(item.get("chain") or "ethereum").lower())
    for item in REFERENCE_ENTITY_DATASET
    if str(item.get("type") or "").lower() in {"vasp", "exchange"}
}


class TransactionGraphService:
    DEFAULT_MAX_HOPS = 3
    MAX_PATHS = 200
    MAX_NEIGHBORS_PER_NODE = 25
    VALID_DIRECTIONS = {"incoming", "outgoing", "both"}

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory

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

        wallet_addresses = {wallet.address.lower() for wallet in case.wallets}
        if not wallet_addresses:
            return []

        return (
            session.query(Transaction)
            .filter(
                (func.lower(Transaction.from_address).in_(wallet_addresses))
                | (func.lower(Transaction.to_address).in_(wallet_addresses))
            )
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
            .all()
        )

    @classmethod
    def build_graph(cls, transactions: Iterable[Transaction]) -> dict[str, Any]:
        nodes: dict[str, str] = {}
        edges: list[dict[str, Any]] = []
        seen_transactions: set[str] = set()

        for transaction in transactions:
            chain = getattr(transaction, "chain", None) or "ethereum"
            from_type = node_type_for_address(transaction.from_address, chain)
            to_type = node_type_for_address(transaction.to_address, chain)
            nodes[transaction.from_address] = from_type
            nodes[transaction.to_address] = to_type
            if transaction.tx_hash in seen_transactions:
                continue
            seen_transactions.add(transaction.tx_hash)
            is_vasp = (transaction.to_address.lower(), chain.lower()) in _VASP_KEYS
            relation = relation_for_counterparty(transaction.to_address, chain, is_vasp=is_vasp)
            if relation == "TRANSFER":
                relation = relation_for_counterparty(
                    transaction.from_address,
                    chain,
                    is_vasp=(transaction.from_address.lower(), chain.lower()) in _VASP_KEYS,
                )
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
                    "relation_type": relation,
                    "contract_address": getattr(transaction, "contract_address", None),
                    "tx_type": getattr(transaction, "tx_type", None),
                }
            )

        return {
            "nodes": [{"id": address, "type": node_type} for address, node_type in sorted(nodes.items())],
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
        max_paths: int | None = None,
        max_neighbors: int | None = None,
    ) -> list[dict[str, Any]]:
        if direction not in cls.VALID_DIRECTIONS:
            raise ValueError("direction must be incoming, outgoing, or both")
        if max_hops < 1:
            raise ValueError("max_hops must be at least 1")

        path_limit = max_paths if max_paths is not None else cls.MAX_PATHS
        neighbor_limit = max_neighbors if max_neighbors is not None else cls.MAX_NEIGHBORS_PER_NODE
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

        for wallet, neighbors in list(adjacency.items()):
            if len(neighbors) > neighbor_limit:
                adjacency[wallet] = neighbors[:neighbor_limit]

        paths: list[dict[str, Any]] = []
        seen_paths: set[tuple[str, ...]] = set()
        truncated = False

        def visit(current: str, wallets: list[str], path_transactions: list[Transaction]) -> None:
            nonlocal truncated
            if len(paths) >= path_limit:
                truncated = True
                return
            if len(path_transactions) >= max_hops:
                return
            for next_wallet, transaction in adjacency.get(current, []):
                if len(paths) >= path_limit:
                    truncated = True
                    return
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
            if truncated:
                path["truncated"] = True
        return paths

    def get_persisted_graph(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                return {"nodes": [], "edges": [], "transactions": [], "cross_chain": [], "persisted": False}
            wallet_addresses = {wallet.address.lower() for wallet in case.wallets}
            transactions = self._case_transactions(session, case_id)
            edges = []
            if transactions:
                tx_hashes = [tx.tx_hash for tx in transactions]
                edges = (
                    session.query(GraphEdge)
                    .filter(GraphEdge.tx_ref.in_(tx_hashes))
                    .order_by(GraphEdge.timestamp.asc(), GraphEdge.id.asc())
                    .all()
                )
            session.expunge_all()

        if edges:
            nodes = {edge.source for edge in edges} | {edge.destination for edge in edges}
            serialized_edges = [
                {
                    "id": edge.tx_ref,
                    "source": edge.source,
                    "target": edge.destination,
                    "tx_ref": edge.tx_ref,
                    "chain": edge.chain,
                    "value": edge.value,
                    "timestamp": self._as_utc(edge.timestamp).isoformat(),
                    "token": None,
                    "relation_type": getattr(edge, "relation_type", None) or "TRANSFER",
                }
                for edge in edges
            ]
            graph = {
                "nodes": [
                    {"id": address, "type": node_type_for_address(address, edges[0].chain if edges else "ethereum")}
                    for address in sorted(nodes)
                ],
                "edges": serialized_edges,
                "transactions": serialized_edges,
                "persisted": True,
            }
        else:
            graph = self.build_graph(transactions)
            graph["persisted"] = False

        from app.services.cross_chain_service import CrossChainService

        try:
            graph["cross_chain"] = CrossChainService(self.session_factory).case_movements(case_id)
        except ValueError:
            graph["cross_chain"] = []
        graph["wallet_count"] = len(wallet_addresses)
        return graph

    def build_case_graph(self, case_id: str) -> dict[str, Any]:
        with self.session_factory() as session:
            transactions = self._case_transactions(session, case_id)
            session.expunge_all()

        graph = self.build_graph(transactions)
        tx_hashes = [tx.tx_hash for tx in transactions]

        with self.session_factory() as session:
            existing_edges: set[str] = set()
            if tx_hashes:
                existing_edges = {
                    edge.tx_ref
                    for edge in session.query(GraphEdge).filter(GraphEdge.tx_ref.in_(tx_hashes)).all()
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
                        relation_type=relation_for_counterparty(
                            transaction.to_address,
                            transaction.chain,
                            is_vasp=(transaction.to_address.lower(), (transaction.chain or "ethereum").lower())
                            in _VASP_KEYS,
                        ),
                    )
                )
            session.commit()

        from app.services.cross_chain_service import CrossChainService

        graph["cross_chain"] = CrossChainService(self.session_factory).case_movements(case_id)
        graph["persisted"] = True
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
            session.expunge_all()
        return self.trace_paths_from_transactions(
            transactions,
            start_wallet,
            direction=direction,
            max_hops=min(max_hops, self.DEFAULT_MAX_HOPS),
            start_time=start_time,
            end_time=end_time,
            min_value=min_value,
            max_paths=self.MAX_PATHS,
            max_neighbors=self.MAX_NEIGHBORS_PER_NODE,
        )
