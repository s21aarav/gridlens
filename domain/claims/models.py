"""Domain models for atomic verified Claims, strict FACT/INFERENCE/RECOMMENDATION typing, and conflict lifecycles."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    FACT = "FACT"                      # Directly observable or deterministically derived from an authoritative source
    INFERENCE = "INFERENCE"            # Derived from verified facts using an explicit inference rule
    RECOMMENDATION = "RECOMMENDATION"  # Suggested next engineering or field investigation step


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"                      # Verified against authoritative source (for FACT)
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"  # Validated against verified premise claims and rules (for INFERENCE)
    UNVERIFIED = "UNVERIFIED"                  # Pending verification check
    REJECTED = "REJECTED"                      # Fact mismatch or unsupported premise; stripped from final claims
    CONFLICTED = "CONFLICTED"                  # Contradicts another verified fact; enters Conflict Lifecycle


class ConflictLifecycle(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    INVESTIGATION = "INVESTIGATION"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    CONFLICT_UNRESOLVED = "CONFLICT_UNRESOLVED"


class Claim(BaseModel):
    """Atomic claim unit comprising the verified engineering ledger."""
    claim_id: str
    statement: str
    claim_type: ClaimType
    evidence_ids: List[str] = Field(default_factory=list)
    premise_claim_ids: List[str] = Field(default_factory=list)  # Referenced for INFERENCE claims
    inference_rule_id: Optional[str] = None                    # Rule ID defining how inference derives from premises
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_source: Optional[str] = None                  # e.g., "COMTRADE_ANALYZER", "NEO4J_TOPOLOGY", "CONFIG_VALIDATOR"
    conflict_lifecycle: ConflictLifecycle = ConflictLifecycle.NO_CONFLICT
    verification_notes: Optional[str] = None
