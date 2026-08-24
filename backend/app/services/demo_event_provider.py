from __future__ import annotations

from datetime import datetime, timezone

from app.models.investigation_event import InvestigationEvent
from app.services.event_adapter import EventProvider


class DemoEventProvider(EventProvider):
    """Deterministic synthetic event source for the dashboard demonstration."""

    name = "SYNTHETIC_DEMO"

    def get_events(self, case_id: str) -> list[InvestigationEvent]:
        created_at = datetime(2024, 1, 5, 9, tzinfo=timezone.utc)
        return [
            InvestigationEvent(
                event_id=f"demo-event-{case_id}-001",
                case_id=case_id,
                chain="ethereum",
                event_type="new_transaction",
                transaction_ref="demo-eth-005",
                wallet="0x1111111111111111111111111111111111111111",
                timestamp=datetime(2024, 1, 5, 8, tzinfo=timezone.utc),
                payload={
                    "from": "0x1111111111111111111111111111111111111111",
                    "to": "0x3333333333333333333333333333333333333333",
                    "value": "200000000000000000",
                    "token": "ETH",
                    "block": 18000200,
                },
                source=self.name,
                created_at=created_at,
            ),
            InvestigationEvent(
                event_id=f"demo-event-{case_id}-002",
                case_id=case_id,
                chain="ethereum",
                event_type="analysis_update",
                transaction_ref=None,
                wallet="0x1111111111111111111111111111111111111111",
                timestamp=created_at,
                payload={"message": "Synthetic demo event stream available."},
                source=self.name,
                created_at=created_at,
            ),
        ]