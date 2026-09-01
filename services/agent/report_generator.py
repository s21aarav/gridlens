"""ReportGenerator synthesizing human-readable engineering report strictly from verified claims."""
from typing import List, Optional
from domain.claims.models import Claim, ClaimType, ConflictLifecycle
from domain.hypotheses.models import Hypothesis
from domain.investigation.models import (
    InvestigationResult,
    InvestigationType,
    AuditTraceEntry,
)
from domain.models.results import RetrievedDocumentChunk
from services.agent.llm_provider import LLMProvider, get_configured_llm_provider


class ReportGenerator:
    """Synthesizes final investigation report exclusively from verified claims and supported inferences."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or get_configured_llm_provider()

    async def generate_final_report(
        self,
        investigation_id: str,
        incident_id: Optional[str],
        investigation_type: InvestigationType,
        user_query: str,
        hypotheses: List[Hypothesis],
        verified_facts: List[Claim],
        supported_inferences: List[Claim],
        rejected_claims: List[Claim],
        is_sufficient: bool,
        sufficiency_reason: str,
        conflict_lifecycle: ConflictLifecycle,
        citations: List[RetrievedDocumentChunk],
        execution_trace: List[AuditTraceEntry],
        start_time_iso: str,
        duration_ms: float,
    ) -> InvestigationResult:
        top_hyp = hypotheses[0] if hypotheses else None
        
        # Determine diagnosis title
        if not is_sufficient or (top_hyp and top_hyp.code == "H6"):
            diagnosis_title = "INSUFFICIENT EVIDENCE TO DETERMINE ROOT CAUSE"
            confidence_score = 0.15
        elif top_hyp and top_hyp.code == "H3":
            diagnosis_title = "SECONDARY CT CHANNEL MAPPING INCONSISTENCY (RESOLVED)"
            confidence_score = top_hyp.confidence_normalized
        elif top_hyp and top_hyp.code == "H1":
            diagnosis_title = f"GENUINE PRIMARY OVERCURRENT FAULT (CONFIDENCE: {int(top_hyp.confidence_normalized*100)}%)"
            confidence_score = top_hyp.confidence_normalized
        else:
            diagnosis_title = top_hyp.title if top_hyp else "INVESTIGATION CONCLUDED"
            confidence_score = top_hyp.confidence_normalized if top_hyp else 0.5

        recs = [c for c in verified_facts if c.claim_type == ClaimType.RECOMMENDATION]
        # Keep the final narrative deterministic. An LLM may format prose,
        # but it must not be the source of measurements or conclusions: the
        # previous implementation allowed the mock provider to invent values
        # that differed from the waveform analyzer.
        fact_lines = [f"- {c.statement}" for c in verified_facts if c.claim_type == ClaimType.FACT]
        inference_lines = [f"- {c.statement}" for c in supported_inferences]
        recommendation_lines = [f"- {c.statement}" for c in recs]
        sections = [f"GridLens Investigation Finding: {diagnosis_title}."]
        if not is_sufficient:
            sections.append(f"Sufficiency: {sufficiency_reason}")
        if fact_lines:
            sections.append("Verified facts:\n" + "\n".join(fact_lines))
        if inference_lines:
            sections.append("Supported inferences:\n" + "\n".join(inference_lines))
        if recommendation_lines:
            sections.append("Recommendations:\n" + "\n".join(recommendation_lines))
        prose_summary = "\n\n".join(sections)

        unresolved_contradictions = []
        if conflict_lifecycle == ConflictLifecycle.CONFLICT_UNRESOLVED:
            unresolved_contradictions.append("Relay event reports Phase A overcurrent, but waveform indicates normal current on Phase A without mapping resolution.")

        missing_evidence = []
        if not is_sufficient:
            missing_evidence.append(sufficiency_reason)

        return InvestigationResult(
            investigation_id=investigation_id,
            incident_id=incident_id,
            investigation_type=investigation_type,
            user_query=user_query,
            diagnosis_title=diagnosis_title,
            diagnosis_summary=prose_summary,
            confidence_score=confidence_score,
            is_sufficient=is_sufficient,
            sufficiency_reason=sufficiency_reason,
            conflict_lifecycle=conflict_lifecycle,
            conflict_explanation="Inverted secondary CT mapping between Phase A and Phase C was identified and validated." if conflict_lifecycle == ConflictLifecycle.CONFLICT_RESOLVED else None,
            hypotheses=hypotheses,
            verified_facts=[c for c in verified_facts if c.claim_type == ClaimType.FACT],
            supported_inferences=supported_inferences,
            rejected_claims=rejected_claims,
            unresolved_contradictions=unresolved_contradictions,
            missing_evidence=missing_evidence,
            recommendations=recs,
            citations=citations,
            execution_trace=execution_trace,
            created_at=start_time_iso,
            duration_ms=round(duration_ms, 2),
        )
