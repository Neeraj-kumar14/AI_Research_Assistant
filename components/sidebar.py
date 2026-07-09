import streamlit as st

from utils.pdf_loader import load_pdf
from utils.chunker import create_chunks
from utils.embedding import create_embeddings
from utils.vector_store import create_vector_store
from utils.llm import (
    summarize_pdf,
    generate_flashcards,
    generate_quiz,
    generate_study_notes
)

from utils.pdf_export import export_notes_to_pdf


def render_sidebar():
    with st.sidebar:

        st.header("📄 Upload PDF")

        uploaded_files = st.file_uploader(
            "Choose PDF Files",
            type="pdf",
            accept_multiple_files=True
        )

        st.divider()

        st.subheader("🔍 Search Mode")

        st.session_state.search_mode = st.radio(
            "Choose search mode:",
            [
                "Hybrid",
                "PDF Only",
                "Web Only"
            ],
            index=["Hybrid", "PDF Only", "Web Only"].index(
                st.session_state.search_mode
            )
        )

        st.divider()

        if uploaded_files:

        # Agar nayi PDF hai tabhi process karo
            current_files = [pdf.name for pdf in uploaded_files]

            if (
                    "current_pdf_list" not in st.session_state
                    or st.session_state.current_pdf_list != current_files
                ):

                with st.spinner("Processing PDF..."):

                    all_pages = []

                    for pdf in uploaded_files:

                        pages = load_pdf(pdf)

                        all_pages.extend(pages)

                    pdf_text = ""

                    for page in all_pages:

                        pdf_text += page["text"] + "\n\n"

                    st.session_state.pdf_text = pdf_text
                    st.session_state.pages = all_pages

                    chunks = create_chunks(all_pages)

                    chunk_texts = [chunk["text"] for chunk in chunks]

                    embeddings = create_embeddings(chunk_texts)

                    vector_store = create_vector_store(embeddings)

                    st.session_state.vector_store = vector_store
                    st.session_state.chunks = chunks
                    st.session_state.pdf_loaded = True
                    st.session_state.current_pdf_list = current_files

                st.success("✅ PDF Ready!")

            else:
                st.success("✅ PDF Already Loaded")
            if st.button("📑 Summarize PDF"):

                with st.spinner("Generating Summary..."):

                    try:

                        summary = summarize_pdf(
                            st.session_state.pdf_text
                        )

                    except Exception as e:

                        st.error(f"⚠️ Groq Error:\n\n{e}")

                        st.stop()

                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": "📑 Summarize this PDF"
                    }
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": summary
                    }
                )

                st.rerun()
            if st.button("📝 Generate Study Notes"):

                with st.spinner("Generating Study Notes..."):

                    notes = generate_study_notes(
                        st.session_state.pdf_text
                    )
                    st.session_state.study_notes = notes
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": "📝 Generate Study Notes"
                    }
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": notes
                    }
                )

                st.rerun()

            if st.session_state.study_notes:

                pdf_file = export_notes_to_pdf(
                    st.session_state.study_notes
                )

                with open(pdf_file, "rb") as f:

                    st.download_button(
                        "📄 Download Notes (.pdf)",
                        data=f,
                        file_name="study_notes.pdf",
                        mime="application/pdf"
                    )

            if st.session_state.study_notes:

                st.download_button(
                    "📥 Download Notes (.md)",
                    data=st.session_state.study_notes,
                    file_name="study_notes.md",
                    mime="text/markdown"
                )

            if st.button("🧠 Generate Flashcards"):

                with st.spinner("Generating Flashcards..."):

                    flashcards = generate_flashcards(
                        st.session_state.pdf_text
                    )

                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": "🧠 Generate Flashcards"
                    }
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": flashcards
                    }
                )

                st.rerun()
            if st.button("❓ Generate Quiz"):

                with st.spinner("Generating Quiz..."):

                    try:

                        quiz = generate_quiz(
                            st.session_state.pdf_text
                        )

                    except Exception as e:

                        st.error(f"⚠️ Groq Error:\n\n{e}")

                        st.stop()

                st.session_state.quiz = quiz

                st.session_state.current_question = 0

                st.session_state.quiz_answers = {}

                st.session_state.quiz_score = 0

                st.session_state.quiz_submitted = False

                st.session_state.review_mode = False

                st.rerun()

            if st.button("🗑 Clear Chat"):

    # Clear chat
                st.session_state.messages = []

                # Clear PDF data
                st.session_state.pdf_loaded = False

                st.session_state.review_mode = False

                st.session_state.quiz = None

                st.session_state.quiz_answers = {}

                st.session_state.quiz_score = 0

                st.session_state.quiz_submitted = False

                st.session_state.current_question = 0

                # Remove stored objects
                for key in [
                    "pdf_text",
                    "chunks",
                    "vector_store",
                    "current_pdf_list"
                ]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("✅ Chat and PDF cleared successfully!")

                st.rerun()


            st.divider()