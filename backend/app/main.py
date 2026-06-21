import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.auth_deps import get_current_user
from app.repositories.analytics import AnalyticsRepository
from app.api import auth, documents, chat, rag, voice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Multi-Document AI Chatbot & Hybrid RAG System",
    description="Enterprise-Grade AI Chatbot with FAISS, MongoDB, Context-Awareness, Memory, and Voice Features.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# FRONTEND_URL env var = your Vercel URL (comma-separated for multiple)
# If not set, allow all origins so deployment works out of the box
_raw = os.getenv("FRONTEND_URL", "")
_allow_all = not bool(_raw)  # allow * when no FRONTEND_URL is configured

_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
for url in _raw.split(","):
    url = url.strip()
    if url and url not in _allowed_origins:
        _allowed_origins.append(url)

logger.info(f"CORS allow_all_origins={_allow_all}, explicit_origins={_allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _allowed_origins,
    allow_credentials=False if _allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(voice.router, prefix="/api")


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    analytics_repo = AnalyticsRepository()
    return await analytics_repo.get_dashboard_stats(current_user["id"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "docbot-backend",
        "version": "1.0.0",
        "cors_mode": "allow_all" if _allow_all else "restricted",
        "allowed_origins": ["*"] if _allow_all else _allowed_origins
    }
