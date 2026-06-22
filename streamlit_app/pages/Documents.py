import streamlit as st
from streamlit_app.utils.api_client import (
    list_documents, upload_document, delete_document,
    rename_document, summarize_document, generate_quiz, rag_search,
)
from streamlit_app.utils.helpers import inject_css, file_icon, badge_html, format_date
from streamlit_app.utils.constants import APP_NAME, APP_ICON, ALLOWED_FILE_TYPES, SUMMARY_TYPES, QUIZ_TYPES

st.set_page_config(
    page_title=f"{APP_NAME} · Documents",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

token = st.session_state.get("access_token")
if not token:
    st.switch_page("pages/Login.py")

# ── Sidebar Nav ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_NAME}")
    st.divider()
    st.page_link("pages/Chat.py", label="💬 Chat", use_container_width=True)
    st.page_link("pages/Documents.py", label="📁 Documents", use_container_width=True)
    st.page_link("pages/Dashboard.py", label="📊 Dashboard", use_container_width=True)
    st.page_link("pages/Settings.py", label="⚙️ Settings", use_container_width=True)

# ── Header ────────────────────────────────────────────────────────
st.markdown("## 📁 Document Manager")

# ── Upload Section ────────────────────────────────────────────────
with st.expander("📤 Upload Documents", expanded=False):
    uploaded_files = st.file_uploader(
        "Drop files here or click to browse",
        type=ALLOWED_FILE_TYPES,
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, CSV, XML (max 10MB each)"
    )
    if uploaded_files:
        if st.button("Upload All", type="primary", use_container_width=True):
            for f in uploaded_files:
                with st.spinner(f"Uploading {f.name}…"):
                    try:
                        res = upload_document(token, f, f.name)
                        st.success(f"✅ {f.name} — {res['document']['chunk_count']} chunks indexed")
                    except Exception as e:
                        err = str(e)
                        if "413" in err:
                            st.error(f"❌ {f.name} — File too large (max 10MB)")
                        else:
                            st.error(f"❌ {f.name} — {e}")
            st.rerun()

# ── Semantic Search ───────────────────────────────────────────────
with st.expander("🔍 Semantic Search", expanded=False):
    search_q = st.text_input("Search document content by meaning", placeholder="What does the document say about…")
    if st.button("Search", key="semantic_search", use_container_width=True):
        if search_q.strip():
            with st.spinner("Searching…"):
                try:
                    results = rag_search(token, search_q)
                    if not results:
                        st.info("No relevant chunks found.")
                    for r in results:
                        score = int(r.get("similarity_score", 0) * 100)
                        with st.container(border=True):
                            c1, c2 = st.columns([5, 1])
                            with c1:
                                st.markdown(f"**{r.get('document_name', 'Unknown')}** · Page {r.get('page_number', 1)}")
                                st.caption(r.get("chunk_text", "")[:300])
                            with c2:
                                st.metric("Match", f"{score}%")
                except Exception as e:
                    st.error(f"Search failed: {e}")

# ── Document List ─────────────────────────────────────────────────
st.markdown("### Your Documents")

try:
    docs = list_documents(token)
except Exception as e:
    st.error(f"Failed to load documents: {e}")
    docs = []

# Filter
filter_type = st.selectbox("Filter by type", ["All", "PDF", "DOCX", "CSV", "XML"], label_visibility="collapsed")
if filter_type != "All":
    docs = [d for d in docs if d.get("file_type", "").lower() == filter_type.lower()]

if not docs:
    st.info("No documents uploaded yet. Upload your first document above.")
else:
    st.caption(f"{len(docs)} document{'s' if len(docs) != 1 else ''}")

    for doc in docs:
        doc_id = doc.get("id", "")
        fname = doc.get("original_filename", "Unknown")
        ftype = doc.get("file_type", "?")
        chunks = doc.get("chunk_count", 0)
        upload_time = format_date(doc.get("upload_time", ""))
        icon = file_icon(ftype)

        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 1, 1])

            with col1:
                st.markdown(
                    f"{icon} **{fname}** &nbsp; {badge_html(ftype)} &nbsp; "
                    f"<small style='color:#64748b'>{chunks} chunks · {upload_time}</small>",
                    unsafe_allow_html=True
                )

            with col2:
                if st.button("📝 Summary", key=f"sum_{doc_id}", use_container_width=True):
                    st.session_state[f"show_sum_{doc_id}"] = not st.session_state.get(f"show_sum_{doc_id}", False)
                    st.rerun()

            with col3:
                if st.button("🧠 Quiz", key=f"quiz_{doc_id}", use_container_width=True):
                    st.session_state[f"show_quiz_{doc_id}"] = not st.session_state.get(f"show_quiz_{doc_id}", False)
                    st.rerun()

            with col4:
                new_name = st.text_input("Rename", label_visibility="collapsed", key=f"rename_{doc_id}",
                                         placeholder="New name…")
                if new_name and st.button("✔", key=f"save_rename_{doc_id}"):
                    try:
                        rename_document(token, doc_id, new_name)
                        st.success("Renamed")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            with col5:
                if st.button("🗑 Delete", key=f"del_{doc_id}", use_container_width=True):
                    try:
                        delete_document(token, doc_id)
                        st.success(f"Deleted {fname}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

            # ── Summary Panel ──────────────────────────────────────
            if st.session_state.get(f"show_sum_{doc_id}"):
                sum_type_label = st.selectbox(
                    "Summary type", list(SUMMARY_TYPES.keys()),
                    key=f"sumtype_{doc_id}", label_visibility="collapsed"
                )
                if st.button("Generate Summary", key=f"gen_sum_{doc_id}", use_container_width=True):
                    with st.spinner("Generating summary…"):
                        try:
                            res = summarize_document(token, doc_id, SUMMARY_TYPES[sum_type_label])
                            st.markdown(f"> {res['summary']}")
                        except Exception as e:
                            st.error(str(e))

            # ── Quiz Panel ─────────────────────────────────────────
            if st.session_state.get(f"show_quiz_{doc_id}"):
                qcol1, qcol2 = st.columns(2)
                with qcol1:
                    quiz_type_label = st.selectbox("Quiz type", list(QUIZ_TYPES.keys()),
                                                    key=f"qtype_{doc_id}", label_visibility="collapsed")
                with qcol2:
                    num_q = st.selectbox("# Questions", [3, 5, 10], key=f"qnum_{doc_id}",
                                         label_visibility="collapsed")

                if st.button("Generate Quiz", key=f"gen_quiz_{doc_id}", use_container_width=True):
                    with st.spinner("Generating quiz…"):
                        try:
                            res = generate_quiz(token, doc_id, int(num_q), QUIZ_TYPES[quiz_type_label])
                            for q in res.get("questions", []):
                                with st.expander(f"Q{q['id']}. {q['question']}", expanded=False):
                                    if q.get("options"):
                                        for i, opt in enumerate(q["options"]):
                                            st.write(f"{'ABCD'[i]}. {opt}")
                                    st.success(f"✅ Answer: {q['answer']}")
                                    if q.get("explanation"):
                                        st.caption(q["explanation"])
                        except Exception as e:
                            st.error(str(e))
