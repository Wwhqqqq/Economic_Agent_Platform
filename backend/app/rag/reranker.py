from __future__ import annotations

import re

from langchain_core.documents import Document


class Reranker:
    """Lightweight reranker: term overlap + original score. Optional cross-encoder if installed."""

    def rerank(
        self,
        query: str,
        docs: list[Document],
        *,
        top_k: int = 8,
    ) -> list[Document]:
        if not docs:
            return []
        if len(docs) == 1:
            return docs

        query_terms = self._terms(query)
        scored: list[tuple[float, Document]] = []
        for doc in docs:
            base = float(doc.metadata.get("score", doc.metadata.get("rrf_score", 0.0)))
            overlap = self._overlap_score(query_terms, self._terms(doc.page_content))
            content_boost = 0.0
            ctype = doc.metadata.get("content_type", "")
            if ctype == "table_row":
                content_boost = 0.15
            elif ctype == "table_summary":
                content_boost = 0.08
            elif ctype == "fact":
                content_boost = 0.2
            final = base * 0.45 + overlap * 0.45 + content_boost
            doc.metadata["rerank_score"] = final
            doc.metadata["score"] = final
            scored.append((final, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _terms(self, text: str) -> set[str]:
        text = text.lower()
        terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", text))
        terms.update(w for w in re.findall(r"[a-zA-Z0-9_]{2,}", text))
        return terms

    def _overlap_score(self, query_terms: set[str], doc_terms: set[str]) -> float:
        if not query_terms or not doc_terms:
            return 0.0
        inter = query_terms & doc_terms
        return len(inter) / max(1, len(query_terms))


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
