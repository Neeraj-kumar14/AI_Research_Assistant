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

from utils.language_detector import detect_language

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

def _question_language_instruction(question: str) -> str:
    """Builds a hard, non-negotiable language instruction based on the
    QUESTION itself, detected deterministically with langdetect — not left
    to the model's own judgment. This is what actually fixes "always
    answers in Hindi": previously the model only had a soft, wordy rule
    to follow, and it kept getting pulled toward the PDF's language
    (often Hindi) since the retrieved context sat right there in the
    prompt. Pre-detecting the question's language and stating it as a
    fact up front — before the model ever sees the context — makes the
    answer language depend on what the user typed, not on the document.
    """
    q = (question or "").strip()

    # Too short to detect reliably (e.g. "hi", "ok") — fall back to
    # letting the model infer it itself rather than risk a wrong guess.
    if len(q) < 2:
        return (
            "LANGUAGE RULE: Detect the language of the CURRENT QUESTION below "
            "yourself, and write your entire answer in that exact language — "
            "even if the Context/PDF or conversation history is in a "
            "different language. Do not default to Hindi or English just "
            "because the document is in that language.\n\n"
        )

    try:
        detected = detect_language(q)
    except Exception:
        detected = "Unknown"

    if not detected or detected == "Unknown":
        return (
            "LANGUAGE RULE: Detect the language of the CURRENT QUESTION below "
            "yourself, and write your entire answer in that exact language — "
            "even if the Context/PDF or conversation history is in a "
            "different language. Do not default to Hindi or English just "
            "because the document is in that language.\n\n"
        )

    return (
        f"LANGUAGE RULE: The CURRENT QUESTION below is written in {detected}. "
        f"You MUST write your ENTIRE answer in {detected}, using its native "
        f"script. This applies no matter what language the Context/PDF or "
        f"conversation history is in below — do not switch to the document's "
        f"language, do not switch to Hindi, do not switch to English, unless "
        f"{detected} literally is Hindi or English. Do not mix languages. "
        f"Do not translate the answer afterward.\n\n"
    )


def ask_groq(context: str, question: str, chat_history=None):
    history = ""

    if chat_history:
        for msg in chat_history[-6:]:
            role = msg["role"].capitalize()
            history += f"{role}: {msg['content']}\n"

    prompt = f"""
{_question_language_instruction(question)}You are an AI Research Assistant.

Rules:
1. Answer ONLY from the provided context.
2. Never use your own knowledge.
3. If the answer is not available in the context, reply with that same
   message translated into the question's language (see LANGUAGE RULE
   above), meaning: "I couldn't find this information in the uploaded PDF."
4. Follow the LANGUAGE RULE above no matter what language the context,
   the PDF, or the conversation history are in, unless the user
   explicitly asks for a translation into another language.

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

def generate_flashcards(
    pdf_text: str,
    language: str | None = None,
    num_cards: int = 10,
    difficulty: str = "Medium",
    focus: str | None = None,
):

    pdf_text = _condense_large_text(pdf_text)
    num_cards = max(3, min(int(num_cards), 50))

    if difficulty == "Mixed":
        difficulty_instruction = (
            "Vary the difficulty across the set: roughly a third easy (direct recall), "
            "a third medium (requires connecting two facts), a third hard (requires "
            "inference or synthesis across the document)."
        )
    else:
        difficulty_instruction = f"Target difficulty: {difficulty}. Keep every question at this level."

    focus_instruction = f"\nFocus especially on this topic/section if present in the PDF: {focus}\n" if focus else ""

    prompt = f"""
{_language_instruction(language)}You are an AI tutor.

Generate exactly {num_cards} high-quality flashcards from the PDF.

{difficulty_instruction}
{focus_instruction}
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
- Produce exactly {num_cards} flashcards, no more, no fewer.

PDF:

{pdf_text}
"""

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.3)


# =======================================================================================

def generate_quiz(pdf_text: str, language: str | None = None, num_questions: int = 10, difficulty: str = "Medium"):

    pdf_text = _condense_large_text(pdf_text)
    num_questions = max(1, min(int(num_questions), 25))

    if difficulty == "Mixed":
        difficulty_instruction = (
            "Vary the difficulty across the set: roughly a third easy (direct recall), "
            "a third medium (requires connecting two facts), a third hard (requires "
            "inference or synthesis across the document)."
        )
    else:
        difficulty_instruction = f"Target difficulty: {difficulty}. Keep every question at this level."

    prompt = f"""
{_language_instruction(language)}You are an AI tutor.

Generate exactly {num_questions} multiple-choice questions from the PDF.

{difficulty_instruction}

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

# Every possible notes section, in default order. Keys are what the
# setup UI toggles on/off; values are the exact Markdown heading the
# model is told to use, so the requested sections and the model's
# output headings always match up.
NOTE_SECTIONS = [
    ("overview", "## Overview"),
    ("concepts", "## Important Concepts"),
    ("definitions", "## Definitions"),
    ("key_points", "## Key Points"),
    ("examples", "## Examples"),
    ("advantages", "## Advantages"),
    ("disadvantages", "## Disadvantages"),
    ("applications", "## Applications"),
    ("interview_questions", "## Interview Questions"),
    ("common_mistakes", "## Common Mistakes"),
    ("quick_revision", "## Quick Revision"),
]

_STYLE_INSTRUCTIONS = {
    "Concise": (
        "STYLE: Be concise. Use short bullet points only — no long "
        "paragraphs. Every bullet should be one line where possible. Cut "
        "anything that isn't essential for a quick review pass."
    ),
    "Detailed": (
        "STYLE: Be thorough. Use clear explanatory prose plus bullet "
        "points where useful. Cover the reasoning behind concepts, not "
        "just the facts, so someone with no prior context can follow along."
    ),
    "Exam-focused": (
        "STYLE: Optimize for exam preparation. Prioritize the facts, "
        "definitions, and distinctions most likely to be tested. Under "
        "each relevant section, call out likely exam angles or common "
        "trick points. Keep 'Common Mistakes', 'Interview Questions', and "
        "'Quick Revision' especially sharp and test-oriented."
    ),
}


def generate_study_notes(
    pdf_text: str,
    language: str | None = None,
    style: str = "Detailed",
    sections: list[str] | None = None,
    focus: str | None = None,
):
    pdf_text = _condense_large_text(pdf_text)

    # No selection (or None, for backward compatibility with older
    # callers) means "everything" — the original fixed behavior.
    selected_keys = set(sections) if sections else {key for key, _ in NOTE_SECTIONS}
    headings = [heading for key, heading in NOTE_SECTIONS if key in selected_keys]
    if not headings:
        headings = [heading for _, heading in NOTE_SECTIONS]

    style_instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["Detailed"])
    focus_instruction = (
        f"\nFocus especially on this topic/section if present in the PDF: {focus}\n"
        if focus else ""
    )

    sections_block = "\n\n".join(headings)

    prompt = f"""
{_language_instruction(language)}You are an expert AI tutor.

Create high-quality study notes from the following PDF.

{style_instruction}
{focus_instruction}
Output format — use EXACTLY these headings, in this order, and no others:

# 📘 Study Notes

{sections_block}

Use proper markdown formatting (headings, **bold**, bullet lists).

PDF Content:

{pdf_text}
"""

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)


# ===========================================================================

def ask_groq_web(context: str, question: str):

    prompt = f"""
{_question_language_instruction(question)}You are an AI Research Assistant.

Answer the user's question ONLY using the web search results below.

Rules:
1. Do not make up information.
2. Use only the provided web context.
3. Give a clear answer.
4. Mention important details if available.
5. Follow the LANGUAGE RULE above no matter what language the web
   context is in, unless the user explicitly asks for a translation.

Web Context:

{context}

Question:

{question}
"""

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
