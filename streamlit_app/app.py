import streamlit as st
from streamlit_app.utils.helpers import inject_css
from streamlit_app.utils.constants import APP_NAME, APP_ICON

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Route to login if not authenticated ───────────────────────────
if not st.session_state.get("logged_in"):
    st.switch_page("pages/Login.py")
else:
    st.switch_page("pages/Chat.py")
