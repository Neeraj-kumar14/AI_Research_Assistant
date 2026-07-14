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
    "quiz_answers": {},
    "quiz_score": 0,
    "quiz_submitted": False,
    "review_mode": False,
    "current_question": 0,
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
# Sidebar
# -----------------------------
render_sidebar()

# -----------------------------
# Landing hero (only before a document is loaded, so the chat isn't
# competing with the pitch once someone is actually using the tool)
# -----------------------------
if not st.session_state.pdf_loaded and not st.session_state.messages:
    render_hero()
    render_feature_grid()
    st.markdown("")

# -----------------------------
# Chat history
# -----------------------------
render_chat(st.session_state.messages)

# -----------------------------
# Interactive quiz
# -----------------------------
render_quiz()

# -----------------------------
# Chat input
# -----------------------------
question = st.chat_input("Ask anything about your document...")

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

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "web_sources": web_sources,
            }
        )
