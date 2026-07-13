import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing API key. Set GROQ_API_KEY in your .env file or environment."
        )

    return Groq(api_key=api_key)


def ask_groq(context: str, question: str, chat_history=None):
    history = ""

    if chat_history:

        for msg in chat_history[-6:]:

            role = msg["role"].capitalize()

            history += f"{role}: {msg['content']}\n"
    prompt = f"""
You are an AI Research Assistant.

Rules:
Rules:
Rules:
1. Answer ONLY from the provided context.
2. Never use your own knowledge.
3. If the answer is not available in the context, reply:
   "I couldn't find this information in the uploaded PDF."
4. Detect the language of the user's question.
5. Your response MUST be in the same language as the user's question.
6. Do NOT translate the response into English.
7. If the user's question is in Hindi, write the entire response in Hindi using Devanagari script.
8. Follow these language rules even if the document is in another language, unless the user explicitly asks for translation.

Conversation History:
{history}

Context:
{context}

Current Question:
{question}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content or ""


# ----------------------------------------------------------------------------------

def summarize_pdf(pdf_text: str):

    prompt = f"""
You are an AI Research Assistant.

Summarize the following PDF.

Give the output in this format:

## Summary

## Key Topics

## Key Takeaways

PDF Content:

{pdf_text}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content or ""

# --------------------------------------------------------------------------------------------------------
def rewrite_question(question: str, chat_history):

    history = ""

    # Last 6 messages only
    for msg in chat_history[-6:]:

        role = msg["role"].capitalize()

        history += f"{role}: {msg['content']}\n"

    prompt = f"""
You are a query rewriting assistant.

Rewrite the latest user question into a standalone question.

Rules:

1. Keep the meaning exactly the same.
2. Replace pronouns like "it", "this", "that", "they", "these", "those" with the correct subject from the conversation history.
3. Do NOT add extra information.
4. Do NOT expand the question.
5. Do NOT answer the question.
6. If the latest question is already complete, return it unchanged.
7. Return ONLY the rewritten question.

Conversation History:
{history}

Latest Question:
{question}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()
# -----------------------------------------------------------------------------------------
FOLLOW_UP_WORDS = {
    "it",
    "this",
    "that",
    "they",
    "them",
    "these",
    "those",
    "he",
    "she",
    "its",
    "their"
}


def needs_rewrite(question: str) -> bool:

    question = question.lower()

    words = question.split()

    if any(word in FOLLOW_UP_WORDS for word in words):
        return True

    followup_phrases = [
        "explain more",
        "tell me more",
        "give example",
        "compare",
        "why",
        "how about",
        "what about"
    ]

    return any(
        phrase in question
        for phrase in followup_phrases
    )

# ----------------------------------------------------------------------------------------
def generate_flashcards(pdf_text: str):

    prompt = f"""
You are an AI tutor.

Generate 10 high-quality flashcards from the PDF.

Rules:
- Use only the PDF content.
- Make concise questions.
- Keep answers short.
- Use Markdown.

Format EXACTLY like this:

## Flashcard 1

**Q:**
<Question here>

**A:**
<Answer here>

---

## Flashcard 2

**Q:**
<Question here>

**A:**
<Answer here>

Rules for formatting:
- Put the answer on a new line below the question.
- Never write the question and answer on the same line.

PDF:

{pdf_text}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content or ""

# =======================================================================================

def generate_quiz(pdf_text: str):

    prompt = f"""
You are an AI tutor.

Generate exactly 10 multiple-choice questions from the PDF.

Return ONLY valid JSON.

Do not return markdown.

Do not return explanations outside JSON.

JSON format:

[
  {{
    "question": "...",
    "options": [
      "...",
      "...",
      "...",
      "..."
    ],
    "answer": "A",
    "explanation": "..."
  }}
]

Rules:

- Use ONLY the PDF.
- Exactly 4 options.
- Only one correct answer.
- Answer must be A, B, C or D.

PDF:

{pdf_text}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content or ""

    return json.loads(content)

# ======================================================================

def generate_study_notes(pdf_text: str):

    prompt = f"""
You are an expert AI tutor.

Create high-quality study notes from the following PDF.

Output format:

# 📘 Study Notes

## Overview

## Important Concepts

## Definitions

## Key Points

## Examples

## Advantages

## Disadvantages

## Applications

## Interview Questions

## Common Mistakes

## Quick Revision

Use proper markdown formatting.

PDF Content:

{pdf_text}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content or ""

# ===========================================================================

def ask_groq_web(context: str, question: str):

    prompt = f"""
You are an AI Research Assistant.

Answer the user's question ONLY using the web search results below.

Rules:
1. Do not make up information.
2. Use only the provided web context.
3. Give a clear answer.
4. Mention important details if available.

Web Context:

{context}

Question:

{question}
"""

    response = get_groq_client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content or ""