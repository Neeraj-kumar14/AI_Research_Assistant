import os
import time

import streamlit as st

from utils.embedding import model
from utils.retriever import retrieve_chunks
from utils.llm import (
    ask_groq,
    ask_groq_stream,
    ask_groq_web_stream,
    rewrite_question,
    needs_rewrite,
    NOTE_SECTIONS,
)
from utils.web_search import search_web, WebSearchError
from utils.errors import show_llm_error
from utils.theme import inject_css, render_hero, render_topbar, inject_scroll_preserver
from components.chat_toolbar import (
    sync_documents,
    add_files,
    render_document_chips,
    render_toolbar_actions,
    render_composer_options,
)
from components.chat import render_chat, render_source_cards
from components.quiz import render_quiz
from components.quiz_setup import render_quiz_setup
from components.flashcard_setup import render_flashcard_setup
from components.flashcards import render_flashcard_deck
from components.notes_setup import render_notes_setup

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="📚",
    layout="wide",
)

inject_css()
inject_scroll_preserver()

# -----------------------------
# Session State
# -----------------------------
defaults = {
    "messages": [],
    "quiz": None,
    "quiz_stage": None,  # None | "setup" | "active"
    "quiz_num_questions": 10,
    "quiz_difficulty": "Medium",
    "quiz_timer_mode": "per_question",  # "per_question" | "total"
    "quiz_time_per_question": 0,  # seconds; 0 = no time limit
    "quiz_total_minutes": 0,  # 0 = no time limit
    "quiz_total_time_limit": 0,  # seconds, computed when the quiz starts
    "quiz_question_start_time": None,
    "quiz_start_time": None,
    "quiz_flagged": {},
    "quiz_answers": {},
    "quiz_score": 0,
    "quiz_submitted": False,
    "review_mode": False,
    "current_question": 0,
    "flashcard_stage": None,  # None | "setup" | "active"
    "flashcard_num": 10,
    "flashcard_difficulty": "Medium",
    "flashcard_focus": "",
    "flashcards": None,
    "flashcard_order": [],
    "flashcard_current": 0,
    "flashcard_known": {},
    "flashcard_starred": {},
    "flashcard_direction": "next",
    "flashcard_view": "deck",
    "vector_store": None,
    "chunks": None,
    "pdf_loaded": False,
    "doc_files": [],
    "search_mode": "Hybrid",
    "study_notes": None,
    "document_language": None,
    "notes_stage": None,  # None | "setup"
    "notes_style": "Detailed",  # "Concise" | "Detailed" | "Exam-focused"
    "notes_sections": {key for key, _ in NOTE_SECTIONS},
    "notes_focus": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# -----------------------------
# Idle-session eviction
#
# Streamlit already frees a session's memory when its browser tab
# actually closes, so the real gap is a tab left OPEN but idle — its
# vector store + chunks (often the biggest objects per session) sit in
# RAM the whole time, and with many concurrent users this adds up on a
# free/shared host. Since Python here only runs when a rerun happens,
# "idle time" is measured between reruns: each run stamps last_active,
# and the next run (whenever that happens, even hours later) checks
# the gap and evicts the heavy state if it's stale, before rendering
# anything that would depend on it. Chat history is intentionally kept
# — only the loaded-document state is cleared, since the on-disk cache
# in components/chat_toolbar.py means reprocessing the same file is fast.
# Override via SESSION_IDLE_TIMEOUT_SECONDS env var.
SESSION_IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", str(30 * 60)))

now = time.time()
last_active = st.session_state.get("last_active")

if (
    last_active is not None
    and (now - last_active) > SESSION_IDLE_TIMEOUT_SECONDS
    and st.session_state.get("pdf_loaded")
):
    for key in ["vector_store", "chunks", "pdf_text", "pages", "current_pdf_list"]:
        st.session_state.pop(key, None)
    st.session_state.pdf_loaded = False
    st.session_state.document_language = None
    # doc_files (the accumulated attachment list) is deliberately kept —
    # sync_documents() below notices current_pdf_list no longer matches
    # it and transparently rebuilds from the on-disk cache.

st.session_state.last_active = now

# -----------------------------
# Documents — reprocess the accumulated attachment set if it has
# changed (new file attached, or one removed) since the last run.
# -----------------------------
sync_documents()

# -----------------------------
# Top bar (replaces the old sidebar branding)
# -----------------------------
_status = ""
if st.session_state.pdf_loaded:
    _status = (
        f"{len(st.session_state.get('doc_files', []))} doc(s) · "
        f"{len(st.session_state.get('pages', []))} pages · "
        f"{st.session_state.get('document_language', '—')}"
    )
with st.container(key="sticky_header"):
    render_topbar(_status)
    if st.session_state.pdf_loaded:
        render_toolbar_actions()

# -----------------------------
# Landing hero (only before a document is loaded, so the chat isn't
# competing with the pitch once someone is actually using the tool)
# -----------------------------
quiz_takeover = st.session_state.quiz_stage in ("setup", "active")
flashcard_takeover = st.session_state.flashcard_stage in ("setup", "active")
notes_takeover = st.session_state.notes_stage == "setup"
takeover = quiz_takeover or flashcard_takeover or notes_takeover

if not takeover:
    if not st.session_state.pdf_loaded and not st.session_state.messages:
        render_hero()

    # -----------------------------
    # Chat history
    # -----------------------------
    render_chat(st.session_state.messages)

# -----------------------------
# Interactive quiz — takes over as its own full-width "slide" once the
# user clicks Quiz in the toolbar, so it isn't competing with the chat
# transcript underneath it.
# -----------------------------
if st.session_state.quiz_stage == "setup":
    render_quiz_setup()
elif st.session_state.quiz_stage == "active":
    render_quiz()

# -----------------------------
# Flashcard deck — same full-slide takeover pattern as the quiz.
# -----------------------------
if st.session_state.flashcard_stage == "setup":
    render_flashcard_setup()
elif st.session_state.flashcard_stage == "active":
    render_flashcard_deck()

# -----------------------------
# Study notes setup — floating modal dialog, same pattern as flashcards.
# -----------------------------
if st.session_state.notes_stage == "setup":
    render_notes_setup()

# -----------------------------
# Composer — pinned to the bottom of the page. Document chips (and the
# search-mode/options popover) sit directly above a chat_input whose
# built-in "+" attach button lets you drop in more PDFs/DOCX at any
# time, the same way this very chat interface's composer works.
# -----------------------------
submission = None
if not takeover:
    with st.bottom:
        render_document_chips()
        col_opts, col_input = st.columns([0.055, 0.945], gap="small")
        with col_opts:
            render_composer_options()
        with col_input:
            placeholder = (
                "Message AI Research Assistant..."
                if st.session_state.pdf_loaded
                else "Attach a PDF or DOCX with + to get started, or just ask a question..."
            )
            submission = st.chat_input(
                placeholder,
                accept_file="multiple",
                file_type=["pdf", "docx"],
            )

question = None
attached_files = []
if submission:
    question = submission.text.strip() if submission.text else ""
    attached_files = list(submission.files) if submission.files else []

if attached_files:
    add_files(attached_files)
    sync_documents()  # ingest immediately so a same-turn question can use it
    if not question:
        st.rerun()  # files-only turn: just ingest and refresh, no chat bubble needed

if question:
    if not st.session_state.pdf_loaded:
        st.warning("Attach a PDF or DOCX file first (use the + in the message box).")
    else:
        with st.chat_message("user"):
            st.markdown(question)

        st.session_state.messages.append({"role": "user", "content": question})

        if needs_rewrite(question):
            rewritten_question = rewrite_question(question, st.session_state.messages)
        else:
            rewritten_question = question

        search_mode = st.session_state.search_mode
        context, sources = retrieve_chunks(
            rewritten_question,
            model,
            st.session_state.vector_store,
            st.session_state.chunks,
        )

        web_sources = []
        answer = ""

        # Streamed via st.write_stream() so tokens appear as they're
        # generated instead of the user staring at a spinner for the
        # whole call. The one exception is Hybrid mode's *first* pass:
        # we have to see the complete answer before we can decide
        # whether to fall back to the web, so streaming it would mean
        # showing partial text and then yanking it away if the
        # fallback triggers — worse than a brief spinner. Only Hybrid's
        # (less common) web-fallback pass streams.
        with st.chat_message("assistant"):
            try:
                if search_mode == "PDF Only":
                    with st.spinner("🤖 Thinking..."):
                        stream = ask_groq_stream(context, rewritten_question, st.session_state.messages)
                    answer = st.write_stream(stream)

                elif search_mode == "Web Only":
                    with st.spinner("🌐 Searching the web..."):
                        web_context, web_sources = search_web(rewritten_question)
                        stream = ask_groq_web_stream(web_context, rewritten_question)
                    sources = []
                    answer = st.write_stream(stream)

                else:  # Hybrid
                    with st.spinner("🤖 Thinking..."):
                        answer = ask_groq(context, rewritten_question, st.session_state.messages)

                    if "I couldn't find this information" in answer:
                        with st.spinner("🌐 Searching the web..."):
                            web_context, web_sources = search_web(rewritten_question)
                            stream = ask_groq_web_stream(web_context, rewritten_question)
                        sources = []
                        answer = st.write_stream(stream)
                    else:
                        st.markdown(answer)

                render_source_cards(sources, web_sources)

            except WebSearchError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                show_llm_error(e, action="answer your question")
                st.stop()

        # Only "source" and "page" are ever read back from stored
        # sources (see components/chat.py render_source_cards) — the
        # full chunk text isn't needed again, but was previously kept
        # in session_state for the life of the session regardless.
        # Trimming here means each question asked adds a few dozen
        # bytes of citation metadata to memory instead of the full
        # chunk text (up to ~1800 chars each, times k chunks, times
        # every question) — meaningful over a long session.
        stored_sources = (
            [{"source": c["source"], "page": c["page"]} for c in sources]
            if sources else sources
        )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": stored_sources,
                "web_sources": web_sources,
            }
        )
