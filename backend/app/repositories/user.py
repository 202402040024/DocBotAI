from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bson import ObjectId
from app.database.mongodb import get_database

class UserRepository:
    @property
    def collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["users"]

    @property
    def settings_collection(self):
        db = get_database()
        if db is None:
            raise RuntimeError("Database not initialized")
        return db["settings"]

    async def create_user(self, name: str, email: str, password_hash: str) -> Dict[str, Any]:
        user = {
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        result = await self.collection.insert_one(user)
        user["_id"] = result.inserted_id
        
        # Initialize default settings for user
        await self.settings_collection.insert_one({
            "user_id": user["_id"],
            "theme": "dark",
            "model_preferences": {
                "primary_model": "gemini",
                "temperature": 0.7
            },
            "created_at": datetime.now(timezone.utc)
        })
        return user

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"email": email.lower()})

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    async def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.settings_collection.find_one({"user_id": ObjectId(user_id)})
        except Exception:
            return None

    async def update_user_settings(self, user_id: str, theme: str, model_preferences: Dict[str, Any]) -> bool:
        try:
            uid = ObjectId(user_id)
            result = await self.settings_collection.update_one(
                {"user_id": uid},
                {
                    "$set": {
                        "theme": theme,
                        "model_preferences": model_preferences,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception:
            return False
