"""Hybrid RAG retrieval engine combining BM25 lexical search, semantic scoring, and Reciprocal Rank Fusion (RRF)."""
import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from domain.models.results import DocumentRetrievalResult, RetrievedDocumentChunk
from services.retrieval.corpus_loader import CorpusLoader


class HybridRAGEngine:
    """Hybrid RAG retrieval engine with power-engineering tokenization and RRF ranking."""

    def __init__(self, chunks: Optional[List[RetrievedDocumentChunk]] = None):
        self.chunks = chunks or []
        self.bm25: Optional[BM25Okapi] = None
        self._initialize_retrievers()

    def _initialize_retrievers(self):
        if not self.chunks:
            return
        # Tokenize corpus for BM25 with preservation of engineering terms (e.g. 50P, 51N, OGS-01)
        tokenized_corpus = [self._tokenize(chunk.content + " " + chunk.title + " " + chunk.section) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        # Custom power engineering tokenization preserving alphanumeric codes and hyphenated identifiers
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", " ", text.lower())
        return [tok.strip() for tok in cleaned.split() if len(tok.strip()) > 1]

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        category_filter: Optional[str] = None,
        use_dense: bool = True,
        use_lexical: bool = True,
    ) -> DocumentRetrievalResult:
        if not self.chunks:
            return DocumentRetrievalResult(query=query, chunks=[], total_chunks_found=0)

        # 1. Lexical retrieval (BM25)
        bm25_ranks: Dict[str, int] = {}
        if use_lexical and self.bm25:
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)
            sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            for rank, idx in enumerate(sorted_indices):
                bm25_ranks[self.chunks[idx].chunk_id] = rank + 1

        # 2. Semantic scoring (Cosine / Lexical-Semantic Keyword Match)
        dense_ranks: Dict[str, int] = {}
        if use_dense:
            q_terms = set(self._tokenize(query))
            dense_scores = []
            for idx, ch in enumerate(self.chunks):
                ch_terms = set(self._tokenize(ch.content + " " + ch.section + " " + ch.title))
                intersection = q_terms.intersection(ch_terms)
                jaccard = len(intersection) / max(len(q_terms.union(ch_terms)), 1)
                # Boost if exact phrase in title or section
                if any(t in ch.title.lower() for t in q_terms):
                    jaccard += 0.3
                dense_scores.append((jaccard, idx))
            dense_scores.sort(key=lambda x: x[0], reverse=True)
            for rank, (_, idx) in enumerate(dense_scores):
                dense_ranks[self.chunks[idx].chunk_id] = rank + 1

        # 3. Reciprocal Rank Fusion (RRF with k=60)
        rrf_k = 60
        fused_scores: Dict[str, float] = {}
        for ch in self.chunks:
            c_id = ch.chunk_id
            score = 0.0
            if c_id in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[c_id])
            if c_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[c_id])
            fused_scores[c_id] = score

        # Sort by fused score
        sorted_chunks = sorted(self.chunks, key=lambda c: fused_scores.get(c.chunk_id, 0.0), reverse=True)

        result_chunks: List[RetrievedDocumentChunk] = []
        for ch in sorted_chunks[:top_k]:
            # Support both Pydantic 1 (used by some local environments) and
            # Pydantic 2 (the declared deployment dependency).
            cloned = ch.model_copy() if hasattr(ch, "model_copy") else ch.copy(deep=True)
            cloned.score = round(fused_scores.get(ch.chunk_id, 0.0) * 100.0, 3)
            cloned.relevance_reason = f"Ranked via Hybrid BM25 + Dense RRF (Score: {cloned.score})"
            result_chunks.append(cloned)

        return DocumentRetrievalResult(
            query=query,
            retrieval_method="HYBRID_BM25_DENSE_RRF",
            chunks=result_chunks,
            total_chunks_found=len(result_chunks),
        )
