"""
Embedding service — uses Gemini text-embedding-004 API.
No sentence-transformers / torch required → fits in Render free tier (512 MB RAM).
Falls back to deterministic hash-based vectors if Gemini key is missing.
"""
import hashlib
import logging
import os
import math
from typing import List

import httpx
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini embedding dimension
GEMINI_EMBED_DIM = 768
FALLBACK_DIM = 384


class EmbeddingService:
    def __init__(self):
        self.dimension = GEMINI_EMBED_DIM if settings.GEMINI_API_KEY else FALLBACK_DIM
        self._use_gemini = bool(settings.GEMINI_API_KEY)
        logger.info(
            f"EmbeddingService init — mode={'gemini' if self._use_gemini else 'hash-fallback'} "
            f"dim={self.dimension}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._use_gemini:
            try:
                return self._gemini_batch(texts)
            except Exception as e:
                logger.warning(f"Gemini embedding failed ({e}), using hash fallback")
        return [self._hash_vector(t, FALLBACK_DIM) for t in texts]

    def get_embedding(self, text: str) -> List[float]:
        return self.get_embeddings([text])[0]

    # ── Gemini API ────────────────────────────────────────────────────────────

    def _gemini_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Call Gemini text-embedding-004 in batches of 100 (API limit).
        Uses httpx synchronously — called from thread pool via run_in_executor.
        """
        results: List[List[float]] = []
        batch_size = 20  # stay well under API limits

        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            batch_results = self._gemini_call(batch)
            results.extend(batch_results)

        self.dimension = len(results[0]) if results else GEMINI_EMBED_DIM
        return results

    def _gemini_call(self, texts: List[str]) -> List[List[float]]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"text-embedding-004:batchEmbedContents?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "requests": [
                {
                    "model": "models/text-embedding-004",
                    "content": {"parts": [{"text": t}]},
                }
                for t in texts
            ]
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        embeddings = []
        for item in data.get("embeddings", []):
            vec = item.get("values", [])
            embeddings.append(self._normalize(vec))
        return embeddings

    # ── Fallback ──────────────────────────────────────────────────────────────

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
