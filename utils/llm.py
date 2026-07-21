import os
import json
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()


# ---------------------------------------------------------------------------
# Multi-model / multi-key fallback
#
# Groq's free tier gives each MODEL its own separate daily token budget
# (e.g. llama-3.3-70b-versatile: 100K tokens/day, llama-3.1-8b-instant:
# 500K tokens/day — these do not share a pool). So the cheapest fix for
# "ran out of tokens" is often just falling back to a different model on
# the SAME key. Adding more keys (e.g. separate free Groq accounts)
# stacks additional headroom on top of that.
#
# Configure via .env:
#   GROQ_API_KEY        = your primary key (required)
#   GROQ_API_KEY_2       = optional second key
#   GROQ_API_KEY_3       = optional third key
#   GROQ_API_KEY_4       = optional fourth key
#   GROQ_MODEL_FALLBACKS = comma-separated model names to try in order,
#                          for each key. Defaults to a sensible chain if unset.
#
# Every call in this file goes through chat_completion(), which walks
# (key, model) pairs in order and only moves to the next one when it
# hits a rate limit — any other error (bad request, auth failure, etc.)
# still surfaces immediately instead of being silently retried.
# ---------------------------------------------------------------------------

DEFAULT_MODEL_FALLBACKS = "llama-3.3-70b-versatile,llama-3.1-8b-instant,openai/gpt-oss-120b"

_fallback_chain = None  # built lazily, cached for the process lifetime


def _build_fallback_chain():
    keys = []
    for var in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4"):
        key = os.getenv(var)
        if key:
            keys.append(key)

    if not keys:
        # Fall back to the old GEMINI_API_KEY alias for backward compatibility
        legacy_key = os.getenv("GEMINI_API_KEY")
        if legacy_key:
            keys.append(legacy_key)

    if not keys:
        raise RuntimeError(
            "Missing API key. Set GROQ_API_KEY in your .env file or environment "
            "(optionally GROQ_API_KEY_2 / _3 / _4 for additional fallback accounts)."
        )

    models_env = os.getenv("GROQ_MODEL_FALLBACKS", DEFAULT_MODEL_FALLBACKS)
    models = [m.strip() for m in models_env.split(",") if m.strip()]

    if not models:
        models = [DEFAULT_MODEL_FALLBACKS.split(",")[0]]

    # Try every model on the first key before moving to the next key —
    # a different model on the same key is "free" (no new account needed)
    # and already solves most single-model rate-limit errors.
    chain = [(key, model) for key in keys for model in models]
    return chain


def _get_fallback_chain():
    global _fallback_chain
    if _fallback_chain is None:
        _fallback_chain = _build_fallback_chain()
    return _fallback_chain


# Without an explicit timeout, a stalled or slow-to-respond request can
# hang far longer than expected with no error at all — from the UI this
# is indistinguishable from a broken spinner. This bounds every single
# Groq call so a bad request fails loudly (and moves to the next
# fallback candidate) instead of hanging forever.
REQUEST_TIMEOUT_SECONDS = 45


def _is_rate_limit_error(exc) -> bool:
    msg = str(exc).lower()
    return "429" in str(exc) or "rate_limit" in msg or "rate limit" in msg


def _is_timeout_error(exc) -> bool:
    msg = str(exc).lower()
    return "timeout" in msg or "timed out" in msg


def chat_completion(messages, temperature=0.2):
    """Single entry point for every Groq call in this file. Walks the
    (api_key, model) fallback chain in order and returns the first
    successful response. Only raises once every candidate has been
    exhausted by a rate limit or timeout; any non-rate-limit,
    non-timeout error (bad request, invalid key, etc.) is raised
    immediately instead of masking a real bug behind retries."""
    chain = _get_fallback_chain()
    last_error = None
    attempted = []

    for api_key, model in chain:
        attempted.append(model)
        try:
            client = Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if _is_rate_limit_error(e) or _is_timeout_error(e):
                continue  # try the next (key, model) candidate
            raise  # real error — don't hide it behind fallback retries

    raise RuntimeError(
        f"All configured models/keys are rate-limited (tried: {', '.join(attempted)}). "
        f"Last error: {last_error}"
    )


# Max concurrent Groq requests during map-step condensation. Groq calls
# are I/O-bound (network round-trips), so threads — not asyncio — are
# the right tool here and this is a plain speedup with no added
# complexity. Keep this modest: Groq's free tier rate-limits on
# concurrent/per-minute requests too, not just daily tokens, so a very
# high value can trip 429s that chat_completion's fallback chain then
# has to absorb. 5 is a safe default; drop to 2-3 if you see rate-limit
# fallbacks kicking in during condensation.
CONDENSE_MAX_WORKERS = 3


def _condense_chunk(chunk: str) -> str:
    prompt = f"""Condense the following text into a dense, factual summary.
Preserve all names, numbers, dates, definitions, and key details.
Do not add commentary or opinions. Keep it well under the original length.

Text:
{chunk}
"""
    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)


def _condense_large_text(text: str, max_chars: int = 30000, chunk_chars: int = 12000, max_passes: int = 4):
    """Map-reduce condensation for documents too large to fit in one
    context window.

    If the text already fits, it's returned unchanged — no extra API
    calls, no behavior change for normal-sized documents. If it doesn't
    fit, it's split into chunks, each chunk gets condensed into a dense
    summary IN PARALLEL (this is the slow step on large documents —
    previously one sequential API call per chunk), the results are
    joined back together, and the whole thing repeats (up to
    max_passes) until it's small enough.
    """
    passes = 0

    while len(text) > max_chars and passes < max_passes:
        chunks = [text[i:i + chunk_chars] for i in range(0, len(text), chunk_chars)]

        with ThreadPoolExecutor(max_workers=min(CONDENSE_MAX_WORKERS, len(chunks))) as pool:
            # map() preserves input order in its results, so condensed
            # parts stay in the same order as the original chunks even
            # though the calls themselves run concurrently.
            condensed_parts = list(pool.map(_condense_chunk, chunks))

        text = "\n\n".join(condensed_parts)
        passes += 1

    if len(text) > max_chars:
        text = text[:max_chars]

    return text


# ----------------------------------------------------------------------------------

def ask_groq(context: str, question: str, chat_history=None):
    history = ""

    if chat_history:
        for msg in chat_history[-6:]:
            role = msg["role"].capitalize()
            history += f"{role}: {msg['content']}\n"

    prompt = f"""
You are an AI Research Assistant.

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

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)


# --------------------------------------------------------------------------------------------------------

def _language_instruction(language: str | None) -> str:
    """Build a language-enforcement instruction to prepend to a prompt.
    Without this, the model tends to default to English regardless of
    the source document's language — this is what makes summarize_pdf,
    generate_flashcards, generate_quiz, and generate_study_notes
    actually respond in the document's detected language instead."""
    if not language or language == "Unknown":
        return ""
    return (
        f"IMPORTANT: Write your entire response in {language}, matching "
        f"the language of the source document. Do not translate or "
        f"switch to English, even for headings — only the exact "
        f"Markdown formatting symbols (e.g. #, ##, **, ---) stay as-is.\n\n"
    )


def summarize_pdf(pdf_text: str, language: str | None = None):

    pdf_text = _condense_large_text(pdf_text)

    prompt = f"""
{_language_instruction(language)}You are an AI Research Assistant.

Summarize the following PDF.

Give the output in this format:

## Summary

## Key Topics

## Key Takeaways

PDF Content:

{pdf_text}
"""

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)


# --------------------------------------------------------------------------------------------------------

def rewrite_question(question: str, chat_history):

    history = ""

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

    return chat_completion([{"role": "user", "content": prompt}], temperature=0).strip()


# -----------------------------------------------------------------------------------------

FOLLOW_UP_WORDS = {
    "it", "this", "that", "they", "them", "these", "those", "he", "she", "its", "their"
}


def needs_rewrite(question: str) -> bool:

    question = question.lower()
    words = question.split()

    if any(word in FOLLOW_UP_WORDS for word in words):
        return True

    followup_phrases = [
        "explain more", "tell me more", "give example", "compare", "why", "how about", "what about"
    ]

    return any(phrase in question for phrase in followup_phrases)


# ----------------------------------------------------------------------------------------

def generate_flashcards(pdf_text: str, language: str | None = None):

    pdf_text = _condense_large_text(pdf_text)

    prompt = f"""
{_language_instruction(language)}You are an AI tutor.

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

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.3)


# =======================================================================================

def generate_quiz(pdf_text: str, language: str | None = None):

    pdf_text = _condense_large_text(pdf_text)

    prompt = f"""
{_language_instruction(language)}You are an AI tutor.

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

    content = chat_completion([{"role": "user", "content": prompt}], temperature=0.3)

    return json.loads(content)


# ======================================================================

def generate_study_notes(pdf_text: str, language: str | None = None):

    pdf_text = _condense_large_text(pdf_text)

    prompt = f"""
{_language_instruction(language)}You are an expert AI tutor.

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

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)


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

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
