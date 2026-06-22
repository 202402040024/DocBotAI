"""
Embedding service ΓÇö uses Gemini gemini-embedding-001 API (3072 dim).
No sentence-transformers / torch required ΓåÆ fits in Render free tier.
Falls back to deterministic hash-based vectors if Gemini key is missing or fails.
"""
import hashlib
import logging
from typing import List

import httpx
import numpy as np

from server.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = "gemini-embedding-001"
GEMINI_EMBED_DIM = 3072
FALLBACK_DIM = 384


class EmbeddingService:
    def __init__(self):
        self._use_gemini = bool(settings.GEMINI_API_KEY)
        self.dimension = GEMINI_EMBED_DIM if self._use_gemini else FALLBACK_DIM
        logger.info(
            f"EmbeddingService ΓÇö mode={'gemini' if self._use_gemini else 'hash-fallback'}, "
            f"dim={self.dimension}"
        )

    # ΓöÇΓöÇ Public API ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._use_gemini:
            try:
                return self._gemini_batch(texts)
            except Exception as e:
                logger.warning(f"Gemini embedding failed ({e}), using hash fallback")
                self.dimension = FALLBACK_DIM
        return [self._hash_vector(t, FALLBACK_DIM) for t in texts]

    def get_embedding(self, text: str) -> List[float]:
        return self.get_embeddings([text])[0]

    # ΓöÇΓöÇ Gemini API ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def _gemini_batch(self, texts: List[str]) -> List[List[float]]:
        """Call embedContent one by one ΓÇö batchEmbedContents not supported for this model."""
        results = []
        for text in texts:
            vec = self._gemini_single(text)
            results.append(vec)
        # Update dimension from first result
        if results:
            self.dimension = len(results[0])
        return results

    def _gemini_single(self, text: str) -> List[float]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_EMBED_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "content": {"parts": [{"text": text[:8000]}]}  # cap at 8k chars
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        vec = data.get("embedding", {}).get("values", [])
        if not vec:
            raise ValueError("Empty embedding returned from Gemini")
        return self._normalize(vec)

    # ΓöÇΓöÇ Fallback ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def _hash_vector(self, text: str, dim: int) -> List[float]:
        """Deterministic pseudo-embedding using SHA-256 seeded RNG."""
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2 ** 32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim).astype(np.float32)
        return self._normalize(vec.tolist())

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        arr = np.array(vec, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if norm < 1e-9:
            return arr.tolist()
        return (arr / norm).tolist()


embedding_service = EmbeddingService()
