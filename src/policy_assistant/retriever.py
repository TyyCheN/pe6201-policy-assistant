"""Semantic retrieval over clauses.

Default backend: sentence embeddings (BAAI/bge-small-en-v1.5), cosine similarity.
Fallback when sentence-transformers is not installed or the model cannot be downloaded:
TF-IDF over word 1-2-grams. The fallback keeps the repo runnable offline; reported
results use the embedding backend.
"""
import numpy as np

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Retriever:
    def __init__(self, clauses, backend="auto"):
        self.clauses = clauses
        texts = [c.search_text for c in clauses]
        self.backend = backend
        if backend in ("auto", "embedding"):
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(EMBED_MODEL)
                self._matrix = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                self.backend = "embedding"
            except Exception as err:  # not installed, or no network for the model download
                if backend == "embedding":
                    raise
                print(f"[retriever] embedding backend unavailable ({type(err).__name__}); using TF-IDF")
                self.backend = "tfidf"
        if self.backend == "tfidf":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
            self._matrix = self._vectorizer.fit_transform(texts)

    def search(self, query, k=5):
        """Return [(clause, score)] for the k most similar clauses, best first."""
        if self.backend == "embedding":
            q = self._model.encode([QUERY_PREFIX + query], normalize_embeddings=True, show_progress_bar=False)
            scores = (self._matrix @ q.T).ravel()
        else:
            scores = (self._matrix @ self._vectorizer.transform([query]).T).toarray().ravel()
        top = np.argsort(-scores)[:k]
        return [(self.clauses[i], float(scores[i])) for i in top]
