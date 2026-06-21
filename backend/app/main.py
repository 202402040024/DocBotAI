import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
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


# ── Dynamic CORS middleware ────────────────────────────────────────────────────
# Allows: localhost, any *.vercel.app, and any explicit FRONTEND_URL entries
_EXTRA = [u.strip() for u in os.getenv("FRONTEND_URL", "").split(",") if u.strip()]

_STATIC_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    *_EXTRA,
}

def _is_allowed_origin(origin: str) -> bool:
    if origin in _STATIC_ORIGINS:
        return True
    # Allow ALL vercel.app preview/production deployments
    if re.match(r"^https://[\w-]+(\.vercel\.app)$", origin):
        return True
    return False


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        allowed = _is_allowed_origin(origin)

        # Handle preflight
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            if allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin"
                response.headers["Access-Control-Max-Age"] = "600"
            return response

        response = await call_next(request)

        if allowed and origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization,Content-Type,Accept,Origin"
            response.headers["Vary"] = "Origin"

        return response


app.add_middleware(DynamicCORSMiddleware)

logger.info(f"CORS: static origins={_STATIC_ORIGINS}, vercel.app wildcard=enabled")

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
        "cors": "dynamic — allows all *.vercel.app + localhost"
    }
