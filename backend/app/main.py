import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.auth_deps import get_current_user
from app.repositories.analytics import AnalyticsRepository
from app.api import auth, documents, chat, rag, voice

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB client connection
    await connect_to_mongo()
    yield
    # Shutdown: Close client connection
    await close_mongo_connection()

app = FastAPI(
    title="Multi-Document AI Chatbot & Hybrid RAG System",
    description="Enterprise-Grade AI Chatbot with FAISS, MongoDB, Context-Awareness, Memory, and Voice Features.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Enable CORS — allow localhost for dev + FRONTEND_URL env var for production
_frontend_url = os.getenv("FRONTEND_URL", "")
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(voice.router, prefix="/api")

# Dashboard Analytics Endpoint
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    analytics_repo = AnalyticsRepository()
    stats = await analytics_repo.get_dashboard_stats(current_user["id"])
    return stats
@app.get("/")
async def root():
    return {"message": "Backend Running Successfully"}

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy", "service": "chatbot-backend"}
