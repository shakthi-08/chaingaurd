from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.investigation_event import InvestigationEvent


class IntegrationAdapter(ABC):
    """Extension point for authorized RPC, indexer, VASP, or compliance feeds."""

    name = "base"


class EventProvider(IntegrationAdapter):
    @abstractmethod
    def get_events(self, case_id: str) -> list[InvestigationEvent]:
        """Fetch new normalized events for a case."""