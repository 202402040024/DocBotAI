import os
import uuid
import logging
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from app.api.auth_deps import get_current_user
from app.repositories.document import DocumentRepository
from app.repositories.analytics import AnalyticsRepository
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import vector_store_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

document_repository = DocumentRepository()
analytics_repository = AnalyticsRepository()

ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "xml"}
# Limit file size to 10MB on free tier to avoid OOM
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def get_file_dir_and_type(filename: str):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS).upper()}"
        )
    dirs = {
        "pdf": settings.pdf_dir,
        "docx": settings.docx_dir,
        "csv": settings.csv_dir,
        "xml": settings.xml_dir,
    }
    return dirs[ext], ext


def _index_in_background(user_id: str, doc_id_str: str, db_chunks: list):
    """Run FAISS indexing synchronously in a thread pool thread."""
    try:
        vector_store_service.add_chunks(user_id, db_chunks)
        logger.info(f"Background FAISS indexing complete for doc {doc_id_str}: {len(db_chunks)} chunks")
    except Exception as e:
        logger.error(f"Background FAISS indexing failed for doc {doc_id_str}: {e}")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    target_dir, file_type = get_file_dir_and_type(file.filename)

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {e}")

    # Enforce size limit on free tier
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 10MB. Your file: {len(content) // 1024}KB"
        )

    # Save to disk
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(target_dir, unique_filename)
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save file to disk")

    # Extract and chunk text
    try:
        chunks = DocumentProcessor.process_document(file_path, file_type)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to process document: {e}")

    if not chunks:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable text found in document.")

    # Limit chunks to avoid OOM on free tier (first 200 chunks = ~100k chars)
    if len(chunks) > 200:
        logger.warning(f"Document has {len(chunks)} chunks — limiting to 200 for free tier")
        chunks = chunks[:200]

    # Save document record
    doc_record = await document_repository.create_document(
        user_id=current_user["id"],
        filename=unique_filename,
        original_filename=file.filename,
        file_type=file_type
    )
    doc_id_str = str(doc_record["_id"])

    # Save chunks to MongoDB
    success_chunks = await document_repository.create_document_chunks(doc_id_str, chunks)
    if not success_chunks:
        await document_repository.delete_document(doc_id_str, current_user["id"])
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save document chunks")

    # Get DB chunks with IDs
    db_chunks = await document_repository.get_chunks_by_document(doc_id_str)

    # ✅ Run FAISS indexing in background so upload returns immediately
    # This prevents timeout on Render free tier when embedding model is slow
    background_tasks.add_task(
        asyncio.get_event_loop().run_in_executor,
        None,
        _index_in_background,
        current_user["id"],
        doc_id_str,
        db_chunks
    )

    # Increment analytics
    await analytics_repository.increment_documents_uploaded(current_user["id"])

    return {
        "message": "File uploaded successfully. Indexing in background — ready in a few seconds.",
        "document": {
            "id": doc_id_str,
            "original_filename": file.filename,
            "file_type": file_type,
            "chunk_count": len(db_chunks)
        }
    }


@router.get("")
async def list_documents(current_user: dict = Depends(get_current_user)):
    docs = await document_repository.list_documents(current_user["id"])
    for doc in docs:
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        doc["user_id"] = str(doc["user_id"])
        if "upload_time" in doc:
            doc["upload_time"] = doc["upload_time"].isoformat()
    return docs


@router.get("/{id}")
async def get_document(id: str, current_user: dict = Depends(get_current_user)):
    doc = await document_repository.get_document(id, current_user["id"])
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    doc["id"] = str(doc["_id"])
    doc["_id"] = str(doc["_id"])
    doc["user_id"] = str(doc["user_id"])
    if "upload_time" in doc:
        doc["upload_time"] = doc["upload_time"].isoformat()
    return doc


@router.delete("/{id}")
async def delete_document(id: str, current_user: dict = Depends(get_current_user)):
    doc = await document_repository.get_document(id, current_user["id"])
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    dirs = {"pdf": settings.pdf_dir, "docx": settings.docx_dir, "csv": settings.csv_dir, "xml": settings.xml_dir}
    target_dir = dirs.get(doc["file_type"], settings.UPLOAD_DIR)
    file_path = os.path.join(target_dir, doc["filename"])
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete file from disk: {e}")

    success = await document_repository.delete_document(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete document")

    # Rebuild FAISS in background
    all_user_chunks = await document_repository.get_all_user_chunks(current_user["id"])
    vector_store_service.rebuild_index(current_user["id"], all_user_chunks)

    return {"message": "Document deleted successfully"}


@router.put("/{id}")
async def rename_document(id: str, new_name: str, current_user: dict = Depends(get_current_user)):
    if not new_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New name cannot be empty")
    success = await document_repository.rename_document(id, current_user["id"], new_name.strip())
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or rename failed")
    return {"message": "Document renamed successfully"}
