from datetime import datetime, timezone
from typing import Any, Dict
from bson import ObjectId
from server.database.mongodb import get_database

class AnalyticsRepository:
    @property
    def analytics_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["analytics"]

    @property
    def docs_collection(self):
        db = get_database()
        return db["uploaded_documents"]

    @property
    def sessions_collection(self):
        db = get_database()
        return db["chat_sessions"]

    async def get_analytics(self, user_id: str) -> Dict[str, Any]:
        try:
            uid = ObjectId(user_id)
            stats = await self.analytics_collection.find_one({"user_id": uid})
            if not stats:
                stats = {
                    "user_id": uid,
                    "total_questions": 0,
                    "documents_uploaded": 0,
                    "searches_performed": 0,
                    "retrieval_count": 0
                }
                await self.analytics_collection.insert_one(stats)
            return stats
        except Exception:
            return {}

    async def increment_counter(self, user_id: str, field: str, amount: int = 1):
        try:
            uid = ObjectId(user_id)
            await self.analytics_collection.update_one(
                {"user_id": uid},
                {"$inc": {field: amount}},
                upsert=True
            )
        except Exception:
            pass

    async def increment_total_questions(self, user_id: str):
        await self.increment_counter(user_id, "total_questions")

    async def increment_documents_uploaded(self, user_id: str, count: int = 1):
        await self.increment_counter(user_id, "documents_uploaded", count)

    async def increment_searches_performed(self, user_id: str):
        await self.increment_counter(user_id, "searches_performed")

    async def increment_retrieval_count(self, user_id: str):
        await self.increment_counter(user_id, "retrieval_count")

    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            uid = ObjectId(user_id)
            # Count total uploaded documents
            total_docs = await self.docs_collection.count_documents({"user_id": uid})
            # Count total chat sessions
            total_chats = await self.sessions_collection.count_documents({"user_id": uid})
            # Fetch general analytics counters
            counters = await self.get_analytics(user_id)
            
            # Fetch recent 5 uploads
            recent_uploads_cursor = self.docs_collection.find({"user_id": uid}).sort("upload_time", -1).limit(5)
            recent_uploads = await recent_uploads_cursor.to_list(length=5)
            # Serialize ObjectId
            for doc in recent_uploads:
                doc["_id"] = str(doc["_id"])
                doc["user_id"] = str(doc["user_id"])
                if "upload_time" in doc:
                    doc["upload_time"] = doc["upload_time"].isoformat()

            # Fetch recent 5 chat sessions
            recent_chats_cursor = self.sessions_collection.find({"user_id": uid}).sort("updated_at", -1).limit(5)
            recent_chats = await recent_chats_cursor.to_list(length=5)
            # Serialize ObjectId
            for chat in recent_chats:
                chat["_id"] = str(chat["_id"])
                chat["user_id"] = str(chat["user_id"])
                if "created_at" in chat:
                    chat["created_at"] = chat["created_at"].isoformat()
                if "updated_at" in chat:
                    chat["updated_at"] = chat["updated_at"].isoformat()
            
            return {
                "total_documents": total_docs,
                "total_chats": total_chats,
                "total_questions": counters.get("total_questions", 0),
                "retrieval_count": counters.get("retrieval_count", 0),
                "searches_performed": counters.get("searches_performed", 0),
                "recent_uploads": recent_uploads,
                "recent_conversations": recent_chats
            }
        except Exception as e:
            # Return empty structure on failure
            return {
                "total_documents": 0,
                "total_chats": 0,
                "total_questions": 0,
                "retrieval_count": 0,
                "searches_performed": 0,
                "recent_uploads": [],
                "recent_conversations": []
            }
