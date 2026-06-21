import logging
from typing import Dict, List
from app.repositories.chat import ChatRepository

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.chat_repository = ChatRepository()

    async def get_conversation_history(self, session_id: str, limit: int = 12) -> List[Dict[str, str]]:
        """
        Retrieves the last `limit` messages of a session from MongoDB,
        formatted for the LLM.
        """
        raw_messages = await self.chat_repository.get_messages(session_id)
        
        # We only keep the most recent messages up to the limit
        recent_messages = raw_messages[-limit:] if len(raw_messages) > limit else raw_messages
        
        formatted_messages = []
        for msg in recent_messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        return formatted_messages

    async def get_contextual_prompt(self, session_id: str, current_query: str, system_prompt: str) -> List[Dict[str, str]]:
        """
        Assembles the full prompt messages array, incorporating the system prompt,
        retrieved history, and the current query.
        """
        history = await self.get_conversation_history(session_id)
        
        messages = []
        # Prepend system instruction
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add history
        messages.extend(history)
        
        # Add the current question
        messages.append({
            "role": "user",
            "content": current_query
        })
        
        return messages

memory_service = MemoryService()
