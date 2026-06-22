from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from server.database.mongodb import get_database

class DocumentRepository:
    @property
    def docs_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["uploaded_documents"]

    @property
    def chunks_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["document_chunks"]

    async def create_document(self, user_id: str, filename: str, original_filename: str, file_type: str, version: int = 1) -> Dict[str, Any]:
        document = {
            "user_id": ObjectId(user_id),
            "filename": filename,
            "original_filename": original_filename,
            "file_type": file_type,
            "upload_time": datetime.now(timezone.utc),
            "document_version": version
        }
        result = await self.docs_collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.docs_collection.find_one({
                "_id": ObjectId(document_id),
                "user_id": ObjectId(user_id)
            })
        except Exception:
            return None

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.docs_collection.find({"user_id": ObjectId(user_id)}).sort("upload_time", -1)
        return await cursor.to_list(length=100)

    async def rename_document(self, document_id: str, user_id: str, new_original_filename: str) -> bool:
        try:
            result = await self.docs_collection.update_one(
                {"_id": ObjectId(document_id), "user_id": ObjectId(user_id)},
                {"$set": {"original_filename": new_original_filename}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        try:
            did = ObjectId(document_id)
            uid = ObjectId(user_id)
            # Verify ownership
            doc = await self.docs_collection.find_one({"_id": did, "user_id": uid})
            if not doc:
                return False
            
            # Delete chunks first
            await self.chunks_collection.delete_many({"document_id": did})
            # Delete document
            result = await self.docs_collection.delete_one({"_id": did})
            return result.deleted_count > 0
        except Exception:
            return False

    async def create_document_chunks(self, document_id: str, chunks: List[Dict[str, Any]]) -> bool:
        try:
            did = ObjectId(document_id)
            chunk_docs = []
            for idx, c in enumerate(chunks):
                chunk_docs.append({
                    "document_id": did,
                    "chunk_id": f"{document_id}_{idx}",
                    "chunk_text": c["chunk_text"],
                    "page_number": c.get("page_number", 1),
                    "paragraph_number": c.get("paragraph_number", idx + 1),
                    "metadata": c.get("metadata", {})
                })
            if chunk_docs:
                result = await self.chunks_collection.insert_many(chunk_docs)
                return len(result.inserted_ids) > 0
            return False
        except Exception:
            return False

    async def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.chunks_collection.find({"document_id": ObjectId(document_id)}).sort("paragraph_number", 1)
            return await cursor.to_list(length=1000)
        except Exception:
            return []

    async def get_all_user_chunks(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            uid = ObjectId(user_id)
            # Find all user document IDs
            cursor = self.docs_collection.find({"user_id": uid})
            docs = await cursor.to_list(length=100)
            doc_ids = [doc["_id"] for doc in docs]
            
            # Find chunks matching these doc IDs
            if not doc_ids:
                return []
            chunks_cursor = self.chunks_collection.find({"document_id": {"$in": doc_ids}})
            return await chunks_cursor.to_list(length=5000)
        except Exception:
            return []
            
    async def get_chunk_by_faiss_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.chunks_collection.find_one({"chunk_id": chunk_id})
        except Exception:
            return None
