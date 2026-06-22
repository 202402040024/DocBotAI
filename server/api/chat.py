import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from server.api.auth_deps import get_current_user
from server.repositories.chat import ChatRepository
from server.repositories.analytics import AnalyticsRepository
from server.services.rag_engine import rag_engine
from server.services.memory import memory_service
from server.services.llm import llm_service
from server.schemas.schemas import ChatSessionCreate, ChatQueryRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

chat_repository = ChatRepository()
analytics_repository = AnalyticsRepository()

@router.post("/new")
async def create_chat_session(session_data: ChatSessionCreate, current_user: dict = Depends(get_current_user)):
    session = await chat_repository.create_session(current_user["id"], session_data.title)
    return {
        "id": str(session["_id"]),
        "title": session["title"],
        "created_at": session["created_at"].isoformat()
    }

@router.get("/history")
async def get_chat_history(
    query: Optional[str] = Query(None, description="Search chats by session title or message content"),
    current_user: dict = Depends(get_current_user)
):
    if query:
        sessions = await chat_repository.search_sessions(current_user["id"], query)
    else:
        sessions = await chat_repository.list_sessions(current_user["id"])
        
    for s in sessions:
        s["id"] = str(s["_id"])
        s["_id"] = str(s["_id"])
        s["user_id"] = str(s["user_id"])
        if "created_at" in s:
            s["created_at"] = s["created_at"].isoformat()
        if "updated_at" in s:
            s["updated_at"] = s["updated_at"].isoformat()
    return sessions

@router.delete("/{id}")
async def delete_chat_session(id: str, current_user: dict = Depends(get_current_user)):
    success = await chat_repository.delete_session(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized")
    return {"message": "Chat session and messages deleted successfully"}

@router.put("/{id}")
async def rename_chat_session(id: str, title: str = Query(...), current_user: dict = Depends(get_current_user)):
    if not title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")
        
    success = await chat_repository.rename_session(id, current_user["id"], title.strip())
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or unauthorized")
    return {"message": "Chat session renamed successfully"}

@router.post("")
async def query_chat(
    request: ChatQueryRequest,
    session_id: Optional[str] = Query(None, description="Optional active session ID"),
    stream: bool = Query(False, description="Set to true for SSE streaming responses"),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    query = request.query
    
    # 1. Resolve or create chat session
    active_session_id = session_id
    if not active_session_id:
        # Generate session title using first 30 chars of query
        title = query[:30] + "..." if len(query) > 30 else query
        session = await chat_repository.create_session(user_id, title)
        active_session_id = str(session["_id"])

    # 2. Trigger analytics
    await analytics_repository.increment_total_questions(user_id)

    # 3. Retrieve context & citations using RAG Engine
    chunks, citations, is_rag_active = await rag_engine.retrieve_context(user_id, query)

    # 4. Construct prompts
    if is_rag_active:
        system_prompt = rag_engine.build_rag_system_prompt(chunks)
    else:
        system_prompt = rag_engine.build_general_system_prompt()

    # 5. Fetch message history & assemble prompt messages
    # Fetch last 10 messages (5 turns) to stay within reasonable token/time counts
    messages = await memory_service.get_contextual_prompt(active_session_id, query, system_prompt)

    # 6. Save user query message to DB
    await chat_repository.create_message(active_session_id, "user", query)

    # 7. Route and respond
    if stream:
        async def response_streamer():
            full_response = ""
            
            # Send session information first
            yield f"data: {json.dumps({'type': 'session', 'session_id': active_session_id})}\n\n"
            
            try:
                # Stream content from LLM
                async for chunk in llm_service.stream_response(messages):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Error in chat streaming: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
            # Write assistant message to DB
            if full_response.strip():
                await chat_repository.create_message(active_session_id, "assistant", full_response, citations)
                
            # Send citations
            yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(response_streamer(), media_type="text/event-stream")

    else:
        # Non-streaming response
        try:
            assistant_response = await llm_service.generate_response(messages)
            
            # Save assistant message to DB
            await chat_repository.create_message(active_session_id, "assistant", assistant_response, citations)
            
            # Fetch message list to get timestamps/id format
            db_messages = await chat_repository.get_messages(active_session_id)
            serialized = []
            for msg in db_messages:
                serialized.append({
                    "id": str(msg["_id"]),
                    "role": msg["role"],
                    "content": msg["content"],
                    "citations": msg.get("citations", []),
                    "timestamp": msg["timestamp"].isoformat()
                })
                
            return {
                "session_id": active_session_id,
                "messages": serialized
            }
        except Exception as e:
            logger.error(f"Error generating non-streaming response: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate AI response: {e}"
            )
            
@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    # Verify session belongs to user
    session = await chat_repository.get_session(session_id, current_user["id"])
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        
    messages = await chat_repository.get_messages(session_id)
    serialized = []
    for msg in messages:
        serialized.append({
            "id": str(msg["_id"]),
            "role": msg["role"],
            "content": msg["content"],
            "citations": msg.get("citations", []),
            "timestamp": msg["timestamp"].isoformat()
        })
    return serialized
