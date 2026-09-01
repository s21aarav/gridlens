"""ClaimConstructor generating candidate atomic claims categorized into FACT, INFERENCE, and RECOMMENDATION."""
from typing import List, Dict, Tuple
from domain.evidence.models import Evidence
from domain.claims.models import Claim, ClaimType, VerificationStatus, ConflictLifecycle
from domain.hypotheses.models import Hypothesis


class ClaimConstructor:
    """Constructs candidate atomic claims with strict semantic categorization."""

    @classmethod
    def construct_candidate_claims(
        cls,
        evidence_list: List[Evidence],
        hypotheses: List[Hypothesis],
        conflict_lifecycle: ConflictLifecycle = ConflictLifecycle.NO_CONFLICT,
    ) -> List[Claim]:
        claims: List[Claim] = []
        claim_counter = 1

        # 1. FACT Claims (derived directly from Evidence objects)
        for ev in evidence_list:
            c_id = f"C{claim_counter:02d}"
            claims.append(Claim(
                claim_id=c_id,
                statement=ev.fact,
                claim_type=ClaimType.FACT,
                evidence_ids=[ev.evidence_id],
                verification_status=VerificationStatus.UNVERIFIED,
                verification_source=ev.tool_name,
                conflict_lifecycle=conflict_lifecycle,
            ))
            claim_counter += 1

        fact_claim_ids = {
            claim.evidence_ids[0]: claim.claim_id
            for claim in claims
            if claim.claim_type == ClaimType.FACT and len(claim.evidence_ids) == 1
        }

        # 2. INFERENCE Claims (derived via explicit premise rules)
        top_hyp = hypotheses[0] if hypotheses else None
        available_evidence_ids = {ev.evidence_id for ev in evidence_list}
        if (
            top_hyp
            and top_hyp.code == "H1"
            and {"EV_COMTRADE_OVERCURRENT_EXCEEDED", "EV_TOPO_PRIMARY_RELAY"} <= available_evidence_ids
        ):
            # Inference: Current exceeded pickup threshold causing trip
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="Phase C measured fault current significantly exceeded the configured 2500 A pickup threshold, initiating ANSI 51 time-overcurrent trip logic.",
                claim_type=ClaimType.INFERENCE,
                evidence_ids=[
                    "EV_COMTRADE_RMS_IC",
                    "EV_COMTRADE_OVERCURRENT_EXCEEDED",
                    "EV_TOPO_PRIMARY_RELAY",
                ],
                premise_claim_ids=[
                    fact_claim_ids[eid]
                    for eid in (
                        "EV_COMTRADE_RMS_IC",
                        "EV_COMTRADE_OVERCURRENT_EXCEEDED",
                        "EV_TOPO_PRIMARY_RELAY",
                    )
                    if eid in fact_claim_ids
                ],
                inference_rule_id="INF_RULE_OVERCURRENT_TRIP_INITIATION",
                verification_status=VerificationStatus.UNVERIFIED,
                verification_source="INFERENCE_ENGINE",
                conflict_lifecycle=conflict_lifecycle,
            ))
            claim_counter += 1
        elif top_hyp and top_hyp.code == "H3":
            # Inference: Inverted CT channel wiring created misleading Phase A alarm
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="Inverted CT secondary terminal wiring between Phase A and Phase C caused the relay event log to report a Phase A trip, while the actual physical disturbance occurred on Phase C.",
                claim_type=ClaimType.INFERENCE,
                evidence_ids=[
                    *[ev.evidence_id for ev in evidence_list if "RULE-MAP-003" in ev.evidence_id],
                    "EV_COMTRADE_RMS_IC",
                ],
                premise_claim_ids=[
                    fact_claim_ids[eid]
                    for eid in (
                        *[ev.evidence_id for ev in evidence_list if "RULE-MAP-003" in ev.evidence_id],
                        "EV_COMTRADE_RMS_IC",
                    )
                    if eid in fact_claim_ids
                ],
                inference_rule_id="INF_RULE_CROSS_PHASE_MAPPING_RESOLUTION",
                verification_status=VerificationStatus.UNVERIFIED,
                verification_source="INFERENCE_ENGINE",
                conflict_lifecycle=ConflictLifecycle.CONFLICT_RESOLVED,
            ))
            claim_counter += 1
        elif top_hyp and top_hyp.code == "H6":
            # Inference: Insufficient waveform duration to establish clearance
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="The available 30 ms oscillography record is insufficient to confirm whether the fault was successfully cleared by breaker operation.",
                claim_type=ClaimType.INFERENCE,
                evidence_ids=["EV_COMTRADE_TRUNCATED"],
                premise_claim_ids=["C01"],
                inference_rule_id="INF_RULE_INSUFFICIENT_DATA_DEDUCTION",
                verification_status=VerificationStatus.UNVERIFIED,
                verification_source="INFERENCE_ENGINE",
                conflict_lifecycle=conflict_lifecycle,
            ))
            claim_counter += 1

        # 3. RECOMMENDATION Claims
        if top_hyp and top_hyp.code == "H1":
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="Execute cable insulation resistance (megger) test and visual patrol of Feeder F12 before initiating breaker reclosure according to SOP-006.",
                claim_type=ClaimType.RECOMMENDATION,
                evidence_ids=[],
                verification_status=VerificationStatus.VERIFIED,  # Recommendations don't require fact verification but are explicitly marked
                verification_source="SOP-006",
                conflict_lifecycle=conflict_lifecycle,
            ))
            claim_counter += 1
        elif top_hyp and top_hyp.code == "H3":
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="De-energize Bay F12 and perform point-to-point secondary wiring audit on terminal block X100 to correct transposed Phase A and Phase C CT test block connections.",
                claim_type=ClaimType.RECOMMENDATION,
                evidence_ids=[],
                verification_status=VerificationStatus.VERIFIED,
                verification_source="DOC-IED-003",
                conflict_lifecycle=ConflictLifecycle.CONFLICT_RESOLVED,
            ))
            claim_counter += 1
        elif top_hyp and top_hyp.code == "H6":
            claims.append(Claim(
                claim_id=f"C{claim_counter:02d}",
                statement="Retrieve complete uncorrupted COMTRADE recording from relay internal flash storage and calibrate Bay F13 CT secondary ratio settings.",
                claim_type=ClaimType.RECOMMENDATION,
                evidence_ids=[],
                verification_status=VerificationStatus.VERIFIED,
                verification_source="ENGINEERING_PROCEDURE",
                conflict_lifecycle=conflict_lifecycle,
            ))

        return claims
