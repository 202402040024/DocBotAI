import logging
import os
import numpy as np
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

# Use a lighter model on Render free tier to save RAM
# Override via EMBEDDING_MODEL_NAME env var
_IS_PRODUCTION = os.getenv("RENDER", "") or os.getenv("RAILWAY_ENVIRONMENT", "")

class EmbeddingService:
    def __init__(self):
        self.model = None
        # Use smaller model in production to fit in 512MB RAM
        if _IS_PRODUCTION:
            self.model_name = "sentence-transformers/all-MiniLM-L6-v2"  # 80MB vs 130MB
        else:
            self.model_name = settings.EMBEDDING_MODEL_NAME
        self.fallback_model_name = "sentence-transformers/paraphrase-MiniLM-L3-v2"  # 60MB
        self.dimension = 384

    def _load_model(self):
        if self.model is not None:
            return

        for model_name in [self.model_name, self.fallback_model_name]:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {model_name}...")
                self.model = SentenceTransformer(model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"Model loaded: {model_name} | dim={self.dimension}")
                return
            except Exception as e:
                logger.warning(f"Failed to load {model_name}: {e}")

        logger.warning("All embedding models failed — using mock embeddings")
        self.model = "mock"
        self.dimension = 384

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if not texts:
            return []

        if self.model == "mock":
            return self._generate_mock_embeddings(texts)

        try:
            # Process in small batches to avoid OOM on free tier
            batch_size = 16
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                emb = self.model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                all_embeddings.append(emb)

            embeddings = np.vstack(all_embeddings)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return (embeddings / norms).tolist()
        except Exception as e:
            logger.error(f"Embedding error: {e} — falling back to mock")
            return self._generate_mock_embeddings(texts)

    def get_embedding(self, text: str) -> List[float]:
        return self.get_embeddings([text])[0]

    def _generate_mock_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            seed = abs(hash(text)) % (2**32 - 1)
            rng = np.random.default_rng(seed)
            vec = rng.normal(0, 1, self.dimension)
            norm = np.linalg.norm(vec)
            vec = (vec / norm).tolist() if norm > 0 else vec.tolist()
            embeddings.append(vec)
        return embeddings


embedding_service = EmbeddingService()
