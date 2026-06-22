import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from streamlit_app.utils.api_client import get_dashboard_stats
from streamlit_app.utils.helpers import inject_css, file_icon, format_date
from streamlit_app.utils.constants import APP_NAME, APP_ICON

st.set_page_config(
    page_title=f"{APP_NAME} · Dashboard",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

token = st.session_state.get("access_token")
if not token:
    st.switch_page("pages/Login.py")

with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_NAME}")
    st.divider()
    st.page_link("pages/Chat.py", label="💬 Chat", use_container_width=True)
    st.page_link("pages/Documents.py", label="📁 Documents", use_container_width=True)
    st.page_link("pages/Dashboard.py", label="📊 Dashboard", use_container_width=True)
    st.page_link("pages/Settings.py", label="⚙️ Settings", use_container_width=True)

user = st.session_state.get("user_info", {})
st.markdown(f"## 📊 Dashboard")
st.caption(f"Welcome back, **{user.get('name', 'User')}**")

# Load stats
with st.spinner("Loading analytics…"):
    try:
        stats = get_dashboard_stats(token)
    except Exception as e:
        st.error(f"Failed to load stats: {e}")
        st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────
st.markdown("### Overview")
k1, k2, k3, k4, k5 = st.columns(5)
kpis = [
    (k1, "📄", "Documents", stats.get("total_documents", 0), "#2563eb"),
    (k2, "💬", "Chat Sessions", stats.get("total_chats", 0), "#7c3aed"),
    (k3, "❓", "Questions Asked", stats.get("total_questions", 0), "#059669"),
    (k4, "🔍", "RAG Retrievals", stats.get("retrieval_count", 0), "#d97706"),
    (k5, "🔎", "Searches", stats.get("searches_performed", 0), "#dc2626"),
]
for col, icon, label, value, color in kpis:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div style='font-size:1.6rem'>{icon}</div>
            <div class="stat-number" style='color:{color}'>{value:,}</div>
            <div class="stat-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Activity Overview")
    labels = ["Questions", "Retrievals", "Searches"]
    values = [
        stats.get("total_questions", 0),
        stats.get("retrieval_count", 0),
        stats.get("searches_performed", 0),
    ]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=["#2563eb", "#7c3aed", "#059669"],
        text=values, textposition="auto",
    ))
    fig.update_layout(
        showlegend=False, height=260, margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12), yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)"),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown("#### Usage Distribution")
    pie_labels = ["Questions", "Retrievals", "Searches"]
    pie_values = [
        stats.get("total_questions", 1),
        stats.get("retrieval_count", 1),
        stats.get("searches_performed", 1),
    ]
    fig2 = go.Figure(go.Pie(
        labels=pie_labels, values=pie_values,
        hole=0.45,
        marker_colors=["#2563eb", "#7c3aed", "#059669"],
    ))
    fig2.update_layout(
        showlegend=True, height=260, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(size=12),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Recent Activity ───────────────────────────────────────────────
col_docs, col_chats = st.columns(2)

with col_docs:
    st.markdown("#### 📄 Recent Uploads")
    recent_uploads = stats.get("recent_uploads", [])
    if not recent_uploads:
        st.info("No documents uploaded yet.")
    else:
        df_docs = pd.DataFrame([{
            "File": d.get("original_filename", "Unknown"),
            "Type": d.get("file_type", "?").upper(),
            "Uploaded": format_date(d.get("upload_time", "")),
        } for d in recent_uploads])
        st.dataframe(df_docs, use_container_width=True, hide_index=True,
                     column_config={"File": st.column_config.TextColumn(width="medium")})

with col_chats:
    st.markdown("#### 💬 Recent Conversations")
    recent_convs = stats.get("recent_conversations", [])
    if not recent_convs:
        st.info("No conversations yet.")
    else:
        df_chats = pd.DataFrame([{
            "Title": c.get("title", "Untitled"),
            "Updated": format_date(c.get("updated_at", "")),
        } for c in recent_convs])
        st.dataframe(df_chats, use_container_width=True, hide_index=True,
                     column_config={"Title": st.column_config.TextColumn(width="large")})
