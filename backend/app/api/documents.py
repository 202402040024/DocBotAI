import os
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
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

def get_file_dir_and_type(filename: str):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    if ext == "pdf":
        return settings.pdf_dir, "pdf"
    elif ext == "docx":
        return settings.docx_dir, "docx"
    elif ext == "csv":
        return settings.csv_dir, "csv"
    elif ext == "xml":
        return settings.xml_dir, "xml"

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    target_dir, file_type = get_file_dir_and_type(file.filename)
    
    # Save file on disk
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(target_dir, unique_filename)
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save file to disk")
    
    # Process document (extract text and chunk it)
    try:
        chunks = DocumentProcessor.process_document(file_path, file_type)
    except Exception as e:
        # Cleanup file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Failed to process document: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to process document structure: {e}")

    if not chunks:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable text found in document.")

    # Create document record
    doc_record = await document_repository.create_document(
        user_id=current_user["id"],
        filename=unique_filename,
        original_filename=file.filename,
        file_type=file_type
    )
    
    # Save chunks in MongoDB
    doc_id_str = str(doc_record["_id"])
    success_chunks = await document_repository.create_document_chunks(doc_id_str, chunks)
    if not success_chunks:
        # Rollback
        await document_repository.delete_document(doc_id_str, current_user["id"])
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to write document chunks to DB")

    # Fetch newly created chunks from DB to get their DB details for vector store
    db_chunks = await document_repository.get_chunks_by_document(doc_id_str)
    
    # Add embeddings to FAISS
    success_faiss = vector_store_service.add_chunks(current_user["id"], db_chunks)
    if not success_faiss:
        # Rebuild/Rollback clean up DB
        await document_repository.delete_document(doc_id_str, current_user["id"])
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to index vectors in FAISS store")

    # Increment analytics
    await analytics_repository.increment_documents_uploaded(current_user["id"])
    
    return {
        "message": "File uploaded and indexed successfully",
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
    # Serialize ObjectId
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

    # Remove file from disk
    file_type = doc["file_type"]
    filename = doc["filename"]
    
    if file_type == "pdf":
        target_dir = settings.pdf_dir
    elif file_type == "docx":
        target_dir = settings.docx_dir
    elif file_type == "csv":
        target_dir = settings.csv_dir
    elif file_type == "xml":
        target_dir = settings.xml_dir
    else:
        target_dir = settings.UPLOAD_DIR
        
    file_path = os.path.join(target_dir, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete disk file: {e}")

    # Delete from MongoDB (Document and Chunks)
    success = await document_repository.delete_document(id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete document from DB")

    # Rebuild user FAISS index
    all_user_chunks = await document_repository.get_all_user_chunks(current_user["id"])
    vector_store_service.rebuild_index(current_user["id"], all_user_chunks)

    return {"message": "Document deleted successfully"}

@router.put("/{id}")
async def rename_document(id: str, new_name: str, current_user: dict = Depends(get_current_user)):
    # Simple rename endpoint matching PUT /api/documents/{id}?new_name=...
    if not new_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New name cannot be empty")
        
    success = await document_repository.rename_document(id, current_user["id"], new_name.strip())
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or rename failed")
        
    return {"message": "Document renamed successfully"}
