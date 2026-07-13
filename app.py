import streamlit as st

from utils.pdf_loader import load_pdf
from utils.chunker import create_chunks
from utils.embedding import create_embeddings, model
from utils.vector_store import create_vector_store
from utils.retriever import retrieve_chunks
from components.sidebar import render_sidebar
from components.chat import render_chat
from components.quiz import render_quiz
from utils.docx_loader import load_docx
from utils.llm import (
    ask_groq,
    ask_groq_web,
    summarize_pdf,
    rewrite_question,
    needs_rewrite,
    generate_flashcards,
    generate_quiz,
    generate_study_notes
)
from utils.web_search import search_web

st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🤖",
    layout="wide"
)


st.title("🤖 AI Research Assistant")
st.caption("Chat with your PDF using Groq + RAG")


# -----------------------------
# Session State
# -----------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "quiz" not in st.session_state:
    st.session_state.quiz = None

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}

if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

if "review_mode" not in st.session_state:
    st.session_state.review_mode = False

if "current_question" not in st.session_state:
    st.session_state.current_question = 0

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "chunks" not in st.session_state:
    st.session_state.chunks = None

if "pdf_loaded" not in st.session_state:
    st.session_state.pdf_loaded = False

if "study_notes" not in st.session_state:
    st.session_state.study_notes = None

if "search_mode" not in st.session_state:
    st.session_state.search_mode = "Hybrid"

# -----------------------------
# Sidebar
# -----------------------------

render_sidebar()
# with st.sidebar:

#     st.header("📄 Upload PDF")

#     uploaded_files = st.file_uploader(
#         "Choose PDF Files",
#         type="pdf",
#         accept_multiple_files=True
#     )

#     if uploaded_files:

#     # Agar nayi PDF hai tabhi process karo
#         current_files = [pdf.name for pdf in uploaded_files]

#         if (
#                 "current_pdf_list" not in st.session_state
#                 or st.session_state.current_pdf_list != current_files
#             ):

#             with st.spinner("Processing PDF..."):

#                 all_pages = []

#                 for pdf in uploaded_files:

#                     pages = load_pdf(pdf)

#                     all_pages.extend(pages)

#                 pdf_text = ""

#                 for page in all_pages:

#                     pdf_text += page["text"] + "\n\n"

#                 st.session_state.pdf_text = pdf_text
#                 st.session_state.pages = all_pages

#                 chunks = create_chunks(all_pages)

#                 chunk_texts = [chunk["text"] for chunk in chunks]

#                 embeddings = create_embeddings(chunk_texts)

#                 vector_store = create_vector_store(embeddings)

#                 st.session_state.vector_store = vector_store
#                 st.session_state.chunks = chunks
#                 st.session_state.pdf_loaded = True
#                 st.session_state.current_pdf_list = current_files

#             st.success("✅ PDF Ready!")

#         else:
#             st.success("✅ PDF Already Loaded")
#         if st.button("📑 Summarize PDF"):

#             with st.spinner("Generating Summary..."):

#                 try:

#                     summary = summarize_pdf(
#                         st.session_state.pdf_text
#                     )

#                 except Exception as e:

#                     st.error(f"⚠️ Groq Error:\n\n{e}")

#                     st.stop()

#             st.session_state.messages.append(
#                 {
#                     "role": "user",
#                     "content": "📑 Summarize this PDF"
#                 }
#             )

#             st.session_state.messages.append(
#                 {
#                     "role": "assistant",
#                     "content": summary
#                 }
#             )

#             st.rerun()

#         if st.button("🧠 Generate Flashcards"):

#             with st.spinner("Generating Flashcards..."):

#                 flashcards = generate_flashcards(
#                     st.session_state.pdf_text
#                 )

#             st.session_state.messages.append(
#                 {
#                     "role": "user",
#                     "content": "🧠 Generate Flashcards"
#                 }
#             )

#             st.session_state.messages.append(
#                 {
#                     "role": "assistant",
#                     "content": flashcards
#                 }
#             )

#             st.rerun()
#         if st.button("❓ Generate Quiz"):

#             with st.spinner("Generating Quiz..."):

#                 try:

#                     quiz = generate_quiz(
#                         st.session_state.pdf_text
#                     )

#                 except Exception as e:

#                     st.error(f"⚠️ Groq Error:\n\n{e}")

#                     st.stop()

#             st.session_state.quiz = quiz

#             st.session_state.current_question = 0

#             st.session_state.quiz_answers = {}

#             st.session_state.quiz_score = 0

#             st.session_state.quiz_submitted = False

#             st.session_state.review_mode = False

#             st.rerun()

#     st.divider()

#     if st.button("🗑 Clear Chat"):

#     # Clear chat
#         st.session_state.messages = []

#         # Clear PDF data
#         st.session_state.pdf_loaded = False

#         st.session_state.review_mode = False

#         st.session_state.quiz = None

#         st.session_state.quiz_answers = {}

#         st.session_state.quiz_score = 0

#         st.session_state.quiz_submitted = False

#         st.session_state.current_question = 0

#         # Remove stored objects
#         for key in [
#             "pdf_text",
#             "chunks",
#             "vector_store",
#             "current_pdf_list"
#         ]:
#             if key in st.session_state:
#                 del st.session_state[key]

#         st.success("✅ Chat and PDF cleared successfully!")

#         st.rerun()


# st.divider()


# -----------------------------
# Show Chat History
# -----------------------------

# for message in st.session_state.messages:

#     with st.chat_message(message["role"]):

#         if message.get("type") == "quiz":

#             for i, q in enumerate(message["content"], start=1):

#                 st.markdown(f"## Question {i}")

#                 st.markdown(f"**Question:** {q['question']}")

#                 st.markdown("**Options:**")

#                 st.markdown(f"A. {q['options'][0]}")
#                 st.markdown(f"B. {q['options'][1]}")
#                 st.markdown(f"C. {q['options'][2]}")
#                 st.markdown(f"D. {q['options'][3]}")

#                 st.success(f"✅ Correct Answer: {q['answer']}")

#                 st.info(q["explanation"])

#                 st.divider()

#         else:

#             st.markdown(message["content"])
render_chat(st.session_state.messages)

# -----------------------------
# Interactive Quiz
# -----------------------------
render_quiz()
# if st.session_state.quiz:

#     st.header("📝 Interactive Quiz")

#     current = st.session_state.current_question

#     q = st.session_state.quiz[current]

#     st.subheader(
#         f"Question {current + 1} / {len(st.session_state.quiz)}"
#     )

#     progress = (current + 1) / len(st.session_state.quiz)

#     st.progress(progress)

#     st.write(q["question"])

#     selected = st.radio(
#         "Choose your answer:",
#         q["options"],
#         key=f"quiz_{current}",
#         disabled=st.session_state.quiz_submitted
#         )

#     st.session_state.quiz_answers[current] = selected
#     col1, col2 = st.columns(2)

#     with col1:

#         if current > 0:

#             if st.button("⬅ Previous"):

#                 st.session_state.current_question -= 1
#                 st.rerun()

#     with col2:

#         if current < len(st.session_state.quiz) - 1:

#             if st.button("Next ➡"):

#                 st.session_state.current_question += 1
#                 st.rerun()

#         else:

#             if st.button("✅ Submit Quiz"):

#                 score = 0

#                 option_letters = ["A", "B", "C", "D"]

#                 for i, q in enumerate(st.session_state.quiz):

#                     selected = st.session_state.quiz_answers.get(i)

#                     if selected:

#                         selected_letter = option_letters[
#                             q["options"].index(selected)
#                         ]

#                         if selected_letter == q["answer"]:

#                             score += 1

#                 st.session_state.quiz_score = score

#                 st.session_state.quiz_submitted = True

#                 st.rerun()
# # --------------------------------------------------------------------

# if st.session_state.quiz_submitted:

#     total = len(st.session_state.quiz)

#     score = st.session_state.quiz_score

#     percentage = (score / total) * 100

#     st.balloons()

#     st.success(f"🏆 Quiz Completed!")

#     st.markdown(f"## 🎯 Score: {score}/{total}")

#     st.markdown(f"### 📊 Percentage: {percentage:.1f}%")

#     if percentage >= 90:

#         st.success("🥇 Excellent!")

#     elif percentage >= 75:

#         st.success("🥈 Very Good!")

#     elif percentage >= 60:

#         st.warning("🥉 Good Job!")

#     else:

#         st.error("📚 Needs More Practice!")

#     st.progress(percentage / 100)

#     if st.button("📖 Review Answers"):

#         st.session_state.review_mode = True

#         st.rerun()

# if st.session_state.review_mode:

#     st.header("📖 Review Answers")

#     option_letters = ["A", "B", "C", "D"]

#     for i, q in enumerate(st.session_state.quiz):

#         st.subheader(f"Question {i+1}")

#         st.write(q["question"])

#         selected = st.session_state.quiz_answers.get(i)

#         if selected:

#             selected_letter = option_letters[
#                 q["options"].index(selected)
#             ]

#             st.write(f"**Your Answer:** {selected_letter}")

#             st.write(f"**Correct Answer:** {q['answer']}")

#             if selected_letter == q["answer"]:

#                 st.success("✅ Correct")

#             else:

#                 st.error("❌ Wrong")

#         st.info(q["explanation"])

#         st.divider()
# -----------------------------
# Chat Input
# -----------------------------
question = st.chat_input("Ask anything about your document...")

if question:

    if not st.session_state.pdf_loaded:

        st.warning("Please upload a PDF or DOCX file first.")

    else:

        # Show User Message
        with st.chat_message("user"):
            st.markdown(question)

        # Save User Message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        if needs_rewrite(question):

            rewritten_question = rewrite_question(
                question,
                st.session_state.messages
            )

        else:

            rewritten_question = question

        st.caption(f"🔄 Rewritten Question: {rewritten_question}")
        search_mode = st.session_state.search_mode
        context, sources = retrieve_chunks(
            rewritten_question,
            model,
            st.session_state.vector_store,
            st.session_state.chunks
        )

        # Ask Groq
        with st.spinner("🤖 Thinking..."):

            try:

                web_sources = []

                if search_mode == "PDF Only":

                    answer = ask_groq(
                        context,
                        rewritten_question,
                        st.session_state.messages
                    )

                elif search_mode == "Web Only":

                    web_context, web_sources = search_web(
                        rewritten_question
                    )

                    answer = ask_groq_web(
                        web_context,
                        rewritten_question
                    )

                else:   # Hybrid

                    answer = ask_groq(
                        context,
                        rewritten_question,
                        st.session_state.messages
                    )

                    if "I couldn't find this information" in answer:

                        with st.spinner("🌐 Searching the Web..."):

                            web_context, web_sources = search_web(
                                rewritten_question
                            )

                            answer = ask_groq_web(
                                web_context,
                                rewritten_question
                            )

            except Exception as e:

                st.error(f"Groq Error:\n{e}")

                st.stop()

        # Show AI Message
        with st.chat_message("assistant"):
            st.markdown(answer)
            st.markdown("### 📚 Sources")

            shown = set()

            for chunk in sources:

                source = f"📄 {chunk['source']} (Page {chunk['page']})"

                if source not in shown:
                    st.markdown(source)
                    shown.add(source)
            if web_sources:

                st.markdown("### 🌐 Web Sources")

                for url in web_sources:

                    st.markdown(f"- {url}")
        # Save AI Message
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )
