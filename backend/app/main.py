import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
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


async def _rebuild_faiss_background():
    """
    Rebuild FAISS indexes from MongoDB in the background.
    Runs AFTER the server is already accepting requests so Render
    doesn't time out waiting for the port to open.
    """
    # Wait a few seconds to let the server fully start
    await asyncio.sleep(10)
    try:
        from app.repositories.document import DocumentRepository
        from app.services.vector_store import vector_store_service
        from app.database.mongodb import get_database

        db = get_database()
        if db is None:
            return

        user_ids = await db["uploaded_documents"].distinct("user_id")
        if not user_ids:
            logger.info("Startup: no documents found, skipping FAISS rebuild")
            return

        doc_repo = DocumentRepository()
        rebuilt = 0
        for uid in user_ids:
            try:
                uid_str = str(uid)
                chunks = await doc_repo.get_all_user_chunks(uid_str)
                if chunks:
                    vector_store_service.rebuild_index(uid_str, chunks)
                    rebuilt += 1
            except Exception as e:
                logger.error(f"FAISS rebuild failed for {uid}: {e}")

        logger.info(f"Background FAISS rebuild done: {rebuilt}/{len(user_ids)} users")
    except Exception as e:
        logger.error(f"Background FAISS rebuild error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB — fast, no model loading
    await connect_to_mongo()
    logger.info("MongoDB connected. Server starting on port...")

    # Schedule FAISS rebuild as background task — does NOT block port binding
    asyncio.create_task(_rebuild_faiss_background())

    yield  # ← Server is accepting requests from this point

    await close_mongo_connection()


app = FastAPI(
    title="Multi-Document AI Chatbot & Hybrid RAG System",
    description="Enterprise-Grade AI Chatbot with FAISS, MongoDB, RAG, Memory, and Voice.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# ── Dynamic CORS ───────────────────────────────────────────────────────────────
_EXTRA = [u.strip() for u in os.getenv("FRONTEND_URL", "").split(",") if u.strip()]
_STATIC_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    *_EXTRA,
}


def _is_allowed_origin(origin: str) -> bool:
    if origin in _STATIC_ORIGINS:
        return True
    # Allow all Vercel preview + production URLs automatically
    if re.match(r"^https://[\w-]+(\.vercel\.app)$", origin):
        return True
    return False


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        allowed = _is_allowed_origin(origin)

        if request.method == "OPTIONS":
            res = Response(status_code=204)
            if allowed:
                res.headers["Access-Control-Allow-Origin"] = origin
                res.headers["Access-Control-Allow-Credentials"] = "true"
                res.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
                res.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin"
                res.headers["Access-Control-Max-Age"] = "600"
            return res

        response = await call_next(request)
        if allowed and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin"
            response.headers["Vary"] = "Origin"
        return response


app.add_middleware(DynamicCORSMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(voice.router, prefix="/api")


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    return await AnalyticsRepository().get_dashboard_stats(current_user["id"])


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "docbot-backend",
        "version": "1.0.0",
    }
