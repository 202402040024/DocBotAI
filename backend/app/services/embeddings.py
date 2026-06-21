import logging
import numpy as np
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.fallback_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.dimension = 384 # Default dimension for MiniLM/BGE small

    def _load_model(self):
        if self.model is not None:
            return

        # Try loading primary model
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading primary embedding model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Primary model loaded successfully. Dimension: {self.dimension}")
            return
        except Exception as e:
            logger.warning(f"Failed to load primary embedding model '{self.model_name}': {e}. Trying fallback...")

        # Try loading fallback model
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading fallback embedding model: {self.fallback_model_name}...")
            self.model = SentenceTransformer(self.fallback_model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Fallback model loaded successfully. Dimension: {self.dimension}")
            return
        except Exception as e:
            logger.error(f"Failed to load fallback embedding model '{self.fallback_model_name}': {e}.")
            logger.warning("Initializing mock embedding fallback for development/offline mode.")
            self.model = "mock"
            self.dimension = 384

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if not texts:
            return []

        if self.model == "mock":
            # Generate random normalized vectors for mock
            embeddings = []
            for text in texts:
                # Seed with text hash to ensure deterministic embeddings for identical texts
                seed = abs(hash(text)) % (2**32 - 1)
                rng = np.random.default_rng(seed)
                vec = rng.normal(0, 1, self.dimension)
                norm = np.linalg.norm(vec)
                vec = (vec / norm).tolist() if norm > 0 else vec.tolist()
                embeddings.append(vec)
            return embeddings

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # Ensure it is normalized for cosine/inner product search
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid divide by zero
            norms[norms == 0] = 1.0
            normalized = (embeddings / norms).tolist()
            return normalized
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Fall back to mock on the fly if model inference fails
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
