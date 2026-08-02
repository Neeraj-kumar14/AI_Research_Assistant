import html

import streamlit as st

from components.chat_toolbar import clear_conversation, _start_takeover
from utils.llm import summarize_pdf
from utils.pdf_export import export_notes_to_pdf
from utils.errors import show_llm_error


def render_sidebar():
    """Left navigation: New chat up top, then the study tools (each a
    flat nav row instead of the old centered pill), then a read-only
    trail of everything asked so far this session — the ChatGPT-style
    layout, in a glass "3D" panel matching the rest of the console."""
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand"><span class="mark">📚</span> AI Research Assistant</div>',
            unsafe_allow_html=True,
        )

        with st.container(key="sb_new_chat"):
            if st.button("＋  New chat", use_container_width=True, key="sb_new_chat_btn"):
                clear_conversation()
                st.rerun()

        pdf_loaded = st.session_state.get("pdf_loaded", False)

        st.markdown('<div class="sb-section-label">Study tools</div>', unsafe_allow_html=True)
        with st.container(key="sb_tools"):
            if st.button(
                "📑  Summarize", use_container_width=True, key="sb_nav_summarize",
                disabled=not pdf_loaded,
            ):
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

            if st.button(
                "📝  Study notes", use_container_width=True, key="sb_nav_notes",
                disabled=not pdf_loaded,
            ):
                _start_takeover("notes_stage", "setup")
                st.rerun()

            if st.button(
                "🧠  Flashcards", use_container_width=True, key="sb_nav_flashcards",
                disabled=not pdf_loaded,
            ):
                _start_takeover("flashcard_stage", "setup")
                st.rerun()

            if st.button(
                "❓  Quiz", use_container_width=True, key="sb_nav_quiz",
                disabled=not pdf_loaded,
            ):
                _start_takeover("quiz_stage", "setup")
                st.rerun()

            if st.session_state.get("study_notes"):
                pdf_file = export_notes_to_pdf(st.session_state.study_notes)
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "📄  Download notes",
                        data=f,
                        file_name="study_notes.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="sb_dl_notes",
                    )

        if not pdf_loaded:
            st.caption("Attach a document to unlock these.")

        st.markdown('<div class="sb-section-label">History</div>', unsafe_allow_html=True)
        past_questions = [
            m["content"]
            for m in st.session_state.get("messages", [])
            if m.get("role") == "user" and m.get("type") not in ("quiz", "flashcards") and m.get("content")
        ]
        if past_questions:
            for q in reversed(past_questions[-25:]):
                label = q if len(q) <= 42 else q[:39] + "…"
                st.markdown(
                    f'<div class="sb-history-item" title="{html.escape(q)}">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="sb-history-empty">Nothing asked yet</div>', unsafe_allow_html=True)
