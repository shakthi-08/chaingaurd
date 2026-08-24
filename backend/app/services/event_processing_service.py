from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import Case, Transaction
from app.models.investigation_event import InvestigationEvent
from app.services.demo_provider import DemoBlockchainProvider


class EventProcessingService:
    VALID_EVENT_TYPES = {"new_transaction", "analysis_update", "risk_update", "attribution_update"}

    def __init__(self, session_factory=SessionLocal) -> None:
        self.session_factory = session_factory
        init_db()

    @classmethod
    def validate(cls, event: InvestigationEvent) -> InvestigationEvent:
        if not event.case_id.strip():
            raise ValueError("case_id is required")
        if event.chain not in DemoBlockchainProvider.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {event.chain}")
        if event.event_type not in cls.VALID_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {event.event_type}")
        if event.event_type == "new_transaction" and not event.transaction_ref:
            raise ValueError("transaction_ref is required for new_transaction events")
        if not isinstance(event.timestamp, datetime):
            raise ValueError("timestamp must be a datetime")
        if not re.fullmatch(r"[^\s|]+", event.event_id):
            raise ValueError("event_id is invalid")
        return event

    def process(self, event: InvestigationEvent) -> InvestigationEvent:
        event = self.validate(event)
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == event.case_id).first()
            if case is None:
                raise ValueError("Case not found")
            if event.event_type == "new_transaction":
                self._process_transaction(session, event)
            session.commit()
        return event

    @staticmethod
    def _process_transaction(session: Session, event: InvestigationEvent) -> None:
        if session.query(Transaction).filter(Transaction.tx_hash == event.transaction_ref).first() is not None:
            return
        payload = event.payload
        required = {"from", "to", "value", "token", "block"}
        if not required.issubset(payload):
            raise ValueError("new_transaction payload is missing transaction fields")
        session.add(Transaction(
            tx_hash=event.transaction_ref,
            chain=event.chain,
            from_address=str(payload["from"]),
            to_address=str(payload["to"]),
            value=str(payload["value"]),
            token=str(payload["token"]),
            timestamp=event.timestamp.astimezone(timezone.utc),
            block=int(payload["block"]),
        ))