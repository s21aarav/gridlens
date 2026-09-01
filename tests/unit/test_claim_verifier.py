"Regression tests for exact claim-to-evidence grounding."
from domain.claims.models import Claim, ClaimType, VerificationStatus
from domain.evidence.models import Evidence, EvidenceSourceType
from services.agent.verifier import ClaimVerifier


def test_fact_with_real_evidence_id_but_fabricated_statement_is_rejected():
    evidence = Evidence(
        evidence_id="EV_CURRENT", source_type=EvidenceSourceType.COMTRADE,
        source_id="INC-1.DAT", tool_name="WaveformTool",
        fact="Channel IC measured Fault RMS: 3748.2 A.", structured_value=3748.2,
        unit="A", provenance="Analyzer",
    )
    claim = Claim(claim_id="C01", statement="Channel IC measured Fault RMS: 3850 A.",
                  claim_type=ClaimType.FACT, evidence_ids=[evidence.evidence_id])
    facts, inferences, rejected = ClaimVerifier.verify_candidate_claims([claim], [evidence])
    assert facts == []
    assert inferences == []
    assert rejected[0].verification_status == VerificationStatus.REJECTED
