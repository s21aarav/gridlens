"""EvidenceAssessor evaluating relationships between Evidence objects and Candidate Hypotheses."""
from typing import List, Dict, Tuple
from domain.evidence.models import Evidence, EvidenceSourceType
from domain.evidence.assessment import EvidenceAssessment, AssessmentRelationship


class EvidenceAssessor:
    """Evaluates contextual support and contradiction between atomic Evidence and Hypotheses."""

    @classmethod
    def assess_evidence_for_hypotheses(cls, evidence_list: List[Evidence]) -> List[EvidenceAssessment]:
        assessments: List[EvidenceAssessment] = []
        ast_counter = 1

        for ev in evidence_list:
            # Check for COMTRADE overcurrent evidence
            if "OVERCURRENT_EXCEEDED" in ev.evidence_id:
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H1",
                    relationship=AssessmentRelationship.SUPPORTS,
                    weight=3.0,
                    rule_id="RULE_ASSESS_OVERCURRENT_GENUINE_FAULT",
                    explanation=f"Measured fault current exceeds pickup threshold, strongly supporting genuine overcurrent trip on H1.",
                ))
                ast_counter += 1

            # Check for COMTRADE truncation
            if "TRUNCATED" in ev.evidence_id:
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H6",
                    relationship=AssessmentRelationship.SUPPORTS,
                    weight=5.0,
                    rule_id="RULE_ASSESS_TRUNCATION_INSUFFICIENT",
                    explanation="Waveform was truncated before clearing, supporting H6 (Insufficient Evidence).",
                ))
                ast_counter += 1
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H1",
                    relationship=AssessmentRelationship.CONTRADICTS,
                    weight=-4.0,
                    rule_id="RULE_ASSESS_TRUNCATION_BLOCKS_H1",
                    explanation="Cannot substantiate genuine fault without complete clearance oscillography.",
                ))
                ast_counter += 1

            # Check for configuration validation violations
            if "RULE-MAP-003" in ev.evidence_id:  # Phase inversion violation
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H3",
                    relationship=AssessmentRelationship.SUPPORTS,
                    weight=5.0,
                    rule_id="RULE_ASSESS_WIRING_INVERSION_H3",
                    explanation="Validation detected CT Phase inversion, strongly confirming H3 (Secondary Wiring / Channel Mapping Error).",
                ))
                ast_counter += 1
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H1",
                    relationship=AssessmentRelationship.CONTRADICTS,
                    weight=-3.5,
                    rule_id="RULE_ASSESS_WIRING_CONTRADICTS_H1",
                    explanation="Relay reported phase conflicts with physical waveform channel due to inverted CT mapping.",
                ))
                ast_counter += 1

            # Check for configuration passed
            if "EV_VALIDATION_PASSED" in ev.evidence_id:
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H1",
                    relationship=AssessmentRelationship.SUPPORTS,
                    weight=1.5,
                    rule_id="RULE_ASSESS_CONFIG_PASSED_H1",
                    explanation="Substation configuration is structurally valid with 0 violations.",
                ))
                ast_counter += 1
                assessments.append(EvidenceAssessment(
                    assessment_id=f"AST_{ast_counter:03d}",
                    evidence_id=ev.evidence_id,
                    hypothesis_id="H3",
                    relationship=AssessmentRelationship.CONTRADICTS,
                    weight=-3.0,
                    rule_id="RULE_ASSESS_CONFIG_PASSED_REFUTES_H3",
                    explanation="Configuration validation passed, refuting channel mapping errors.",
                ))
                ast_counter += 1

            # Check for valid breaker clearing time
            if "EV_COMTRADE_CLEARING_TIME" in ev.evidence_id:
                clearing_ms = float(ev.structured_value)
                if clearing_ms <= 75.0:
                    assessments.append(EvidenceAssessment(
                        assessment_id=f"AST_{ast_counter:03d}",
                        evidence_id=ev.evidence_id,
                        hypothesis_id="H4",
                        relationship=AssessmentRelationship.CONTRADICTS,
                        weight=-3.0,
                        rule_id="RULE_ASSESS_NORMAL_CLEARING_REFUTES_H4",
                        explanation=f"Breaker cleared fault in {clearing_ms} ms (normal speed), refuting breaker mechanical failure (H4).",
                    ))
                    ast_counter += 1

        return assessments
