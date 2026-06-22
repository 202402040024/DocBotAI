import json
import streamlit as st
from streamlit_app.utils.api_client import (
    list_sessions, create_session, get_messages,
    send_message_stream, delete_session, rename_session,
)
from streamlit_app.utils.helpers import inject_css, citation_html, truncate, format_date
from streamlit_app.utils.constants import APP_NAME, APP_ICON, CHAT_SUGGESTIONS

st.set_page_config(
    page_title=f"{APP_NAME} · Chat",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Auth guard ────────────────────────────────────────────────────
token = st.session_state.get("access_token")
if not token:
    st.switch_page("pages/Login.py")

# ── Init session state ────────────────────────────────────────────
for key, default in [
    ("chat_session_id", None),
    ("chat_messages", []),
    ("chat_sessions", []),
    ("pending_citations", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    user = st.session_state.get("user_info", {})
    st.markdown(f"### {APP_ICON} {APP_NAME}")
    st.divider()

    # Navigation
    st.page_link("pages/Chat.py", label="💬 Chat", use_container_width=True)
    st.page_link("pages/Documents.py", label="📁 Documents", use_container_width=True)
    st.page_link("pages/Dashboard.py", label="📊 Dashboard", use_container_width=True)
    st.page_link("pages/Settings.py", label="⚙️ Settings", use_container_width=True)
    st.divider()

    # New chat
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.chat_session_id = None
        st.session_state.chat_messages = []
        st.session_state.pending_citations = []
        st.rerun()

    # Search sessions
    search_q = st.text_input("🔍 Search chats", placeholder="Search…", label_visibility="collapsed")

    # Load sessions
    try:
        sessions = list_sessions(token)
        st.session_state.chat_sessions = sessions
    except Exception:
        sessions = []

    if search_q:
        sessions = [s for s in sessions if search_q.lower() in s.get("title", "").lower()]

    st.caption(f"{len(sessions)} conversation{'s' if len(sessions) != 1 else ''}")

    for s in sessions:
        is_active = st.session_state.chat_session_id == s["id"]
        c1, c2 = st.columns([6, 1])
        with c1:
            label = truncate(s.get("title", "Untitled"), 28)
            if is_active:
                label = f"▶ {label}"
            if st.button(label, key=f"sess_{s['id']}", use_container_width=True,
                         help=format_date(s.get("updated_at", ""))):
                st.session_state.chat_session_id = s["id"]
                try:
                    msgs = get_messages(token, s["id"])
                    st.session_state.chat_messages = [
                        {"role": m["role"], "content": m["content"],
                         "citations": m.get("citations", [])} for m in msgs
                    ]
                except Exception:
                    st.session_state.chat_messages = []
                st.rerun()
        with c2:
            if st.button("🗑", key=f"del_sess_{s['id']}", help="Delete"):
                try:
                    delete_session(token, s["id"])
                    if st.session_state.chat_session_id == s["id"]:
                        st.session_state.chat_session_id = None
                        st.session_state.chat_messages = []
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    if user:
        st.caption(f"👤 {user.get('name', 'User')}")
        st.caption(f"✉️ {user.get('email', '')}")

# ── Main Chat Area ────────────────────────────────────────────────
st.markdown("## 💬 Chat")

# Header with session title
if st.session_state.chat_session_id:
    sessions_map = {s["id"]: s for s in st.session_state.get("chat_sessions", [])}
    current = sessions_map.get(st.session_state.chat_session_id, {})
    st.caption(f"Session: **{current.get('title', 'Untitled')}**")

# Empty state
if not st.session_state.chat_messages:
    st.markdown("""
    <div style='text-align:center;padding:3rem 0 1rem;'>
        <div style='font-size:3rem;'>🤖</div>
        <h3 style='color:#1e293b;margin:0.5rem 0;'>How can I help you today?</h3>
        <p style='color:#64748b;'>Ask questions about your documents or anything else.</p>
    </div>
    """, unsafe_allow_html=True)

    # Suggestion chips
    cols = st.columns(2)
    for i, s in enumerate(CHAT_SUGGESTIONS[:4]):
        with cols[i % 2]:
            if st.button(s, key=f"sugg_{i}", use_container_width=True):
                st.session_state["_pending_input"] = s
                st.rerun()

# Display messages
for msg in st.session_state.chat_messages:
    role = msg["role"]
    content = msg["content"]
    citations = msg.get("citations", [])

    if role == "user":
        st.markdown(f'<div class="user-message">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">', unsafe_allow_html=True)
        st.markdown(content)
        if citations:
            st.markdown(citation_html(citations), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ── Chat Input ────────────────────────────────────────────────────
pending = st.session_state.pop("_pending_input", None)
prompt = st.chat_input("Ask anything…") or pending

if prompt:
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": prompt, "citations": []})
    st.markdown(f'<div class="user-message">{prompt}</div>', unsafe_allow_html=True)

    # Stream assistant response
    with st.spinner(""):
        st.markdown('<div class="assistant-message">', unsafe_allow_html=True)
        response_placeholder = st.empty()
        full_response = ""
        final_citations = []
        sid = st.session_state.chat_session_id

        try:
            resp = send_message_stream(token, prompt, sid)
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    dtype = data.get("type")
                    if dtype == "session":
                        st.session_state.chat_session_id = data["session_id"]
                        sid = data["session_id"]
                    elif dtype == "content":
                        full_response += data.get("text", "")
                        response_placeholder.markdown(full_response + "▌")
                    elif dtype == "citations":
                        final_citations = data.get("citations", [])
                    elif dtype == "error":
                        response_placeholder.error(data.get("message", "Error"))
                        break
                except json.JSONDecodeError:
                    continue

            response_placeholder.markdown(full_response)
            if final_citations:
                st.markdown(citation_html(final_citations), unsafe_allow_html=True)

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": full_response,
                "citations": final_citations,
            })
        except Exception as e:
            response_placeholder.error(f"Error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

    st.rerun()
