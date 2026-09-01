"""Unit tests for Hybrid RAG and Citation Verifier."""
import pytest
from services.retrieval.corpus_loader import CorpusLoader
from services.retrieval.hybrid_rag import HybridRAGEngine
from services.retrieval.citation_verifier import CitationVerifier
from domain.claims.models import Claim, ClaimType, VerificationStatus


@pytest.mark.asyncio
async def test_hybrid_rag_retrieval():
    chunks = CorpusLoader.load_documents_from_directory("data/documents")
    assert len(chunks) > 0, "Corpus documents must be chunked."

    engine = HybridRAGEngine(chunks)
    res = await engine.retrieve("ANSI 51 time overcurrent protection curve", top_k=2)
    assert len(res.chunks) == 2
    assert any("DOC-PROT-001" in ch.doc_id for ch in res.chunks)


def test_citation_verifier_valid_and_invalid():
    chunks = CorpusLoader.load_documents_from_directory("data/documents")
    
    valid_claim = Claim(
        claim_id="C01",
        statement="ANSI 51 specifies inverse time overcurrent protection with time dial coordination.",
        claim_type=ClaimType.FACT,
        evidence_ids=["DOC-PROT-001"],
    )
    status, note = CitationVerifier.verify_document_claim(valid_claim, chunks)
    assert status == VerificationStatus.VERIFIED

    fake_claim = Claim(
        claim_id="C02",
        statement="Transformer T1 generates free solar energy without loss.",
        claim_type=ClaimType.FACT,
        evidence_ids=["DOC-PROT-001"],
    )
    fake_status, fake_note = CitationVerifier.verify_document_claim(fake_claim, chunks)
    assert fake_status == VerificationStatus.REJECTED
