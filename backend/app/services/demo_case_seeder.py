from __future__ import annotations

from datetime import datetime, timezone

from app.database import SessionLocal, init_db
from app.models import Case, Transaction, Wallet
from app.services.demo_case import DEMO_CASE
from app.services.demo_provider import DemoBlockchainProvider
from app.services.transaction_normalizer import normalize_transaction_record


def seed_demo_case(session_factory=SessionLocal) -> bool:
    """Create the synthetic demo case once; never alter an existing case."""
    init_db()
    with session_factory() as session:
        case_id = DEMO_CASE["case_id"]
        if session.query(Case).filter(Case.case_id == case_id).first() is not None:
            return False

        case = Case(
            case_id=case_id,
            complaint_ref=DEMO_CASE["complaint_ref"],
            status=DEMO_CASE["status"],
            created_at=datetime.fromisoformat(DEMO_CASE["created_at"]),
        )
        session.add(case)
        session.flush()

        records = DemoBlockchainProvider.DEMO_TRANSACTIONS
        addresses = sorted({record["from"] for record in records} | {record["to"] for record in records})
        for address in addresses:
            session.add(
                Wallet(
                    address=address,
                    chain="ethereum",
                    first_seen=case.created_at,
                    last_seen=case.created_at,
                    labels=["DEMO/SAMPLE", "synthetic-demo-wallet"],
                    case=case,
                )
            )

        for record in records:
            normalized = normalize_transaction_record(record)
            if session.query(Transaction).filter(Transaction.tx_hash == normalized["tx_hash"]).first() is not None:
                continue
            session.add(
                Transaction(
                    tx_hash=normalized["tx_hash"],
                    chain=normalized["chain"],
                    from_address=normalized["from_address"],
                    to_address=normalized["to_address"],
                    value=normalized["value"],
                    token=normalized["token"],
                    timestamp=normalized["timestamp"],
                    block=normalized["block"],
                )
            )
        session.commit()
        return True