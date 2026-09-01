"""Sequence of Events (SOE) engine for millisecond-precision event timeline reconciliation."""
from typing import List, Dict, Any, Optional, Union
from domain.models.incident import SOEEvent
from domain.models.results import EventTimelineResult


class SOEEngine:
    """Authoritative reconciliation engine for sequence-of-events and protection logs."""

    @classmethod
    def build_timeline_from_events(
        cls,
        incident_id: str,
        raw_events: List[Union[SOEEvent, Dict[str, Any]]],
        comtrade_digital_transitions: Optional[List[Dict[str, Any]]] = None,
    ) -> EventTimelineResult:
        if not raw_events:
            return EventTimelineResult(
                incident_id=incident_id,
                ordered_events=[],
                synchronization_status="UNSYNCHRONIZED",
                anomalies=["No sequence-of-events logs available for this incident."],
            )

        def get_offset(e: Union[SOEEvent, Dict[str, Any]]) -> float:
            if hasattr(e, "offset_ms"):
                return float(e.offset_ms)
            elif isinstance(e, dict):
                return float(e.get("offset_ms", 0.0))
            return 0.0

        def get_field(e: Union[SOEEvent, Dict[str, Any]], field_name: str, default: Any = "") -> Any:
            if hasattr(e, field_name):
                return getattr(e, field_name)
            elif isinstance(e, dict):
                return e.get(field_name, default)
            return default

        # Sort raw events chronologically by offset_ms
        sorted_events = sorted(raw_events, key=get_offset)

        # Convert to structured dictionary entries
        ordered_list: List[Dict[str, Any]] = []
        anomalies: List[str] = []

        prev_offset = None
        for ev in sorted_events:
            off_ms = get_offset(ev)
            if prev_offset is not None and (off_ms - prev_offset) > 1000.0:
                ev_id = get_field(ev, "event_id", "EVT")
                anomalies.append(f"Timestamp gap detected: {round(off_ms - prev_offset, 1)} ms before {ev_id}.")

            ordered_list.append({
                "event_id": get_field(ev, "event_id", "EVT"),
                "timestamp": get_field(ev, "timestamp", "00:00:00.000"),
                "offset_ms": off_ms,
                "source_device": get_field(ev, "source_device", "UNKNOWN"),
                "event_type": get_field(ev, "event_type", "EVENT"),
                "channel_or_function": get_field(ev, "channel_or_function", ""),
                "description": get_field(ev, "description", ""),
                "value": get_field(ev, "value", None),
            })
            prev_offset = off_ms

        # Merge COMTRADE digital transitions if present
        if comtrade_digital_transitions:
            for dt in comtrade_digital_transitions:
                ordered_list.append({
                    "event_id": f"COMTRADE_DIG_{dt['channel']}_{int(dt['time_ms'])}",
                    "timestamp": f"+{dt['time_ms']:.1f}ms",
                    "offset_ms": dt["time_ms"],
                    "source_device": "COMTRADE_OSCILLOGRAPHY",
                    "event_type": "DIGITAL_EDGE_TRANSITION",
                    "channel_or_function": dt["channel"],
                    "description": f"Digital channel {dt['channel']} changed from {dt['old_val']} to {dt['new_val']}",
                    "value": dt["new_val"],
                })

        # Re-sort combined list
        final_ordered = sorted(ordered_list, key=lambda x: x["offset_ms"])
        
        # Calculate total duration from first disturbance to clearance
        total_duration = 0.0
        if len(final_ordered) > 1:
            total_duration = final_ordered[-1]["offset_ms"] - final_ordered[0]["offset_ms"]

        sync_status = "SYNCHRONIZED"
        if len(anomalies) > 0:
            sync_status = "DESYNCHRONIZED_ANOMALY"

        return EventTimelineResult(
            incident_id=incident_id,
            ordered_events=final_ordered,
            timestamp_precision="1ms",
            synchronization_status=sync_status,
            total_duration_ms=round(total_duration, 2),
            anomalies=anomalies,
        )
