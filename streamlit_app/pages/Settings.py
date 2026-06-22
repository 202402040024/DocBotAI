import streamlit as st
from streamlit_app.utils.api_client import get_settings, update_settings
from streamlit_app.utils.helpers import inject_css
from streamlit_app.utils.constants import APP_NAME, APP_ICON

st.set_page_config(
    page_title=f"{APP_NAME} · Settings",
    page_icon=APP_ICON,
    layout="centered",
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

st.markdown("## ⚙️ Settings")

user = st.session_state.get("user_info", {})

# ── Profile ───────────────────────────────────────────────────────
st.markdown("### 👤 Profile")
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Name", value=user.get("name", ""), disabled=True)
    with c2:
        st.text_input("Email", value=user.get("email", ""), disabled=True)
    st.text_input("Role", value=user.get("role", "user"), disabled=True)

# ── Load current settings ─────────────────────────────────────────
try:
    current = get_settings(token)
except Exception:
    current = {"theme": "dark", "model_preferences": {}}

theme = current.get("theme", "dark")
model_prefs = current.get("model_preferences", {})

# ── Appearance ────────────────────────────────────────────────────
st.markdown("### 🎨 Appearance")
with st.container(border=True):
    new_theme = st.radio(
        "Theme",
        options=["light", "dark"],
        index=0 if theme == "light" else 1,
        horizontal=True,
        help="Theme preference is saved to your profile. Streamlit's actual theme must be set in .streamlit/config.toml"
    )

# ── AI Model ──────────────────────────────────────────────────────
st.markdown("### 🤖 AI Model Preferences")
with st.container(border=True):
    primary_model = st.selectbox(
        "Primary Model",
        options=["gemini-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash", "ollama/llama3"],
        index=0,
    )
    temperature = st.slider(
        "Temperature",
        min_value=0.0, max_value=1.0,
        value=float(model_prefs.get("temperature", 0.7)),
        step=0.1,
        help="Lower = more precise, Higher = more creative"
    )
    st.caption(f"**{temperature:.1f}** — {'Precise' if temperature < 0.4 else 'Balanced' if temperature < 0.7 else 'Creative'}")

# ── Save ──────────────────────────────────────────────────────────
if st.button("💾 Save Settings", type="primary", use_container_width=True):
    prefs = {"primary_model": primary_model, "temperature": temperature}
    try:
        update_settings(token, new_theme, prefs)
        st.success("✅ Settings saved successfully!")
    except Exception as e:
        st.error(f"Failed to save: {e}")

st.divider()

# ── About ─────────────────────────────────────────────────────────
st.markdown("### ℹ️ About")
with st.container(border=True):
    st.markdown(f"""
    **{APP_NAME}** · Multi-Document AI Chatbot  
    Hybrid RAG · FAISS · MongoDB · Gemini AI  
    Built with FastAPI + Streamlit
    """)

st.divider()

# ── Logout ────────────────────────────────────────────────────────
if st.button("🚪 Logout", use_container_width=True, type="secondary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.switch_page("pages/Login.py")
