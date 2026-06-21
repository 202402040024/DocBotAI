import logging
import os
from typing import Dict, List, Any, Tuple
from app.core.config import settings
from app.repositories.document import DocumentRepository
from app.repositories.analytics import AnalyticsRepository
from app.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)

# Lower threshold on Render — lighter model produces slightly lower scores
_IS_PRODUCTION = bool(os.getenv("RENDER", ""))
_THRESHOLD = 0.25 if _IS_PRODUCTION else settings.SIMILARITY_THRESHOLD


class RAGEngine:
    def __init__(self):
        self.doc_repository = DocumentRepository()
        self.analytics_repository = AnalyticsRepository()

    async def retrieve_context(
        self, user_id: str, query: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """
        Retrieves context chunks from FAISS + MongoDB.
        Returns: (chunks, citations, is_rag_active)
        """
        await self.analytics_repository.increment_searches_performed(user_id)

        # 1. Search FAISS
        similar_items = vector_store_service.search_similar(user_id, query, settings.TOP_K)
        if not similar_items:
            logger.info(f"No FAISS results for user {user_id}")
            return [], [], False

        # 2. Threshold check
        max_score = similar_items[0]["similarity_score"]
        is_rag_active = max_score >= _THRESHOLD
        logger.info(
            f"FAISS top score={max_score:.4f} threshold={_THRESHOLD} "
            f"production={_IS_PRODUCTION} rag_active={is_rag_active}"
        )

        if not is_rag_active:
            return [], [], False

        # 3. Fetch chunk content + doc metadata
        chunks_data: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []

        for item in similar_items:
            if item["similarity_score"] < _THRESHOLD:
                continue

            chunk = await self.doc_repository.get_chunk_by_faiss_id(item["chunk_id"])
            if not chunk:
                continue

            doc = await self.doc_repository.get_document(
                str(chunk["document_id"]), user_id
            )
            doc_name = doc["original_filename"] if doc else "Unknown Document"

            chunks_data.append(chunk)
            citations.append({
                "document_name": doc_name,
                "page_number": chunk.get("page_number", 1),
                "paragraph_number": chunk.get("paragraph_number", 1),
                "similarity_score": round(item["similarity_score"], 4),
            })

        if chunks_data:
            await self.analytics_repository.increment_retrieval_count(user_id)

        return chunks_data, citations, bool(chunks_data)

    def build_rag_system_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        context_parts = []
        for idx, chunk in enumerate(chunks):
            context_parts.append(f"--- Source {idx + 1} ---\n{chunk['chunk_text']}")
        context_str = "\n\n".join(context_parts)

        return (
            "You are an advanced Multi-Document AI Assistant with access to the user's uploaded documents.\n\n"
            "RETRIEVED DOCUMENT CONTEXT:\n"
            f"{context_str}\n\n"
            "INSTRUCTIONS:\n"
            "1. Answer using the document context above as your primary source.\n"
            "2. Be factual, clear, and concise.\n"
            "3. If the context lacks the answer, say so and provide a general knowledge answer "
            "clearly marked as '[General Knowledge]'.\n"
            "4. Cite which source you used when relevant.\n"
            "5. Maintain a professional, helpful tone."
        )

    def build_general_system_prompt(self) -> str:
        return (
            "You are a helpful, intelligent general-purpose AI assistant.\n"
            "The user has not uploaded any relevant documents for this query.\n"
            "Answer clearly, accurately, and helpfully based on your general knowledge."
        )


rag_engine = RAGEngine()
