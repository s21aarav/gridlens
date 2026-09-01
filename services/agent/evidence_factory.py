"""EvidenceFactory converting typed tool output results into atomic Evidence objects."""
from typing import List
from domain.evidence.models import Evidence, EvidenceSourceType
from domain.models.results import (
    TopologyQueryResult,
    ComtradeAnalysisResult,
    ValidationResult,
    EventTimelineResult,
    DocumentRetrievalResult,
    HistoricalIncidentResult,
)


class EvidenceFactory:
    """Deterministic factory producing atomic, provenance-tracked Evidence objects."""

    @classmethod
    def from_topology(cls, topo: TopologyQueryResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        if not topo.is_topology_complete:
            evidence_list.append(Evidence(
                evidence_id="EV_TOPO_MISSING",
                source_type=EvidenceSourceType.GRAPH,
                source_id="NEO4J_TOPOLOGY",
                tool_name="TopologyTool",
                fact=f"Feeder {topo.feeder_id} topology records are incomplete or missing.",
                structured_value=False,
                provenance="Neo4j Cypher query",
                deterministic=True,
            ))
            return evidence_list

        evidence_list.append(Evidence(
            evidence_id="EV_TOPO_PRIMARY_RELAY",
            source_type=EvidenceSourceType.GRAPH,
            source_id="NEO4J_TOPOLOGY",
            tool_name="TopologyTool",
            fact=f"{topo.primary_relay_id} is configured as the primary protection relay for Feeder {topo.feeder_id}.",
            structured_value=topo.primary_relay_id,
            provenance=f"Substation OGS-01 -> Bay {topo.bay_id} -> {topo.feeder_id}",
            deterministic=True,
        ))

        evidence_list.append(Evidence(
            evidence_id="EV_TOPO_BREAKER",
            source_type=EvidenceSourceType.GRAPH,
            source_id="NEO4J_TOPOLOGY",
            tool_name="TopologyTool",
            fact=f"Feeder {topo.feeder_id} is controlled by circuit breaker {topo.controlled_breaker_id} on {topo.connected_bus_id}.",
            structured_value=topo.controlled_breaker_id,
            provenance=f"Bay {topo.bay_id} breaker association",
            deterministic=True,
        ))

        evidence_list.append(Evidence(
            evidence_id="EV_TOPO_SENSORS",
            source_type=EvidenceSourceType.GRAPH,
            source_id="NEO4J_TOPOLOGY",
            tool_name="TopologyTool",
            fact=f"Feeder {topo.feeder_id} is monitored by instrument sensors {', '.join(topo.sensor_ids)} feeding {topo.ied_id}.",
            structured_value=topo.sensor_ids,
            provenance="Sensor-to-IED CT/VT wiring table",
            deterministic=True,
        ))
        return evidence_list

    @classmethod
    def from_comtrade(cls, comtrade: ComtradeAnalysisResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        if comtrade.is_truncated:
            evidence_list.append(Evidence(
                evidence_id="EV_COMTRADE_TRUNCATED",
                source_type=EvidenceSourceType.COMTRADE,
                source_id=f"{comtrade.incident_id}.CFG",
                tool_name="WaveformTool",
                fact="COMTRADE waveform recording was truncated before full fault clearance.",
                structured_value=True,
                provenance="COMTRADE header sample count check",
                deterministic=True,
            ))

        for ch_name, m in comtrade.analog_measurements.items():
            ev_id = f"EV_COMTRADE_RMS_{ch_name}"
            evidence_list.append(Evidence(
                evidence_id=ev_id,
                source_type=EvidenceSourceType.COMTRADE,
                source_id=f"{comtrade.incident_id}.DAT",
                tool_name="WaveformTool",
                fact=f"Channel {ch_name} measured Pre-fault RMS: {m.pre_fault_rms} {m.unit}, Fault RMS: {m.fault_rms} {m.unit} (Peak: {m.peak_value} {m.unit}).",
                structured_value=m.fault_rms,
                unit=m.unit,
                    provenance=f"Sliding-window RMS calculation on channel {ch_name}",
                deterministic=True,
            ))

        if comtrade.pickup_exceeded and comtrade.fault_phase_detected:
            evidence_list.append(Evidence(
                evidence_id="EV_COMTRADE_OVERCURRENT_EXCEEDED",
                source_type=EvidenceSourceType.COMTRADE,
                source_id=f"{comtrade.incident_id}.DAT",
                tool_name="WaveformTool",
                fact=f"Overcurrent threshold ({comtrade.pickup_threshold_a} A) was exceeded on {comtrade.fault_phase_detected}.",
                structured_value=True,
                unit="A",
                provenance="Current threshold comparison",
                deterministic=True,
            ))

        if comtrade.total_clearing_time_ms is not None:
            evidence_list.append(Evidence(
                evidence_id="EV_COMTRADE_CLEARING_TIME",
                source_type=EvidenceSourceType.COMTRADE,
                source_id=f"{comtrade.incident_id}.DAT",
                tool_name="WaveformTool",
                fact=f"Total fault clearing time was {comtrade.total_clearing_time_ms} ms.",
                structured_value=comtrade.total_clearing_time_ms,
                unit="ms",
                provenance="Delta t between pickup edge and 52a breaker contact open",
                deterministic=True,
            ))
        return evidence_list

    @classmethod
    def from_validation(cls, val: ValidationResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        if val.valid:
            evidence_list.append(Evidence(
                evidence_id="EV_VALIDATION_PASSED",
                source_type=EvidenceSourceType.CONFIG_VALIDATOR,
                source_id="CONFIG_VALIDATOR",
                tool_name="ValidationTool",
                fact="Substation engineering configuration and channel mapping rules passed with 0 violations.",
                structured_value=True,
                provenance="Deterministic ValidationRuleEngine",
                deterministic=True,
            ))
        else:
            for index, v in enumerate(val.violations, start=1):
                evidence_list.append(Evidence(
                    # A rule can produce multiple violations. Include the
                    # occurrence so each evidence object remains addressable.
                    evidence_id=f"EV_VALIDATION_VIOLATION_{v.rule_id}_{index}",
                    source_type=EvidenceSourceType.CONFIG_VALIDATOR,
                    source_id="CONFIG_VALIDATOR",
                    tool_name="ValidationTool",
                    fact=f"Configuration rule violation [{v.rule_id}]: {v.message}",
                    structured_value=v.rule_id,
                    provenance=f"Rule check {v.rule_name} on {v.entity_id}",
                    deterministic=True,
                    metadata={"remediation": v.remediation_advice},
                ))
        return evidence_list

    @classmethod
    def from_timeline(cls, tl: EventTimelineResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        for ev in tl.ordered_events:
            ev_id = f"EV_SOE_{ev['event_id']}"
            evidence_list.append(Evidence(
                evidence_id=ev_id,
                source_type=EvidenceSourceType.EVENT_LOG,
                source_id=tl.incident_id,
                tool_name="SOETool",
                fact=f"At {ev['timestamp']} ({ev['offset_ms']} ms): {ev['source_device']} recorded {ev['event_type']} - {ev['description']}",
                structured_value=ev['event_type'],
                timestamp=ev['timestamp'],
                provenance=f"{ev['source_device']} SOE buffer",
                deterministic=True,
            ))
        return evidence_list

    @classmethod
    def from_documents(cls, docs: DocumentRetrievalResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        for ch in docs.chunks:
            evidence_list.append(Evidence(
                evidence_id=f"EV_DOC_{ch.chunk_id}",
                source_type=EvidenceSourceType.DOCUMENT,
                source_id=ch.doc_id,
                tool_name="RetrievalTool",
                fact=f"According to {ch.doc_id} ({ch.section}): '{ch.content[:180]}...'",
                structured_value=ch.chunk_id,
                provenance=f"{ch.doc_id} -> {ch.section}",
                deterministic=False,  # Retrieved text
                metadata={"title": ch.title, "full_content": ch.content, "score": ch.score},
            ))
        return evidence_list

    @classmethod
    def from_history(cls, hist: HistoricalIncidentResult) -> List[Evidence]:
        evidence_list: List[Evidence] = []
        for inc in hist.matching_incidents:
            evidence_list.append(Evidence(
                evidence_id=f"EV_HIST_{inc.incident_id}",
                source_type=EvidenceSourceType.INCIDENT_HISTORY,
                source_id=inc.incident_id,
                tool_name="HistoryTool",
                fact=f"Past Incident {inc.incident_id} ({inc.timestamp[:10]}): Feeder {inc.feeder_id} tripped on '{inc.fault_type}'. Root cause: {inc.root_cause}",
                structured_value=inc.root_cause,
                provenance="Historical Substation Fault Database",
                deterministic=True,
            ))
        return evidence_list
