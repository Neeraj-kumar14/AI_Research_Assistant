# 🤖 AI Research Assistant (Hybrid RAG + Web Search)

An AI-powered Research Assistant built with **Streamlit**, **Groq Llama 3.3 70B**, **Retrieval-Augmented Generation (RAG)**, **FAISS**, **Sentence Transformers**, and **Tavily Web Search**.

The application allows users to upload one or multiple PDF documents, ask questions, generate AI-powered study materials, and automatically search the web whenever the uploaded documents don't contain the requested information.

---

## 🚀 Features

- 📄 Multi-PDF Upload
- 🤖 AI Chat with PDFs
- 🧠 Conversation Memory
- 🔄 Query Rewriting
- 📚 Source Citations
- 📑 PDF Summarization
- 📝 AI Study Notes Generator
- 🧠 Flashcard Generator
- ❓ Interactive Quiz
- 🏆 Quiz Evaluation & Review
- 📥 Download Study Notes (PDF & Markdown)
- 🌐 Hybrid Search (PDF + Web Search)
- 🔍 Search Modes
  - PDF Only
  - Web Only
  - Hybrid (Automatic Fallback)
- ⚡ Powered by Groq Llama 3.3 70B
- 🎨 Interactive Streamlit UI

---

# 📸 Application Screenshots

## 🏠 Home Screen

![Home](assets/home.png)

---

## 📑 PDF Summary

![Summary](assets/summary.png)

---

## 📝 AI Study Notes

![Notes](assets/notes.png)

---

## 🧠 Flashcards

![Flashcards](assets/flashcards.png)

---

## ❓ Interactive Quiz

![Quiz](assets/quiz_generation.png)

---

## 🏆 Quiz Result

![Quiz Result](assets/quiz_result.png)

---

# 🛠 Tech Stack

### Frontend

- Streamlit

### Backend

- Python

### AI & LLM

- Groq API
- Llama 3.3 70B Versatile

### RAG

- Sentence Transformers
- FAISS

### Web Search

- Tavily Search API

### PDF Processing

- PyMuPDF

### PDF Export

- ReportLab

---

# 📂 Project Structure

```text
AI_Research_Assistant/
│
├── app.py
│
├── components/
│   ├── __init__.py
│   ├── sidebar.py
│   ├── chat.py
│   ├── quiz.py
│   └── study_tools.py
│
├── utils/
│   ├── chunker.py
│   ├── embedding.py
│   ├── llm.py
│   ├── pdf_export.py
│   ├── pdf_loader.py
│   ├── retriever.py
│   ├── vector_store.py
│   └── web_search.py
│
├── assets/
├── README.md
├── requirements.txt
└── .gitignore
```

---

# ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI_Research_Assistant.git
```

### 2. Navigate to the Project

```bash
cd AI_Research_Assistant
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Create `.env` File

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 7. Run the Application

```bash
streamlit run app.py
```

---

# 🎯 Search Modes

The application supports three intelligent search modes:

### 📄 PDF Only

Answers are generated only from the uploaded PDF documents.

### 🌐 Web Only

Answers are generated only using Tavily Web Search.

### 🤖 Hybrid (Recommended)

The assistant first searches the uploaded PDF.

If the answer is unavailable, it automatically searches the web and generates a response using the latest online information.

---

# 🔮 Future Improvements

- 🎙 Voice Chat
- 🔊 Text-to-Speech
- 📊 Image & Table Extraction
- 📈 Research Report Generator
- 🤖 Multi-LLM Support
- 📤 Chat Export
- ☁ Cloud Deployment
- 👥 User Authentication

---

# 👨‍💻 Author

**Neeraj Kumar**

B.Tech CSE (Artificial Intelligence & Machine Learning)

---

## ⭐ Support

If you found this project helpful, please consider giving it a ⭐ on GitHub.

It helps others discover the project and motivates further development.