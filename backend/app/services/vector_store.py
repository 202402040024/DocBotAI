import os
import json
import logging
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)

class VectorStoreService:
    def _get_paths(self, user_id: str) -> Tuple[str, str]:
        index_path = os.path.join(settings.vector_stores_dir, f"user_{user_id}.index")
        mapping_path = os.path.join(settings.vector_stores_dir, f"user_{user_id}.json")
        return index_path, mapping_path

    def add_chunks(self, user_id: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Generates embeddings for chunks and adds them to the user's FAISS index.
        """
        if not chunks:
            return False

        try:
            texts = [c["chunk_text"] for c in chunks]
            embeddings = embedding_service.get_embeddings(texts)
            embeddings_np = np.array(embeddings, dtype=np.float32)

            index_path, mapping_path = self._get_paths(user_id)
            dim = embedding_service.dimension

            # Load existing or create new
            if os.path.exists(index_path) and os.path.exists(mapping_path):
                index = faiss.read_index(index_path)
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
            else:
                index = faiss.IndexFlatIP(dim)
                mapping = []

            # Add to index
            start_idx = index.ntotal
            index.add(embeddings_np)

            # Update mapping
            for idx, chunk in enumerate(chunks):
                mapping.append({
                    "faiss_id": start_idx + idx,
                    "chunk_id": chunk["chunk_id"],
                    "document_id": str(chunk["document_id"])
                })

            # Save
            faiss.write_index(index, index_path)
            with open(mapping_path, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

            logger.info(f"Added {len(chunks)} chunks to FAISS for user {user_id}. Total chunks: {index.ntotal}")
            return True
        except Exception as e:
            logger.error(f"Error adding chunks to FAISS for user {user_id}: {e}")
            return False

    def search_similar(self, user_id: str, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Searches the user's FAISS index for relevant chunks.
        Returns a list of dicts with: 'chunk_id', 'similarity_score'.
        """
        top_k = top_k or settings.TOP_K
        index_path, mapping_path = self._get_paths(user_id)

        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            return []

        try:
            query_emb = embedding_service.get_embedding(query)
            query_np = np.array([query_emb], dtype=np.float32)

            index = faiss.read_index(index_path)
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)

            # Limit top_k to total index items
            k = min(top_k, index.ntotal)
            if k == 0:
                return []

            # Search FAISS
            scores, indices = index.search(query_np, k)

            results = []
            for score, faiss_idx in zip(scores[0], indices[0]):
                if faiss_idx == -1 or faiss_idx >= len(mapping):
                    continue
                
                # Retrieve corresponding chunk_id
                map_item = mapping[faiss_idx]
                results.append({
                    "chunk_id": map_item["chunk_id"],
                    "similarity_score": float(score)
                })

            return results
        except Exception as e:
            logger.error(f"Error searching FAISS for user {user_id}: {e}")
            return []

    def rebuild_index(self, user_id: str, all_chunks: List[Dict[str, Any]]) -> bool:
        """
        Recreates the FAISS index and mapping file from scratch for the user.
        Used when documents are deleted or modified.
        """
        index_path, mapping_path = self._get_paths(user_id)

        # Remove files first
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(mapping_path):
            os.remove(mapping_path)

        if not all_chunks:
            logger.info(f"Rebuilt index for user {user_id} (index is now empty).")
            return True

        try:
            texts = [c["chunk_text"] for c in all_chunks]
            embeddings = embedding_service.get_embeddings(texts)
            embeddings_np = np.array(embeddings, dtype=np.float32)

            dim = embedding_service.dimension
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings_np)

            mapping = []
            for idx, chunk in enumerate(all_chunks):
                mapping.append({
                    "faiss_id": idx,
                    "chunk_id": chunk["chunk_id"],
                    "document_id": str(chunk["document_id"])
                })

            faiss.write_index(index, index_path)
            with open(mapping_path, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

            logger.info(f"Rebuilt index for user {user_id} with {len(all_chunks)} chunks.")
            return True
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index for user {user_id}: {e}")
            return False

vector_store_service = VectorStoreService()
