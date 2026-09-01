"""SOETool executing sequence of events and timeline reconciliation."""
from typing import List, Dict, Any, Optional
from domain.models.incident import SOEEvent
from domain.models.results import EventTimelineResult
from services.soe.engine import SOEEngine


class SOETool:
    """Specialized tool for millisecond timeline reconstruction."""

    async def execute(
        self,
        incident_id: str,
        events: List[SOEEvent],
        comtrade_digital_transitions: Optional[List[Dict[str, Any]]] = None,
    ) -> EventTimelineResult:
        result = SOEEngine.build_timeline_from_events(
            incident_id=incident_id,
            raw_events=events,
            comtrade_digital_transitions=comtrade_digital_transitions,
        )
        return result
