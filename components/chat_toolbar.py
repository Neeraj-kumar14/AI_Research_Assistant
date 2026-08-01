import hashlib
import html
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

logger = logging.getLogger(__name__)

from utils.pdf_loader import load_pdf
from utils.docx_loader import load_docx
from utils.chunker import create_chunks
from utils.embedding import create_embeddings
from utils.vector_store import create_vector_store
from utils.language_detector import detect_language
from utils.llm import summarize_pdf
from utils.pdf_export import export_notes_to_pdf
from utils.errors import show_llm_error

# -----------------------------------------------------------------------
# Disk cache for processed documents — unchanged from the old sidebar.
# OCR + embedding on a large (20-50MB, partly scanned) file can take a
# couple of minutes, so if the exact same set of files gets reprocessed
# (re-attaching, a dev reload, a second person using the same PDF) this
# skips straight to a ready vector store.
# -----------------------------------------------------------------------
CACHE_DIR = ".study_cache"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", str(7 * 24 * 60 * 60)))  # 7 days
MAX_CACHE_BYTES = int(os.getenv("MAX_CACHE_BYTES", str(500 * 1024 * 1024)))  # 500 MB


def _cleanup_cache():
    if not os.path.isdir(CACHE_DIR):
        return

    now = time.time()
    entries = []

    for name in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, name)
        try:
            stat = os.stat(path)
        except OSError:
            continue

        if (now - stat.st_mtime) > CACHE_TTL_SECONDS:
            try:
                os.remove(path)
            except OSError:
                pass
            continue

        entries.append((path, stat.st_mtime, stat.st_size))

    total_size = sum(size for _, _, size in entries)
    if total_size > MAX_CACHE_BYTES:
        entries.sort(key=lambda e: e[1])  # oldest first
        for path, _, size in entries:
            if total_size <= MAX_CACHE_BYTES:
                break
            try:
                os.remove(path)
                total_size -= size
            except OSError:
                pass


def _cache_key(uploaded_files):
    h = hashlib.md5()
    for f in uploaded_files:
        h.update(f.name.encode())
        h.update(f.getvalue())
    return h.hexdigest()


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.pkl")


def _load_from_cache(key):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        os.utime(path, None)
        return data
    except Exception:
        return None


def _save_to_cache(key, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    _cleanup_cache()
    try:
        with open(_cache_path(key), "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass


def _start_takeover(stage_key, value):
    """Quiz / flashcards / notes are full-screen "takeover" modes, each
    driven by its own <name>_stage session-state flag. Starting one
    always clears the other two first, so at most one takeover screen
    is ever mounted at a time."""
    for key in ("quiz_stage", "flashcard_stage", "notes_stage"):
        if key != stage_key:
            st.session_state[key] = None
    st.session_state[stage_key] = value


# -----------------------------------------------------------------------
# Ingestion — same pipeline the old sidebar ran, now triggered by files
# arriving through the chat composer's "+" attach button instead of a
# standing sidebar file_uploader. Documents accumulate across turns in
# st.session_state.doc_files, so re-attaching adds to the knowledge base
# rather than replacing it.
# -----------------------------------------------------------------------
def _ingest_documents(uploaded_files, status_area):
    progress_label = status_area.empty()
    progress_bar = status_area.progress(0)

    cache_key = _cache_key(uploaded_files)
    cached = _load_from_cache(cache_key)

    if cached is not None:
        progress_label.markdown("Loading cached document…")
        all_pages = cached["pages"]
        chunks = cached["chunks"]
        embeddings = cached["embeddings"]
        detected_language = cached["language"]
        progress_bar.progress(90)
    else:
        def _load_one(uploaded_file):
            if uploaded_file.name.lower().endswith(".pdf"):
                return load_pdf(uploaded_file)
            elif uploaded_file.name.lower().endswith(".docx"):
                return load_docx(uploaded_file)
            return []

        progress_label.markdown("Reading documents (OCR runs automatically on scanned pages)…")
        start = time.perf_counter()
        all_pages = []
        if len(uploaded_files) > 1:
            with ThreadPoolExecutor(max_workers=min(4, len(uploaded_files))) as pool:
                for pages in pool.map(_load_one, uploaded_files):
                    all_pages.extend(pages)
        else:
            all_pages.extend(_load_one(uploaded_files[0]))
        progress_bar.progress(15)
        logger.debug("PDF loading time: %.2f sec", time.perf_counter() - start)

        pdf_text_for_lang = "\n\n".join(page["text"] for page in all_pages)

        progress_label.markdown("Detecting language…")
        detected_language = detect_language(pdf_text_for_lang)
        progress_bar.progress(20)

        progress_label.markdown("Splitting into chunks…")
        chunks = create_chunks(all_pages)
        chunk_texts = [chunk["text"] for chunk in chunks]
        progress_bar.progress(35)

        def _on_embed_progress(done, total):
            pct = 35 + int((done / total) * 50) if total else 85
            progress_bar.progress(min(pct, 85))
            progress_label.markdown(f"Embedding chunks… {done}/{total}")

        start = time.perf_counter()
        embeddings = create_embeddings(chunk_texts, progress_callback=_on_embed_progress)
        logger.debug("Embedding time: %.2f sec", time.perf_counter() - start)
        progress_bar.progress(90)

        _save_to_cache(
            cache_key,
            {"pages": all_pages, "chunks": chunks, "embeddings": embeddings, "language": detected_language},
        )

    pdf_text = "\n\n".join(page["text"] for page in all_pages)
    progress_label.markdown("Building search index…")
    vector_store = create_vector_store(embeddings)
    progress_bar.progress(100)

    st.session_state.document_language = detected_language
    st.session_state.pdf_text = pdf_text
    st.session_state.pages = all_pages
    st.session_state.vector_store = vector_store
    st.session_state.chunks = chunks
    st.session_state.pdf_loaded = True
    st.session_state.current_pdf_list = [f.name for f in uploaded_files]

    progress_label.empty()
    progress_bar.empty()


def sync_documents():
    """Call once near the top of app.py. If st.session_state.doc_files
    (the accumulated set of everything the user has attached so far)
    doesn't match what's currently indexed, re-run ingestion over the
    full accumulated set."""
    doc_files = st.session_state.get("doc_files", [])
    if not doc_files:
        return

    current_names = [f.name for f in doc_files]
    if st.session_state.get("current_pdf_list") == current_names:
        return

    status_area = st.empty()
    with status_area.container():
        try:
            _ingest_documents(doc_files, status_area)
        except Exception as e:
            show_llm_error(e, action="process your document")
            st.session_state.doc_files = [
                f for f in doc_files if f.name != current_names[-1]
            ] if current_names else []
            return
    st.toast(f"{len(doc_files)} document{'s' if len(doc_files) != 1 else ''} ready", icon="📄")


def add_files(new_files):
    """Merge newly attached files into the accumulated document set,
    skipping exact duplicates (same name + same bytes)."""
    if not new_files:
        return
    existing = st.session_state.setdefault("doc_files", [])
    seen = {(f.name, len(f.getvalue())) for f in existing}
    for f in new_files:
        sig = (f.name, len(f.getvalue()))
        if sig not in seen:
            existing.append(f)
            seen.add(sig)


def remove_file(name):
    """Drop a single document from the accumulated set (used by the ✕
    on each chip) and reset any state pointing at the old full set so
    sync_documents() reprocesses the remainder."""
    existing = st.session_state.get("doc_files", [])
    st.session_state.doc_files = [f for f in existing if f.name != name]
    if not st.session_state.doc_files:
        clear_all_documents()
    else:
        st.session_state.current_pdf_list = None  # force reprocessing


def clear_all_documents():
    st.session_state.doc_files = []
    st.session_state.pdf_loaded = False
    st.session_state.document_language = None
    for key in ["pdf_text", "chunks", "vector_store", "current_pdf_list", "pages"]:
        st.session_state.pop(key, None)


def clear_conversation():
    st.session_state.messages = []
    st.session_state.review_mode = False
    st.session_state.quiz = None
    st.session_state.quiz_stage = None
    st.session_state.quiz_answers = {}
    st.session_state.quiz_score = 0
    st.session_state.quiz_submitted = False
    st.session_state.current_question = 0
    st.session_state.quiz_question_start_time = None
    st.session_state.study_notes = None
    st.session_state.notes_stage = None
    st.session_state.notes_focus = ""
    clear_all_documents()


# -----------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------
def render_document_chips():
    """The 'everything I've added' row — always visible just above the
    composer once at least one document is loaded, each with a ✕ to
    remove it. This is the direct replacement for having to open the
    sidebar to see what was uploaded."""
    doc_files = st.session_state.get("doc_files", [])
    if not doc_files:
        return

    chips_html = "".join(
        f'<span class="doc-chip"><span class="dot"></span>{html.escape(f.name)}</span>'
        for f in doc_files
    )
    st.markdown(f'<div class="doc-chip-row">{chips_html}</div>', unsafe_allow_html=True)

    if st.session_state.get("pdf_loaded"):
        pages = len(st.session_state.get("pages", []))
        chunks = len(st.session_state.get("chunks", []))
        lang = st.session_state.get("document_language", "—")
        st.markdown(
            f'<div class="composer-stats">{len(doc_files)} file(s) · {pages} pages · '
            f'{chunks} chunks · lang: {lang}</div>',
            unsafe_allow_html=True,
        )

    with st.popover("Manage documents", use_container_width=False):
        for f in doc_files:
            c1, c2 = st.columns([0.85, 0.15])
            c1.markdown(f"📄 {f.name}")
            if c2.button("✕", key=f"rm_{f.name}", help=f"Remove {f.name}"):
                remove_file(f.name)
                st.rerun()
        st.divider()
        if st.button("🗑 Remove all documents", use_container_width=True, key="clear_docs_btn"):
            clear_all_documents()
            st.rerun()


def render_toolbar_actions():
    """Quick-access study tool pills, shown once a document is loaded —
    the sidebar's old 'Study tools' section, now a persistent row above
    the transcript instead of tucked away."""
    if not st.session_state.get("pdf_loaded"):
        return

    buttons = [
        ("📑 Summarize", "tb_summarize"),
        ("📝 Study notes", "tb_notes"),
        ("🧠 Flashcards", "tb_flashcards"),
        ("❓ Quiz", "tb_quiz"),
    ]
    has_notes = bool(st.session_state.get("study_notes"))
    n = len(buttons) + (2 if has_notes else 0) + 1  # + downloads + clear
    toolbar = st.container(key="toolbar_row")
    cols = toolbar.columns(n, gap="small")

    with cols[0]:
        if st.button(buttons[0][0], key=buttons[0][1], use_container_width=True):
            with st.spinner("Generating summary..."):
                try:
                    summary = summarize_pdf(
                        st.session_state.pdf_text,
                        language=st.session_state.document_language,
                    )
                except Exception as e:
                    show_llm_error(e, action="generate the summary")
                    st.stop()
            st.session_state.messages.append({"role": "user", "content": "📑 Summarize this document"})
            st.session_state.messages.append({"role": "assistant", "content": summary})
            st.rerun()

    with cols[1]:
        if st.button(buttons[1][0], key=buttons[1][1], use_container_width=True):
            _start_takeover("notes_stage", "setup")
            st.rerun()

    with cols[2]:
        if st.button(buttons[2][0], key=buttons[2][1], use_container_width=True):
            _start_takeover("flashcard_stage", "setup")
            st.rerun()

    with cols[3]:
        if st.button(buttons[3][0], key=buttons[3][1], use_container_width=True):
            _start_takeover("quiz_stage", "setup")
            st.rerun()

    next_col = 4
    if has_notes:
        pdf_file = export_notes_to_pdf(st.session_state.study_notes)
        with cols[next_col]:
            with open(pdf_file, "rb") as f:
                st.download_button(
                    "📄 Notes.pdf", data=f, file_name="study_notes.pdf",
                    mime="application/pdf", use_container_width=True, key="tb_dl_pdf",
                )
        with cols[next_col + 1]:
            st.download_button(
                "📥 Notes.md", data=st.session_state.study_notes, file_name="study_notes.md",
                mime="text/markdown", use_container_width=True, key="tb_dl_md",
            )
        next_col += 2

    with cols[next_col]:
        if st.button("🗑 Clear chat", key="tb_clear", use_container_width=True):
            clear_conversation()
            st.success("Cleared")
            st.rerun()


def render_composer_options():
    """The round '+'-style options button that sits to the left of the
    chat input: search mode, plus a reminder of how to attach files
    (the file-attach '+' itself lives natively inside st.chat_input)."""
    trigger = st.container(key="composer_plus")
    with trigger:
        modes = ["Hybrid", "PDF Only", "Web Only"]
        with st.popover("⚙", help="Search mode & options"):
            st.markdown("**Search mode**")
            st.session_state.search_mode = st.radio(
                "Search mode", modes,
                index=modes.index(st.session_state.search_mode),
                label_visibility="collapsed",
                key="search_mode_radio",
            )
            st.caption(
                "Hybrid: answers from your document, falls back to the web. "
                "PDF Only: document only. Web Only: skips the document."
            )
