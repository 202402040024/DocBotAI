"""Utility helpers for the Streamlit app."""
import re
from datetime import datetime, timezone
from pathlib import Path


def load_css() -> str:
    """Load and return the custom CSS string."""
    css_path = Path(__file__).parent.parent / "styles" / "custom.css"
    if css_path.exists():
        return f"<style>{css_path.read_text()}</style>"
    return ""


def inject_css() -> None:
    import streamlit as st
    st.markdown(load_css(), unsafe_allow_html=True)


def format_date(iso_string: str) -> str:
    """Format ISO date string to human-readable relative time."""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "Just now"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        if secs < 604800:
            return f"{secs // 86400}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return iso_string


def file_icon(file_type: str) -> str:
    icons = {"pdf": "📄", "docx": "📝", "csv": "📊", "xml": "📋"}
    return icons.get(file_type.lower(), "📁")


def badge_html(file_type: str) -> str:
    cls = {"pdf": "badge-pdf", "docx": "badge-docx", "csv": "badge-csv", "xml": "badge-xml"}
    c = cls.get(file_type.lower(), "badge-pdf")
    return f'<span class="doc-type-badge {c}">{file_type.upper()}</span>'


def citation_html(citations: list) -> str:
    if not citations:
        return ""
    html = "<div style='margin-top:0.5rem'><small><strong>📚 Sources:</strong></small>"
    for c in citations:
        score_pct = int(c.get("similarity_score", 0) * 100)
        html += f"""
        <div class="citation-card">
            <strong>{c.get('document_name','Unknown')}</strong>
            <span class="citation-score">{score_pct}%</span><br>
            <span>Page {c.get('page_number',1)} · Para {c.get('paragraph_number',1)}</span>
        </div>"""
    html += "</div>"
    return html


def truncate(text: str, max_len: int = 40) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"
