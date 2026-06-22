import json
import logging
from typing import Optional
import requests
from streamlit_app.utils.config import API_BASE_URL

logger = logging.getLogger(__name__)

_session = requests.Session()

def _headers(token: Optional[str] = None) -> dict:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

# ── Auth ──────────────────────────────────────────────────────────

def register(name: str, email: str, password: str) -> dict:
    r = _session.post(
        f"{API_BASE_URL}/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()

def login(email: str, password: str) -> dict:
    r = _session.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()

def refresh_token(refresh: str) -> dict:
    r = _session.post(
        f"{API_BASE_URL}/auth/refresh",
        json={"refresh_token": refresh},
    )
    r.raise_for_status()
    return r.json()

def get_me(token: str) -> dict:
    r = _session.get(f"{API_BASE_URL}/auth/me", headers=_headers(token))
    r.raise_for_status()
    return r.json()

# ── Chat ──────────────────────────────────────────────────────────

def create_session(token: str, title: str) -> dict:
    r = _session.post(
        f"{API_BASE_URL}/chat/new",
        json={"title": title},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

def list_sessions(token: str) -> list:
    r = _session.get(f"{API_BASE_URL}/chat/history", headers=_headers(token))
    r.raise_for_status()
    return r.json()

def get_messages(token: str, session_id: str) -> list:
    r = _session.get(
        f"{API_BASE_URL}/chat/{session_id}/messages",
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

def delete_session(token: str, session_id: str) -> None:
    r = _session.delete(
        f"{API_BASE_URL}/chat/{session_id}",
        headers=_headers(token),
    )
    r.raise_for_status()

def rename_session(token: str, session_id: str, title: str) -> None:
    r = _session.put(
        f"{API_BASE_URL}/chat/{session_id}?title={title}",
        headers=_headers(token),
    )
    r.raise_for_status()

def send_message_stream(token: str, query: str, session_id: Optional[str] = None):
    url = f"{API_BASE_URL}/chat?session_id={session_id}&stream=true"
    r = _session.post(
        url,
        json={"query": query},
        headers=_headers(token),
        stream=True,
    )
    r.raise_for_status()
    return r

def send_message_blocking(token: str, query: str, session_id: Optional[str] = None) -> dict:
    url = f"{API_BASE_URL}/chat?session_id={session_id}"
    r = _session.post(url, json={"query": query}, headers=_headers(token))
    r.raise_for_status()
    return r.json()

# ── Documents ─────────────────────────────────────────────────────

def upload_document(token: str, file_obj, filename: str) -> dict:
    files = {"file": (filename, file_obj)}
    r = _session.post(
        f"{API_BASE_URL}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()

def list_documents(token: str) -> list:
    r = _session.get(f"{API_BASE_URL}/documents", headers=_headers(token))
    r.raise_for_status()
    return r.json()

def get_document(token: str, doc_id: str) -> dict:
    r = _session.get(f"{API_BASE_URL}/documents/{doc_id}", headers=_headers(token))
    r.raise_for_status()
    return r.json()

def delete_document(token: str, doc_id: str) -> dict:
    r = _session.delete(f"{API_BASE_URL}/documents/{doc_id}", headers=_headers(token))
    r.raise_for_status()
    return r.json()

def rename_document(token: str, doc_id: str, new_name: str) -> dict:
    r = _session.put(
        f"{API_BASE_URL}/documents/{doc_id}?new_name={new_name}",
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

# ── RAG ───────────────────────────────────────────────────────────

def rag_query(token: str, query: str) -> dict:
    r = _session.post(
        f"{API_BASE_URL}/rag/query",
        json={"query": query},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

def rag_search(token: str, query: str) -> list:
    r = _session.post(
        f"{API_BASE_URL}/rag/search",
        json={"query": query},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

def summarize_document(token: str, doc_id: str, summary_type: str = "short") -> dict:
    r = _session.post(
        f"{API_BASE_URL}/rag/summarize",
        json={"document_id": doc_id, "summary_type": summary_type},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

def generate_quiz(token: str, doc_id: str, num_questions: int = 5, quiz_type: str = "mcq") -> dict:
    r = _session.post(
        f"{API_BASE_URL}/rag/quiz",
        json={"document_id": doc_id, "num_questions": num_questions, "quiz_type": quiz_type},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

# ── Dashboard ─────────────────────────────────────────────────────

def get_dashboard_stats(token: str) -> dict:
    r = _session.get(f"{API_BASE_URL}/dashboard/stats", headers=_headers(token))
    r.raise_for_status()
    return r.json()

# ── Settings ──────────────────────────────────────────────────────

def get_settings(token: str) -> dict:
    r = _session.get(f"{API_BASE_URL}/auth/settings", headers=_headers(token))
    r.raise_for_status()
    return r.json()

def update_settings(token: str, theme: str, model_preferences: dict) -> dict:
    r = _session.put(
        f"{API_BASE_URL}/auth/settings",
        json={"theme": theme, "model_preferences": model_preferences},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.json()

# ── Voice ─────────────────────────────────────────────────────────

def text_to_speech(token: str, text: str) -> bytes:
    r = _session.post(
        f"{API_BASE_URL}/voice/tts",
        json={"text": text},
        headers=_headers(token),
    )
    r.raise_for_status()
    return r.content
