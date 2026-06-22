from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from server.database.mongodb import get_database

class ChatRepository:
    @property
    def sessions_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["chat_sessions"]

    @property
    def messages_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["chat_messages"]

    async def create_session(self, user_id: str, title: str) -> Dict[str, Any]:
        session = {
            "user_id": ObjectId(user_id),
            "title": title,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        result = await self.sessions_collection.insert_one(session)
        session["_id"] = result.inserted_id
        return session

    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.sessions_collection.find_one({
                "_id": ObjectId(session_id),
                "user_id": ObjectId(user_id)
            })
        except Exception:
            return None

    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.sessions_collection.find({"user_id": ObjectId(user_id)}).sort("updated_at", -1)
        return await cursor.to_list(length=100)

    async def rename_session(self, session_id: str, user_id: str, title: str) -> bool:
        try:
            result = await self.sessions_collection.update_one(
                {"_id": ObjectId(session_id), "user_id": ObjectId(user_id)},
                {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        try:
            sid = ObjectId(session_id)
            uid = ObjectId(user_id)
            # Verify ownership
            session = await self.sessions_collection.find_one({"_id": sid, "user_id": uid})
            if not session:
                return False
            
            # Delete messages first
            await self.messages_collection.delete_many({"session_id": sid})
            # Delete session
            result = await self.sessions_collection.delete_one({"_id": sid})
            return result.deleted_count > 0
        except Exception:
            return False

    async def create_message(self, session_id: str, role: str, content: str, citations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        message = {
            "session_id": ObjectId(session_id),
            "role": role,
            "content": content,
            "citations": citations or [],
            "timestamp": datetime.now(timezone.utc)
        }
        result = await self.messages_collection.insert_one(message)
        message["_id"] = result.inserted_id
        
        # Touch session's updated_at
        await self.sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )
        return message

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.messages_collection.find({"session_id": ObjectId(session_id)}).sort("timestamp", 1)
            return await cursor.to_list(length=200)
        except Exception:
            return []

    async def search_sessions(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        # Match sessions where title matches OR any of the session's messages match the query.
        try:
            uid = ObjectId(user_id)
            
            # 1. Search session titles
            title_matches = await self.sessions_collection.find({
                "user_id": uid,
                "title": {"$regex": query, "$options": "i"}
            }).to_list(length=50)
            
            matched_session_ids = {s["_id"] for s in title_matches}
            
            # 2. Search message contents
            message_matches = await self.messages_collection.aggregate([
                {
                    "$match": {"content": {"$regex": query, "$options": "i"}}
                },
                {
                    "$lookup": {
                        "from": "chat_sessions",
                        "localField": "session_id",
                        "foreignField": "_id",
                        "as": "session"
                    }
                },
                {"$unwind": "$session"},
                {
                    "$match": {"session.user_id": uid}
                },
                {
                    "$group": {
                        "_id": "$session._id",
                        "title": {"$first": "$session.title"},
                        "created_at": {"$first": "$session.created_at"},
                        "updated_at": {"$first": "$session.updated_at"}
                    }
                }
            ]).to_list(length=50)
            
            # Combine
            all_sessions = title_matches.copy()
            for s in message_matches:
                if s["_id"] not in matched_session_ids:
                    all_sessions.append({
                        "_id": s["_id"],
                        "user_id": uid,
                        "title": s["title"],
                        "created_at": s["created_at"],
                        "updated_at": s["updated_at"]
                    })
            
            # Sort combined results by updated_at descending
            all_sessions.sort(key=lambda x: x["updated_at"], reverse=True)
            return all_sessions
        except Exception:
            return []
