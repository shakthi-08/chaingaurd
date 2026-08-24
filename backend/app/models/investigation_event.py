from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class InvestigationEvent:
    event_id: str
    case_id: str
    chain: str
    event_type: str
    transaction_ref: str | None
    wallet: str | None
    timestamp: datetime
    payload: dict[str, Any]
    source: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["timestamp"] = self.timestamp.astimezone(timezone.utc).isoformat()
        result["created_at"] = self.created_at.astimezone(timezone.utc).isoformat()
        return result