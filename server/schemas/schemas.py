from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field

# --- AUTH SCHEMAS ---

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- SETTINGS SCHEMAS ---

class UserSettingsUpdate(BaseModel):
    theme: str
    model_preferences: Dict[str, Any]

# --- CHAT SCHEMAS ---

class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1)

class ChatSessionOut(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str

class Citation(BaseModel):
    document_name: str
    page_number: int
    paragraph_number: int
    similarity_score: float

class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: List[Citation] = []
    timestamp: str

class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)

# --- RAG SCHEMAS ---

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: Optional[str] = None

class RAGSearchResponseItem(BaseModel):
    chunk_id: str
    chunk_text: str
    document_name: str
    page_number: int
    paragraph_number: int
    similarity_score: float

class RAGSummarizeRequest(BaseModel):
    document_id: str
    summary_type: str = "short" # short, detailed, key_insights

class QuizQuestion(BaseModel):
    id: int
    type: str # mcq, true_false, interview
    question: str
    options: Optional[List[str]] = None
    answer: str
    explanation: Optional[str] = None

class QuizRequest(BaseModel):
    document_id: str
    num_questions: int = 5
    quiz_type: str = "mcq" # mcq, true_false, interview, mixed

class QuizResponse(BaseModel):
    document_id: str
    questions: List[QuizQuestion]

# --- VOICE SCHEMAS ---

class VoiceSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
