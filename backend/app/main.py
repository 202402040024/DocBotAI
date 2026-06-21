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

# Global flag so we only rebuild once
_faiss_rebuilt = False


async def _rebuild_faiss_background():
    global _faiss_rebuilt
    if _faiss_rebuilt:
        return
    await asyncio.sleep(15)  # Let the server fully start first
    try:
        from app.repositories.document import DocumentRepository
        from app.services.vector_store import vector_store_service
        from app.database.mongodb import get_database

        db = get_database()
        if db is None:
            return

        user_ids = await db["uploaded_documents"].distinct("user_id")
        if not user_ids:
            logger.info("FAISS rebuild: no documents found, skipping")
            _faiss_rebuilt = True
            return

        doc_repo = DocumentRepository()
        for uid in user_ids:
            try:
                chunks = await doc_repo.get_all_user_chunks(str(uid))
                if chunks:
                    vector_store_service.rebuild_index(str(uid), chunks)
                    logger.info(f"FAISS rebuilt for {uid}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"FAISS rebuild failed for {uid}: {e}")

        _faiss_rebuilt = True
        logger.info("Background FAISS rebuild complete")
    except Exception as e:
        logger.error(f"Background FAISS rebuild error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only connect to MongoDB — fast, no model loading
    try:
        await connect_to_mongo()
        logger.info("MongoDB connected — server ready")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        # Don't crash — let health endpoint still work

    # Schedule FAISS rebuild AFTER yield (non-blocking)
    task = asyncio.ensure_future(_rebuild_faiss_background())

    yield  # Server starts accepting requests immediately

    task.cancel()
    await close_mongo_connection()


app = FastAPI(
    title="Multi-Document AI Chatbot",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)


# ── Dynamic CORS ──────────────────────────────────────────────────────────────
_EXTRA = [u.strip() for u in os.getenv("FRONTEND_URL", "").split(",") if u.strip()]
_STATIC_ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000", *_EXTRA}


def _is_allowed_origin(origin: str) -> bool:
    if not origin:
        return False
    if origin in _STATIC_ORIGINS:
        return True
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


# ── Health — must respond instantly ──────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "docbot-backend", "version": "1.0.0"}
