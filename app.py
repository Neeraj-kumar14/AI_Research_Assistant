import os
import time

import streamlit as st

from utils.embedding import model
from utils.retriever import retrieve_chunks
from utils.llm import (
    ask_groq,
    ask_groq_web,
    rewrite_question,
    needs_rewrite,
)
from utils.web_search import search_web
from utils.theme import inject_css, render_hero, render_feature_grid
from components.sidebar import render_sidebar
from components.chat import render_chat
from components.quiz import render_quiz
from components.quiz_setup import render_quiz_setup
from components.flashcard_setup import render_flashcard_setup
from components.flashcards import render_flashcard_deck

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="📚",
    layout="wide",
)

inject_css()

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
    "search_mode": "Hybrid",
    "study_notes": None,
    "document_language": None,
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
# in components/sidebar.py means a re-upload of the same file is fast.
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
    st.info(
        "Your document was unloaded after a period of inactivity to free up "
        "memory. Please re-upload it — if it's the same file, it'll load "
        "quickly from cache."
    )

st.session_state.last_active = now

# -----------------------------
# Sidebar
# -----------------------------
render_sidebar()

# -----------------------------
# Landing hero (only before a document is loaded, so the chat isn't
# competing with the pitch once someone is actually using the tool)
# -----------------------------
quiz_takeover = st.session_state.quiz_stage in ("setup", "active")
flashcard_takeover = st.session_state.flashcard_stage in ("setup", "active")
takeover = quiz_takeover or flashcard_takeover

if not takeover:
    if not st.session_state.pdf_loaded and not st.session_state.messages:
        render_hero()
        render_feature_grid()
        st.markdown("")

    # -----------------------------
    # Chat history
    # -----------------------------
    render_chat(st.session_state.messages)

# -----------------------------
# Interactive quiz — takes over as its own full-width "slide" once the
# user clicks Generate quiz in the sidebar, so it isn't competing with
# the chat transcript underneath it.
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
# Chat input
# -----------------------------
if not takeover:
    question = st.chat_input("Ask anything about your document...")
else:
    question = None

if question:
    if not st.session_state.pdf_loaded:
        st.warning("Please upload a PDF or DOCX file first.")
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

        with st.spinner("🤖 Thinking..."):
            try:
                web_sources = []

                if search_mode == "PDF Only":
                    answer = ask_groq(context, rewritten_question, st.session_state.messages)

                elif search_mode == "Web Only":
                    web_context, web_sources = search_web(rewritten_question)
                    answer = ask_groq_web(web_context, rewritten_question)
                    sources = []

                else:  # Hybrid
                    answer = ask_groq(context, rewritten_question, st.session_state.messages)

                    if "I couldn't find this information" in answer:
                        with st.spinner("🌐 Searching the web..."):
                            web_context, web_sources = search_web(rewritten_question)
                            answer = ask_groq_web(web_context, rewritten_question)
                            sources = []

            except Exception as e:
                st.error(f"Groq Error:\n{e}")
                st.stop()

        with st.chat_message("assistant"):
            st.markdown(answer)
            from components.chat import render_source_cards
            render_source_cards(sources, web_sources)

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
