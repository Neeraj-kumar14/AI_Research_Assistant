import hashlib
import os
import pickle
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from utils.pdf_loader import load_pdf
from utils.docx_loader import load_docx
from utils.chunker import create_chunks
from utils.embedding import create_embeddings
from utils.vector_store import create_vector_store
from utils.language_detector import detect_language
from utils.llm import (
    summarize_pdf,
    generate_flashcards,
    generate_quiz,
    generate_study_notes,
)
from utils.pdf_export import export_notes_to_pdf
from utils.theme import section_label, animated_loader
from components.flashcards import parse_flashcards

# Disk cache for processed documents. OCR + embedding on a large (20-50MB,
# partly scanned) file can take a couple of minutes, so if the same file
# gets re-uploaded (dev reload, reopening the app, a second person using
# the same PDF) we skip straight to a ready vector store instead of
# redoing OCR and re-embedding everything.
CACHE_DIR = ".study_cache"


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
            return pickle.load(f)
    except Exception:
        return None


def _save_to_cache(key, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(_cache_path(key), "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass  # cache is a speed optimization, never let it break processing


def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div style='font-family:\"Source Serif 4\",serif;font-size:1.15rem;"
            "font-weight:600;color:#1B2A4A;margin-bottom:0.2rem;'>📚 Study Desk</div>",
            unsafe_allow_html=True,
        )
        st.caption("Upload once, ask as many times as you like.")

        section_label("Documents")

        uploaded_files = st.file_uploader(
            "Choose PDF or DOCX Files",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        section_label("Search mode")

        st.session_state.search_mode = st.radio(
            "Choose search mode:",
            ["Hybrid", "PDF Only", "Web Only"],
            index=["Hybrid", "PDF Only", "Web Only"].index(
                st.session_state.search_mode
            ),
            label_visibility="collapsed",
        )

        if uploaded_files:
            current_files = [pdf.name for pdf in uploaded_files]

            if (
                "current_pdf_list" not in st.session_state
                or st.session_state.current_pdf_list != current_files
            ):
                progress_label = st.empty()
                progress_bar = st.progress(0)

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

                    # Loading multiple files can overlap I/O even though text
                    # extraction itself is CPU-bound, so this is a cheap win
                    # for multi-file uploads and a no-op for a single file.
                    # Note: load_pdf also runs OCR on any scanned pages it
                    # finds, which is the slowest part of this step for
                    # mixed text/scanned uploads.
                    progress_label.markdown("Reading documents (OCR runs automatically on scanned pages)…")
                    all_pages = []
                    if len(uploaded_files) > 1:
                        with ThreadPoolExecutor(max_workers=min(4, len(uploaded_files))) as pool:
                            for pages in pool.map(_load_one, uploaded_files):
                                all_pages.extend(pages)
                    else:
                        all_pages.extend(_load_one(uploaded_files[0]))
                    progress_bar.progress(15)

                    pdf_text_for_lang = "\n\n".join(page["text"] for page in all_pages)

                    progress_label.markdown("Detecting language…")
                    detected_language = detect_language(pdf_text_for_lang)
                    progress_bar.progress(20)

                    progress_label.markdown("Splitting into chunks…")
                    chunks = create_chunks(all_pages)
                    chunk_texts = [chunk["text"] for chunk in chunks]
                    progress_bar.progress(35)

                    # This is the slow step on large documents, so give it
                    # real, granular progress instead of a flat spinner.
                    def _on_embed_progress(done, total):
                        pct = 35 + int((done / total) * 50) if total else 85
                        progress_bar.progress(min(pct, 85))
                        progress_label.markdown(f"Embedding chunks… {done}/{total}")

                    embeddings = create_embeddings(chunk_texts, progress_callback=_on_embed_progress)
                    progress_bar.progress(90)

                    _save_to_cache(
                        cache_key,
                        {
                            "pages": all_pages,
                            "chunks": chunks,
                            "embeddings": embeddings,
                            "language": detected_language,
                        },
                    )

                pdf_text = "\n\n".join(page["text"] for page in all_pages)
                st.session_state.document_language = detected_language
                st.session_state.pdf_text = pdf_text
                st.session_state.pages = all_pages

                progress_label.markdown("Building search index…")
                vector_store = create_vector_store(embeddings)
                progress_bar.progress(100)

                st.session_state.vector_store = vector_store
                st.session_state.chunks = chunks
                st.session_state.pdf_loaded = True
                st.session_state.current_pdf_list = current_files

                progress_label.empty()
                progress_bar.empty()
                st.success("Document ready")

                section_label("Document stats")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Documents", len(uploaded_files))
                    st.metric("Pages", len(all_pages))
                with col2:
                    st.metric("Chunks", len(chunks))
                    st.metric("Language", st.session_state.document_language)

            else:
                st.success("Document already loaded")

            section_label("Study tools")

            if st.button("📑  Summarize document", use_container_width=True):
                with st.spinner("Generating summary..."):
                    try:
                        summary = summarize_pdf(st.session_state.pdf_text)
                    except Exception as e:
                        st.error(f"Groq Error:\n\n{e}")
                        st.stop()

                st.session_state.messages.append({"role": "user", "content": "📑 Summarize this PDF"})
                st.session_state.messages.append({"role": "assistant", "content": summary})
                st.rerun()

            if st.button("📝  Generate study notes", use_container_width=True):
                with st.spinner("Generating study notes..."):
                    notes = generate_study_notes(st.session_state.pdf_text)
                    st.session_state.study_notes = notes

                st.session_state.messages.append({"role": "user", "content": "📝 Generate Study Notes"})
                st.session_state.messages.append({"role": "assistant", "content": notes})
                st.rerun()

            if st.session_state.get("study_notes"):
                pdf_file = export_notes_to_pdf(st.session_state.study_notes)
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "📄  Download notes (.pdf)",
                        data=f,
                        file_name="study_notes.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

                st.download_button(
                    "📥  Download notes (.md)",
                    data=st.session_state.study_notes,
                    file_name="study_notes.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            if st.button("🧠  Generate flashcards", use_container_width=True):
                with st.spinner("Generating flashcards..."):
                    flashcards_raw = generate_flashcards(st.session_state.pdf_text)
                    parsed_cards = parse_flashcards(flashcards_raw)

                st.session_state.messages.append({"role": "user", "content": "🧠 Generate Flashcards"})
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "type": "flashcards",
                        "content": parsed_cards,
                        "raw": flashcards_raw,
                    }
                )
                st.rerun()

            if st.button("❓  Generate quiz", use_container_width=True):
                loader = st.empty()
                loader.markdown(
                    animated_loader(
                        ["Reading your document", "Identifying key concepts", "Drafting questions", "Finalizing quiz"]
                    ),
                    unsafe_allow_html=True,
                )
                try:
                    quiz = generate_quiz(st.session_state.pdf_text)
                except Exception as e:
                    loader.empty()
                    st.error(f"Groq Error:\n\n{e}")
                    st.stop()
                loader.empty()

                st.session_state.quiz = quiz
                st.session_state.current_question = 0
                st.session_state.quiz_answers = {}
                st.session_state.quiz_score = 0
                st.session_state.quiz_submitted = False
                st.session_state.review_mode = False
                st.rerun()

            st.divider()

            if st.button("🗑  Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.pdf_loaded = False
                st.session_state.review_mode = False
                st.session_state.quiz = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_score = 0
                st.session_state.quiz_submitted = False
                st.session_state.current_question = 0
                st.session_state.study_notes = None

                for key in ["pdf_text", "chunks", "vector_store", "current_pdf_list"]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("Cleared")
                st.rerun()
