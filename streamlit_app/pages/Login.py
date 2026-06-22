import streamlit as st
from streamlit_app.utils.api_client import login, register, get_me
from streamlit_app.utils.helpers import inject_css
from streamlit_app.utils.constants import APP_NAME, APP_ICON

st.set_page_config(page_title=f"{APP_NAME} · Login", page_icon=APP_ICON, layout="centered")
inject_css()

# ── Centered Login Card ───────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    st.markdown(f"""
    <div class="login-header">
        <div class="login-icon">{APP_ICON}</div>
        <div class="login-title">{APP_NAME}</div>
        <div class="login-subtitle">Your AI-powered document assistant</div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔐 Sign In", "✨ Create Account"])

    # ── Login ─────────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Signing in…"):
                    try:
                        res = login(email, password)
                        st.session_state["access_token"] = res["access_token"]
                        st.session_state["refresh_token"] = res["refresh_token"]
                        st.session_state["logged_in"] = True
                        user = get_me(res["access_token"])
                        st.session_state["user_info"] = user
                        st.success(f"Welcome back, {user.get('name','User')}!")
                        st.switch_page("pages/Chat.py")
                    except Exception as e:
                        err = str(e)
                        if "401" in err or "Incorrect" in err:
                            st.error("Invalid email or password.")
                        elif "connect" in err.lower() or "connection" in err.lower():
                            st.error("Cannot reach the server. Make sure the backend is running.")
                        else:
                            st.error(f"Login failed: {e}")

    # ── Register ──────────────────────────────────────────────────
    with tab_register:
        with st.form("register_form", clear_on_submit=False):
            reg_name = st.text_input("Full Name", placeholder="John Doe")
            reg_email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="reg_pwd")
            reg_submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if reg_submit:
            if not reg_name or not reg_email or not reg_password:
                st.error("Please fill in all fields.")
            elif len(reg_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with st.spinner("Creating your account…"):
                    try:
                        register(reg_name, reg_email, reg_password)
                        st.success("Account created! Please sign in.")
                    except Exception as e:
                        err = str(e)
                        if "already exists" in err or "400" in err:
                            st.error("An account with this email already exists.")
                        else:
                            st.error(f"Registration failed: {e}")
