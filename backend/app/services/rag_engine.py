import logging
from typing import Dict, List, Any, Tuple
from app.core.config import settings
from app.repositories.document import DocumentRepository
from app.repositories.analytics import AnalyticsRepository
from app.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        self.doc_repository = DocumentRepository()
        self.analytics_repository = AnalyticsRepository()

    async def retrieve_context(self, user_id: str, query: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """
        Retrieves context chunks from FAISS and MongoDB.
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]
            - List of raw chunk objects with texts
            - List of citations (serializable)
            - Boolean flag indicating if similarities met the threshold (RAG active)
        """
        # Increment search performed counter
        await self.analytics_repository.increment_searches_performed(user_id)

        # 1. Search FAISS
        similar_items = vector_store_service.search_similar(user_id, query, settings.TOP_K)
        if not similar_items:
            return [], [], False

        # 2. Check if highest similarity score meets the threshold
        max_score = similar_items[0]["similarity_score"]
        is_rag_active = max_score >= settings.SIMILARITY_THRESHOLD
        logger.info(f"FAISS search maximum score: {max_score:.4f}. Threshold: {settings.SIMILARITY_THRESHOLD}. RAG active: {is_rag_active}")

        if not is_rag_active:
            # Although similar chunks were found, their similarity is below threshold. Use general mode.
            return [], [], False

        # 3. Retrieve chunk contents and doc metadata from MongoDB
        chunks_data = []
        citations = []

        for item in similar_items:
            # We filter chunks below threshold for retrieval, but keep the highest ones
            if item["similarity_score"] < settings.SIMILARITY_THRESHOLD:
                continue

            chunk = await self.doc_repository.get_chunk_by_faiss_id(item["chunk_id"])
            if not chunk:
                continue

            # Fetch original document metadata
            doc = await self.doc_repository.get_document(str(chunk["document_id"]), user_id)
            doc_name = doc["original_filename"] if doc else "Unknown Document"

            chunks_data.append(chunk)
            citations.append({
                "document_name": doc_name,
                "page_number": chunk.get("page_number", 1),
                "paragraph_number": chunk.get("paragraph_number", 1),
                "similarity_score": round(item["similarity_score"], 4)
            })

        if chunks_data:
            await self.analytics_repository.increment_retrieval_count(user_id)

        return chunks_data, citations, True

    def build_rag_system_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        context_str = ""
        for idx, chunk in enumerate(chunks):
            context_str += f"\n--- CHUNK {idx+1} ---\n{chunk['chunk_text']}\n"

        return (
            "You are an advanced Multi-Document AI Assistant. You have access to relevant document excerpts uploaded by the user.\n"
            "Here is the context retrieved from the documents:\n"
            f"{context_str}\n"
            "Instructions:\n"
            "1. Answer the user's question utilizing ONLY the provided document context above.\n"
            "2. Be extremely factual, clear, and concise.\n"
            "3. If the context does not contain relevant information to answer the question, state politely that the uploaded documents do not contain the answer, and then provide a general assistant answer clearly marked as 'General Knowledge Answer:'.\n"
            "4. Maintain a professional tone."
        )

    def build_general_system_prompt(self) -> str:
        return (
            "You are a helpful, intelligent general-purpose AI assistant.\n"
            "Answer the user's questions clearly, accurately, and politely.\n"
            "You are not referencing any uploaded document contexts for this answer."
        )

rag_engine = RAGEngine()
