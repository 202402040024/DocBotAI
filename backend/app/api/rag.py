import json
import logging
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.auth_deps import get_current_user
from app.repositories.document import DocumentRepository
from app.services.rag_engine import rag_engine
from app.services.llm import llm_service
from app.schemas.schemas import RAGQueryRequest, RAGSearchResponseItem, RAGSummarizeRequest, QuizRequest, QuizResponse, QuizQuestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG Services"])

document_repository = DocumentRepository()

@router.post("/query")
async def rag_query(request: RAGQueryRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    query = request.query

    # 1. Retrieve context
    chunks, citations, is_rag_active = await rag_engine.retrieve_context(user_id, query)

    # 2. Build system instruction and generate response
    if is_rag_active:
        system_prompt = rag_engine.build_rag_system_prompt(chunks)
    else:
        system_prompt = "You are a helpful AI document assistant. Note that no relevant context was found in the user's uploaded documents."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    try:
        response_text = await llm_service.generate_response(messages)
        return {
            "answer": response_text,
            "citations": citations,
            "is_rag_active": is_rag_active
        }
    except Exception as e:
        logger.error(f"RAG query generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate RAG response: {e}")

@router.post("/search", response_model=List[RAGSearchResponseItem])
async def rag_semantic_search(request: RAGQueryRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    query = request.query

    # Retrieve matching chunks and citations using the rag_engine retrieve method
    chunks, citations, is_rag_active = await rag_engine.retrieve_context(user_id, query)
    
    # Map raw chunks and citations to response schema
    results = []
    for chunk, citation in zip(chunks, citations):
        results.append(RAGSearchResponseItem(
            chunk_id=chunk["chunk_id"],
            chunk_text=chunk["chunk_text"],
            document_name=citation["document_name"],
            page_number=citation["page_number"],
            paragraph_number=citation["paragraph_number"],
            similarity_score=citation["similarity_score"]
        ))
    return results

@router.post("/summarize")
async def summarize_document(request: RAGSummarizeRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Verify ownership
    doc = await document_repository.get_document(request.document_id, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Fetch all document chunks
    chunks = await document_repository.get_chunks_by_document(request.document_id)
    if not chunks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No text content found in document to summarize")

    # Assemble full text
    full_text = "\n".join([c["chunk_text"] for c in chunks])
    
    # Cap text length to avoid excessive tokens if it's massive, though Gemini supports up to 1M
    # Let's cap at 100k characters (~25k words) for rapid API performance
    if len(full_text) > 100000:
        full_text = full_text[:100000] + "\n[Content truncated for performance...]"

    # Prompt details
    sum_type = request.summary_type.lower()
    if sum_type == "detailed":
        instruction = "Create a detailed, comprehensive summary of the document, explaining main points and detailed analysis."
    elif sum_type == "key_insights":
        instruction = "Create a bullet-point summary focusing strictly on the key insights, takeaways, and major findings of the document."
    else: # short
        instruction = "Create a concise, brief summary summarizing the core purpose and findings of the document in one or two paragraphs."

    prompt = (
        f"You are an expert document summarization system.\n"
        f"Goal: {instruction}\n\n"
        f"Document Name: {doc['original_filename']}\n"
        f"Document Content:\n"
        f"{full_text}\n"
    )

    messages = [
        {"role": "system", "content": "You are a professional research assistant that summarizes text accurately."},
        {"role": "user", "content": prompt}
    ]

    try:
        summary = await llm_service.generate_response(messages, temperature=0.3)
        return {
            "document_id": request.document_id,
            "document_name": doc["original_filename"],
            "summary_type": request.summary_type,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to summarize document: {e}")

@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Verify ownership
    doc = await document_repository.get_document(request.document_id, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Fetch document chunks
    chunks = await document_repository.get_chunks_by_document(request.document_id)
    if not chunks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No content found in document to generate quiz")

    # Assemble text context (cap at 60k characters for rapid generation)
    context_text = "\n".join([c["chunk_text"] for c in chunks])
    if len(context_text) > 60000:
        context_text = context_text[:60000]

    # Build prompt
    prompt = (
        f"You are a quiz generation engine. Generate exactly {request.num_questions} questions of type '{request.quiz_type}' "
        f"based on the document contents below.\n\n"
        f"Document name: {doc['original_filename']}\n"
        f"Document text:\n"
        f"{context_text}\n\n"
        f"You MUST output raw JSON matching the following schema. Do NOT include markdown code blocks, backticks, or any conversational text around the JSON:\n"
        f"[\n"
        f"  {{\n"
        f"    \"id\": 1,\n"
        f"    \"type\": \"mcq\",  // Or \"true_false\" or \"interview\"\n"
        f"    \"question\": \"The question text\",\n"
        f"    \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],  // Empty array if type is true_false or interview\n"
        f"    \"answer\": \"Correct option letter (e.g. A) or True/False text or expected key answer description\",\n"
        f"    \"explanation\": \"Detailed explanation of why this answer is correct\"\n"
        f"  }}\n"
        f"]"
    )

    messages = [
        {"role": "system", "content": "You are a professional educational assessment developer that strictly outputs clean JSON data."},
        {"role": "user", "content": prompt}
    ]

    try:
        response_json_str = await llm_service.generate_response(messages, temperature=0.5)
        
        # Clean response string to parse as JSON (remove markdown formatting ` ```json ` if model wraps it)
        cleaned_json = response_json_str.strip()
        if cleaned_json.startswith("```"):
            # Remove leading ```json
            cleaned_json = re.sub(r"^```(json)?\s*", "", cleaned_json)
            # Remove trailing ```
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
        
        questions_data = json.loads(cleaned_json)
        
        # Validate elements
        questions = []
        for q in questions_data:
            questions.append(QuizQuestion(
                id=q.get("id", len(questions) + 1),
                type=q.get("type", request.quiz_type),
                question=q.get("question", ""),
                options=q.get("options"),
                answer=q.get("answer", ""),
                explanation=q.get("explanation", "")
            ))
            
        return QuizResponse(
            document_id=request.document_id,
            questions=questions
        )
    except Exception as e:
        logger.error(f"Failed to generate quiz: {e}. Raw response: {response_json_str if 'response_json_str' in locals() else 'None'}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse AI generated quiz: {e}"
        )
