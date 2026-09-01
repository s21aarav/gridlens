"""Stateful LangGraph investigation orchestrator coordinating deterministic tools and claim verification."""
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from domain.investigation.models import (
    InvestigationRequest,
    InvestigationResult,
    InvestigationType,
    AuditTraceEntry,
)
from domain.claims.models import Claim, ConflictLifecycle
from domain.evidence.models import Evidence
from domain.evidence.assessment import EvidenceAssessment
from domain.hypotheses.models import Hypothesis
from domain.models.results import RetrievedDocumentChunk

from services.tools.topology_tool import TopologyTool
from services.tools.waveform_tool import WaveformTool
from services.tools.validation_tool import ValidationTool
from services.tools.soe_tool import SOETool
from services.tools.retrieval_tool import RetrievalTool
from services.tools.history_tool import HistoryTool

from services.agent.evidence_factory import EvidenceFactory
from services.agent.assessments import EvidenceAssessor
from services.agent.hypotheses import HypothesisEngine
from services.agent.sufficiency import SufficiencyPolicyEngine
from services.agent.claims import ClaimConstructor
from services.agent.verifier import ClaimVerifier
from services.agent.report_generator import ReportGenerator

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # Keep the deterministic demo runnable without optional extras.
    END = START = StateGraph = None


class InvestigationState(BaseModel):
    investigation_id: str
    incident_id: Optional[str] = None
    user_query: str
    user_role: str = "ENGINEER"
    investigation_type: InvestigationType = InvestigationType.PROTECTION_EVENT_INVESTIGATION
    selected_tools: List[str] = Field(default_factory=list)
    raw_tool_results: Dict[str, Any] = Field(default_factory=dict)
    evidence_ledger: List[Evidence] = Field(default_factory=list)
    evidence_assessments: List[EvidenceAssessment] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    conflict_lifecycle: ConflictLifecycle = ConflictLifecycle.NO_CONFLICT
    is_sufficient: bool = True
    sufficiency_reason: str = ""
    missing_evidence: List[str] = Field(default_factory=list)
    candidate_claims: List[Claim] = Field(default_factory=list)
    verified_facts: List[Claim] = Field(default_factory=list)
    supported_inferences: List[Claim] = Field(default_factory=list)
    rejected_claims: List[Claim] = Field(default_factory=list)
    citations: List[RetrievedDocumentChunk] = Field(default_factory=list)
    final_result: Optional[InvestigationResult] = None
    execution_trace: List[AuditTraceEntry] = Field(default_factory=list)
    start_time: float = 0.0


class GridLensInvestigationWorkflow:
    """The canonical stateful agent orchestrator for electrical protection investigations."""

    def __init__(
        self,
        topology_tool: Optional[TopologyTool] = None,
        waveform_tool: Optional[WaveformTool] = None,
        validation_tool: Optional[ValidationTool] = None,
        soe_tool: Optional[SOETool] = None,
        retrieval_tool: Optional[RetrievalTool] = None,
        history_tool: Optional[HistoryTool] = None,
    ):
        self.topology_tool = topology_tool or TopologyTool()
        self.waveform_tool = waveform_tool or WaveformTool()
        self.validation_tool = validation_tool or ValidationTool()
        self.soe_tool = soe_tool or SOETool()
        self.retrieval_tool = retrieval_tool or RetrievalTool()
        self.history_tool = history_tool or HistoryTool()
        self.report_generator = ReportGenerator()
        self._compiled_graph = self._build_langgraph()

    def _build_langgraph(self):
        """Build the conditional LangGraph router when the optional dependency is installed."""
        if StateGraph is None:
            return None
        graph = StateGraph(dict)

        async def classify_node(state: dict) -> dict:
            inv_type, selected_tools = self.classify_query_intent(state["request"].user_query)
            return {
                "request": state["request"],
                "incident_data": state.get("incident_data"),
                "investigation_type": inv_type.value,
                "selected_tools": selected_tools,
            }

        async def route_node(state: dict) -> dict:
            result = await self._run_investigation_linear(
                state["request"], incident_data=state.get("incident_data")
            )
            return {"result": result}

        graph.add_node("classify_intent", classify_node)
        routes = [item.value for item in InvestigationType]
        for route in routes:
            graph.add_node(route, route_node)
        graph.add_edge(START, "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            lambda state: state["investigation_type"],
            {route: route for route in routes},
        )
        for route in routes:
            graph.add_edge(route, END)
        return graph.compile()

    @classmethod
    def classify_query_intent(cls, user_query: str) -> Tuple[InvestigationType, List[str]]:
        q_lower = user_query.lower()
        
        # 1. Topology Inquiry Check
        if (
            "which relay" in q_lower or
            "which circuit breaker" in q_lower or
            "which breaker" in q_lower or
            "what breaker" in q_lower or
            "protects feeder" in q_lower or
            "associated with feeder" in q_lower or
            "connected to bus" in q_lower or
            "substation topology" in q_lower
        ) and "trip" not in q_lower and "incident" not in q_lower:
            return InvestigationType.TOPOLOGY_INQUIRY, ["TopologyTool"]

        # 2. Documentation / Conceptual QA Check
        if (
            "what does" in q_lower or
            "define" in q_lower or
            "meaning of" in q_lower or
            "explain the operating principle" in q_lower or
            "what is the standard clearing time" in q_lower or
            "what is the function of" in q_lower or
            "how does ansi" in q_lower or
            "sop" in q_lower or
            "iec 61850" in q_lower
        ) and "why did" not in q_lower and "incident" not in q_lower:
            return InvestigationType.DOCUMENTATION_QA, ["RetrievalTool"]

        # 3. Configuration Validation Check
        if "is the configuration" in q_lower or "is configuration valid" in q_lower or "validate bay" in q_lower or "rule check" in q_lower:
            return InvestigationType.CONFIGURATION_VALIDATION, ["TopologyTool", "ValidationTool"]

        # 4. Sequence of Events / Timeline Check
        if "show timeline" in q_lower or "sequence of events" in q_lower or "soe log" in q_lower:
            return InvestigationType.EVENT_TIMELINE_RECONCILIATION, ["SOETool", "TopologyTool"]

        # 5. Default: Full Protection Event Investigation
        return InvestigationType.PROTECTION_EVENT_INVESTIGATION, [
            "TopologyTool", "WaveformTool", "ValidationTool", "SOETool", "RetrievalTool", "HistoryTool"
        ]

    async def run_investigation(
        self,
        request: InvestigationRequest,
        incident_data: Optional[Dict[str, Any]] = None,
    ) -> InvestigationResult:
        if self._compiled_graph is not None:
            state = await self._compiled_graph.ainvoke(
                {"request": request, "incident_data": incident_data}
            )
            return state["result"]
        return await self._run_investigation_linear(request, incident_data)

    async def _run_investigation_linear(
        self,
        request: InvestigationRequest,
        incident_data: Optional[Dict[str, Any]] = None,
    ) -> InvestigationResult:
        start_t = time.time()
        inv_id = request.investigation_id or f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        inv_type, selected_tools = self.classify_query_intent(request.user_query)

        state = InvestigationState(
            investigation_id=inv_id,
            incident_id=request.incident_id,
            user_query=request.user_query,
            user_role=request.user_role,
            investigation_type=inv_type,
            selected_tools=selected_tools,
            start_time=start_t,
        )

        step_counter = 1

        state.execution_trace.append(AuditTraceEntry(
            step_index=step_counter,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="INTENT_CLASSIFICATION_AND_TOOL_SELECTION",
            inputs={"user_query": request.user_query},
            outputs_summary=f"Selected {state.investigation_type.value} with tools: {', '.join(state.selected_tools)}",
            duration_ms=round((time.time() - start_t) * 1000, 2),
        ))
        step_counter += 1

        # Determine target feeder & incident
        q_lower = request.user_query.lower()
        feeder_id = request.target_equipment_id or "F12"
        if "f13" in q_lower:
            feeder_id = "F13"
        elif incident_data and incident_data.get("feeder_id"):
            feeder_id = incident_data["feeder_id"]

        inc_id = request.incident_id or ("INC-2026-003" if feeder_id == "F13" else "INC-2026-001")
        if "incident b" in q_lower or "mapping" in q_lower or "inversion" in q_lower or (incident_data and incident_data.get("incident_id") == "INC-2026-002"):
            inc_id = "INC-2026-002"

        # Execute tools conditionally
        if "TopologyTool" in state.selected_tools:
            t0 = time.time()
            topo_res = await self.topology_tool.execute(feeder_id=feeder_id)
            state.raw_tool_results["topology"] = topo_res
            state.evidence_ledger.extend(EvidenceFactory.from_topology(topo_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="TopologyTool",
                inputs={"feeder_id": feeder_id},
                outputs_summary=f"Retrieved protection chain for {feeder_id}: Relay {topo_res.primary_relay_id}, Breaker {topo_res.controlled_breaker_id}",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        if "WaveformTool" in state.selected_tools:
            t0 = time.time()
            wav_res = await self.waveform_tool.execute(incident_id=inc_id)
            state.raw_tool_results["comtrade"] = wav_res
            state.evidence_ledger.extend(EvidenceFactory.from_comtrade(wav_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="WaveformTool",
                inputs={"incident_id": inc_id},
                outputs_summary=f"COMTRADE analysis: Phase with max fault={wav_res.fault_phase_detected}, Pickup exceeded={wav_res.pickup_exceeded}, Clearing time={wav_res.total_clearing_time_ms} ms",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        if "ValidationTool" in state.selected_tools:
            t0 = time.time()
            custom_map = None
            if inc_id == "INC-2026-002":
                custom_map = {"CH1": "CT12C", "CH2": "CT12B", "CH3": "CT12A"}
            val_res = await self.validation_tool.execute(bay_id=f"BAY_{feeder_id}", feeder_id=feeder_id, custom_mapping=custom_map)
            state.raw_tool_results["validation"] = val_res
            state.evidence_ledger.extend(EvidenceFactory.from_validation(val_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="ValidationTool",
                inputs={"bay_id": f"BAY_{feeder_id}"},
                outputs_summary=f"Validation result: valid={val_res.valid}, violations_count={len(val_res.violations)}",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        if "SOETool" in state.selected_tools and incident_data and incident_data.get("events"):
            t0 = time.time()
            soe_res = await self.soe_tool.execute(
                incident_id=inc_id,
                events=incident_data["events"],
                comtrade_digital_transitions=state.raw_tool_results.get("comtrade", {}).digital_transitions if hasattr(state.raw_tool_results.get("comtrade"), "digital_transitions") else None,
            )
            state.raw_tool_results["timeline"] = soe_res
            state.evidence_ledger.extend(EvidenceFactory.from_timeline(soe_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="SOETool",
                inputs={"incident_id": inc_id},
                outputs_summary=f"SOE Timeline reconciled with {len(soe_res.ordered_events)} chronological events (Sync: {soe_res.synchronization_status})",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        if "RetrievalTool" in state.selected_tools:
            t0 = time.time()
            ret_query = request.user_query
            if state.investigation_type == InvestigationType.PROTECTION_EVENT_INVESTIGATION:
                ret_query = f"feeder {feeder_id} overcurrent protection ANSI 51 time-current curves and trip procedure"
            doc_res = await self.retrieval_tool.execute(query=ret_query, top_k=3)
            state.raw_tool_results["documents"] = doc_res
            state.citations = doc_res.chunks
            state.evidence_ledger.extend(EvidenceFactory.from_documents(doc_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="RetrievalTool",
                inputs={"query": ret_query},
                outputs_summary=f"Retrieved {len(doc_res.chunks)} technical document chunks with citation metadata",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        if "HistoryTool" in state.selected_tools:
            t0 = time.time()
            hist_res = await self.history_tool.execute(feeder_id=feeder_id, limit=2)
            state.raw_tool_results["history"] = hist_res
            state.evidence_ledger.extend(EvidenceFactory.from_history(hist_res))
            state.execution_trace.append(AuditTraceEntry(
                step_index=step_counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage="TOOL_EXECUTION",
                tool_invoked="HistoryTool",
                inputs={"feeder_id": feeder_id},
                outputs_summary=f"Retrieved {len(hist_res.matching_incidents)} past incident records for {feeder_id}",
                duration_ms=round((time.time() - t0) * 1000, 2),
            ))
            step_counter += 1

        # 3. Assess Evidence for Candidate Hypotheses
        t0 = time.time()
        state.evidence_assessments = EvidenceAssessor.assess_evidence_for_hypotheses(state.evidence_ledger)
        state.hypotheses = HypothesisEngine.evaluate_hypotheses(state.evidence_ledger, state.evidence_assessments)
        
        has_phase_inversion = any("RULE-MAP-003" in ev.evidence_id for ev in state.evidence_ledger)
        if has_phase_inversion:
            state.conflict_lifecycle = ConflictLifecycle.CONFLICT_RESOLVED
        else:
            state.conflict_lifecycle = ConflictLifecycle.NO_CONFLICT

        state.execution_trace.append(AuditTraceEntry(
            step_index=step_counter,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="EVIDENCE_ASSESSMENT_AND_HYPOTHESIS_SCORING",
            inputs={"evidence_count": len(state.evidence_ledger)},
            outputs_summary=f"Evaluated 6 candidate hypotheses. Top hypothesis: {state.hypotheses[0].code} - {state.hypotheses[0].title} (Score: {state.hypotheses[0].deterministic_score}, Conflict: {state.conflict_lifecycle.value})",
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))
        step_counter += 1

        # 4. Contextual Sufficiency Check
        t0 = time.time()
        is_suff, suff_reason, missing_ev = SufficiencyPolicyEngine.evaluate_sufficiency(
            inv_type=state.investigation_type,
            evidence_list=state.evidence_ledger,
            top_hypothesis=state.hypotheses[0],
        )
        state.is_sufficient = is_suff
        state.sufficiency_reason = suff_reason
        state.missing_evidence = missing_ev

        state.execution_trace.append(AuditTraceEntry(
            step_index=step_counter,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="SUFFICIENCY_POLICY_GATE",
            inputs={"investigation_type": state.investigation_type.value},
            outputs_summary=f"Sufficiency check: {'PASSED' if is_suff else 'FAILED/ABSTAIN'} ({suff_reason})",
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))
        step_counter += 1

        # 5. Construct Candidate Claims & Deterministic Verification
        t0 = time.time()
        state.candidate_claims = ClaimConstructor.construct_candidate_claims(
            evidence_list=state.evidence_ledger,
            hypotheses=state.hypotheses,
            conflict_lifecycle=state.conflict_lifecycle,
        )

        v_facts, s_infs, r_claims = ClaimVerifier.verify_candidate_claims(
            candidate_claims=state.candidate_claims,
            evidence_list=state.evidence_ledger,
        )
        state.verified_facts = v_facts
        state.supported_inferences = s_infs
        state.rejected_claims = r_claims

        state.execution_trace.append(AuditTraceEntry(
            step_index=step_counter,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="CLAIM_CONSTRUCTION_AND_DETERMINISTIC_VERIFICATION",
            inputs={"candidate_claims_count": len(state.candidate_claims)},
            outputs_summary=f"Verified {len(v_facts)} facts, {len(s_infs)} supported inferences, and rejected {len(r_claims)} ungrounded claims",
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))
        step_counter += 1

        # 6. Final Report Synthesis
        t0 = time.time()
        total_duration = (time.time() - start_t) * 1000.0
        final_result = await self.report_generator.generate_final_report(
            investigation_id=state.investigation_id,
            incident_id=inc_id,
            investigation_type=state.investigation_type,
            user_query=state.user_query,
            hypotheses=state.hypotheses,
            verified_facts=state.verified_facts,
            supported_inferences=state.supported_inferences,
            rejected_claims=state.rejected_claims,
            is_sufficient=state.is_sufficient,
            sufficiency_reason=state.sufficiency_reason,
            conflict_lifecycle=state.conflict_lifecycle,
            citations=state.citations,
            execution_trace=state.execution_trace,
            start_time_iso=datetime.now(timezone.utc).isoformat(),
            duration_ms=total_duration,
        )

        state.execution_trace.append(AuditTraceEntry(
            step_index=step_counter,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage="FINAL_REPORT_SYNTHESIS",
            inputs={"verified_facts_count": len(state.verified_facts)},
            outputs_summary=f"Investigation report generated successfully: {final_result.diagnosis_title}",
            duration_ms=round((time.time() - t0) * 1000, 2),
        ))

        state.final_result = final_result
        return final_result
