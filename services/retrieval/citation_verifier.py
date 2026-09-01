"""Deterministic citation verifier auditing document-derived claims against retrieved chunks."""
from typing import List, Tuple
from domain.claims.models import Claim, VerificationStatus
from domain.models.results import RetrievedDocumentChunk


class CitationVerifier:
    """Audits claims citing technical documentation against actually retrieved chunks."""

    @classmethod
    def verify_document_claim(
        cls,
        claim: Claim,
        retrieved_chunks: List[RetrievedDocumentChunk],
    ) -> Tuple[VerificationStatus, str]:
        if not claim.evidence_ids:
            return VerificationStatus.REJECTED, "Claim contains no evidence reference to support documentation citation."

        # Check if cited evidence matches any chunk in the retrieved set
        matching_chunks = [ch for ch in retrieved_chunks if any(ev in ch.doc_id or ev in ch.chunk_id for ev in claim.evidence_ids)]
        if not matching_chunks:
            return VerificationStatus.REJECTED, f"Cited chunk '{claim.evidence_ids}' was not found in the verified retrieval set."

        # Verify keyword overlap between claim statement and chunk content
        claim_words = set(w.lower() for w in claim.statement.split() if len(w) > 3)
        found_overlap = False
        for ch in matching_chunks:
            chunk_words = set(w.lower() for w in ch.content.split())
            if len(claim_words.intersection(chunk_words)) >= 2:
                found_overlap = True
                break

        if not found_overlap:
            return VerificationStatus.REJECTED, "Claim statement text is not supported by the cited document chunk content."

        return VerificationStatus.VERIFIED, f"Verified against {matching_chunks[0].doc_id} ({matching_chunks[0].section})"
