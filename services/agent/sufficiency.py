"""Context-aware Sufficiency Policy Engine governing evidence adequacy and explicit abstention."""
from typing import List, Tuple
from domain.investigation.models import InvestigationType, EvidenceRequirementPolicy
from domain.evidence.models import Evidence, EvidenceSourceType
from domain.hypotheses.models import Hypothesis


class SufficiencyPolicyEngine:
    """Evaluates contextual evidence sufficiency against inquiry-specific policies."""

    @classmethod
    def get_policy_for_investigation(cls, inv_type: InvestigationType) -> EvidenceRequirementPolicy:
        if inv_type == InvestigationType.TOPOLOGY_INQUIRY:
            return EvidenceRequirementPolicy(
                investigation_type=inv_type,
                required_source_types=["GRAPH"],
                preferred_source_types=[],
                must_resolve_contradictions=False,
                min_verified_facts=1,
            )
        elif inv_type == InvestigationType.DOCUMENTATION_QA:
            return EvidenceRequirementPolicy(
                investigation_type=inv_type,
                required_source_types=["DOCUMENT"],
                preferred_source_types=[],
                must_resolve_contradictions=False,
                min_verified_facts=1,
            )
        elif inv_type == InvestigationType.CONFIGURATION_VALIDATION:
            return EvidenceRequirementPolicy(
                investigation_type=inv_type,
                required_source_types=["GRAPH", "CONFIG_VALIDATOR"],
                preferred_source_types=["DOCUMENT"],
                must_resolve_contradictions=True,
                min_verified_facts=2,
            )
        elif inv_type == InvestigationType.EVENT_TIMELINE_RECONCILIATION:
            return EvidenceRequirementPolicy(
                investigation_type=inv_type,
                required_source_types=["EVENT_LOG"],
                preferred_source_types=["GRAPH"],
                must_resolve_contradictions=False,
                min_verified_facts=2,
            )
        else:  # PROTECTION_EVENT_INVESTIGATION
            return EvidenceRequirementPolicy(
                investigation_type=inv_type,
                required_source_types=["GRAPH", "COMTRADE", "EVENT_LOG", "CONFIG_VALIDATOR"],
                preferred_source_types=["DOCUMENT", "INCIDENT_HISTORY"],
                must_resolve_contradictions=True,
                min_verified_facts=3,
            )

    @classmethod
    def evaluate_sufficiency(
        cls,
        inv_type: InvestigationType,
        evidence_list: List[Evidence],
        top_hypothesis: Hypothesis,
    ) -> Tuple[bool, str, List[str]]:
        policy = cls.get_policy_for_investigation(inv_type)
        missing_evidence: List[str] = []

        available_source_types = set(ev.source_type.value for ev in evidence_list)

        # Check required source types
        for req_st in policy.required_source_types:
            if req_st not in available_source_types:
                missing_evidence.append(f"Required evidence source '{req_st}' was not retrieved.")

        # Check for fatal truncation or missing CT parameters in event investigations
        if inv_type == InvestigationType.PROTECTION_EVENT_INVESTIGATION:
            has_truncation = any("TRUNCATED" in ev.evidence_id for ev in evidence_list)
            has_ct_zero = any("RULE-CFG-004" in ev.evidence_id for ev in evidence_list)
            
            if has_truncation:
                missing_evidence.append("Full-duration COMTRADE oscillography recording (current capture is truncated at 30ms).")
            if has_ct_zero:
                missing_evidence.append("Calibrated non-zero CT primary/secondary ratio setting for the bay.")

        # If top hypothesis is H6 (Insufficient Evidence), force abstention
        if top_hypothesis.code == "H6" or len(missing_evidence) > 0:
            reason = "Insufficient evidence to establish root cause. " + " ".join(missing_evidence)
            return False, reason, missing_evidence

        if len(evidence_list) < policy.min_verified_facts:
            return False, f"Total verified facts ({len(evidence_list)}) is below required minimum ({policy.min_verified_facts}).", missing_evidence

        return True, "Sufficient evidence available across all required domain sources.", []
