"""Deterministic claim verifier auditing candidate claims against authoritative tool results."""
from typing import List, Dict, Tuple, Set
from domain.claims.models import Claim, ClaimType, VerificationStatus, ConflictLifecycle
from domain.evidence.models import Evidence


class ClaimVerifier:
    """Audits candidate claims against verified evidence. Rejects or flags unsupported claims without rewriting."""

    @classmethod
    def verify_candidate_claims(
        cls,
        candidate_claims: List[Claim],
        evidence_list: List[Evidence],
    ) -> Tuple[List[Claim], List[Claim], List[Claim]]:
        """Returns (verified_facts, supported_inferences, rejected_claims)."""
        evidence_dict: Dict[str, Evidence] = {ev.evidence_id: ev for ev in evidence_list}
        verified_evidence_ids: Set[str] = set(evidence_dict.keys())
        claims_by_id: Dict[str, Claim] = {claim.claim_id: claim for claim in candidate_claims}

        verified_facts: List[Claim] = []
        supported_inferences: List[Claim] = []
        rejected_claims: List[Claim] = []

        for claim in candidate_claims:
            if claim.claim_type == ClaimType.FACT:
                # A fact is only verified when its statement is exactly the
                # statement emitted by the cited deterministic evidence.
                # Checking IDs alone would allow a fabricated statement to
                # piggyback on a real evidence record.
                cited_evidence = [evidence_dict.get(eid) for eid in claim.evidence_ids]
                statements_match = (
                    bool(cited_evidence)
                    and all(ev is not None for ev in cited_evidence)
                    and len(cited_evidence) == 1
                    and claim.statement == cited_evidence[0].fact
                )
                if not statements_match:
                    claim.verification_status = VerificationStatus.REJECTED
                    claim.verification_notes = "Rejected: Claim statement does not exactly match its cited authoritative evidence."
                    rejected_claims.append(claim)
                else:
                    claim.verification_status = VerificationStatus.VERIFIED
                    claim.verification_notes = f"Verified against authoritative {claim.verification_source} output."
                    verified_facts.append(claim)

            elif claim.claim_type == ClaimType.INFERENCE:
                # Inferences must cite evidence, name an explicit rule, and
                # point at fact claims that have already passed verification.
                premises_valid = bool(claim.premise_claim_ids) and all(
                    claims_by_id.get(cid) is not None
                    and claims_by_id[cid].claim_type == ClaimType.FACT
                    and claims_by_id[cid].verification_status == VerificationStatus.VERIFIED
                    for cid in claim.premise_claim_ids
                )
                if (
                    bool(claim.evidence_ids)
                    and all(eid in verified_evidence_ids for eid in claim.evidence_ids)
                    and bool(claim.inference_rule_id)
                    and premises_valid
                ):
                    claim.verification_status = VerificationStatus.SUPPORTED_INFERENCE
                    claim.verification_notes = f"Supported by verified premise claims: {claim.premise_claim_ids}"
                    supported_inferences.append(claim)
                else:
                    claim.verification_status = VerificationStatus.REJECTED
                    claim.verification_notes = "Rejected: Inference premises could not be substantiated by verified evidence."
                    rejected_claims.append(claim)

            elif claim.claim_type == ClaimType.RECOMMENDATION:
                # Recommendations are valid next steps
                claim.verification_status = VerificationStatus.VERIFIED
                claim.verification_notes = "Standard engineering procedural recommendation."
                verified_facts.append(claim)

        return verified_facts, supported_inferences, rejected_claims
