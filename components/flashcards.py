import re
import html

import streamlit as st

_QA_PATTERN = re.compile(
    r"\*\*Q:\*\*\s*(.*?)\s*\*\*A:\*\*\s*(.*?)(?=(?:\n\s*---)|(?:\n\s*##\s*Flashcard)|\Z)",
    re.DOTALL,
)


def parse_flashcards(markdown_text: str):
    """Turn the LLM's '## Flashcard N / **Q:** / **A:**' markdown into a
    list of {"question": ..., "answer": ...} dicts."""
    cards = []

    for match in _QA_PATTERN.finditer(markdown_text):
        question = match.group(1).strip()
        answer = match.group(2).strip()
        if question and answer:
            cards.append({"question": question, "answer": answer})

    return cards


def render_flashcards(cards, key_prefix="fc"):
    """Render flip cards. Pure CSS (checkbox hack) so no Streamlit rerun
    is needed to flip — clicking is instant and doesn't reset scroll
    position or other widget state."""

    if not cards:
        st.warning("Couldn't parse flashcards from the response.")
        return

    cards_html = ""

    for i, card in enumerate(cards):
        card_id = f"{key_prefix}-{i}"
        q = html.escape(card["question"]).replace("\n", "<br>")
        a = html.escape(card["answer"]).replace("\n", "<br>")

        cards_html += f"""
        <div class="flip-card">
            <input type="checkbox" id="{card_id}" class="flip-toggle" />
            <label for="{card_id}" class="flip-card-inner">
                <div class="flip-card-face flip-card-front">
                    <div class="flash-q">Question {i + 1}</div>
                    <div class="flip-card-text">{q}</div>
                    <div class="flip-hint">Tap to reveal answer</div>
                </div>
                <div class="flip-card-face flip-card-back">
                    <div class="flash-a">Answer</div>
                    <div class="flip-card-text">{a}</div>
                    <div class="flip-hint">Tap to see question</div>
                </div>
            </label>
        </div>
        """

    st.markdown(
        f"""
        <style>
        .flip-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 1rem;
            margin: 0.6rem 0 1rem 0;
        }}
        .flip-card {{
            perspective: 1200px;
            height: 190px;
        }}
        .flip-toggle {{
            display: none;
        }}
        .flip-card-inner {{
            position: relative;
            width: 100%;
            height: 100%;
            display: block;
            cursor: pointer;
            transition: transform 0.5s;
            transform-style: preserve-3d;
        }}
        .flip-toggle:checked ~ .flip-card-inner {{
            transform: rotateY(180deg);
        }}
        .flip-card-face {{
            position: absolute;
            inset: 0;
            backface-visibility: hidden;
            border-radius: 12px;
            border: 1px solid #E4E0D4;
            padding: 1rem 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.35rem;
            box-shadow: 1px 2px 0 rgba(27, 42, 74, 0.05);
        }}
        .flip-card-front {{
            background: #FFFFFF;
        }}
        .flip-card-back {{
            background: #EFF3EE;
            transform: rotateY(180deg);
        }}
        .flash-q {{
            font-family: 'IBM Plex Mono', ui-monospace, monospace;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #B8860B;
        }}
        .flash-a {{
            font-family: 'IBM Plex Mono', ui-monospace, monospace;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #2F6F4E;
        }}
        .flip-card-text {{
            font-size: 0.92rem;
            color: #1B2A4A;
            line-height: 1.4;
            overflow-y: auto;
            max-height: 90px;
        }}
        .flip-hint {{
            font-size: 0.68rem;
            color: #6B7280;
            margin-top: auto;
        }}
        </style>
        <div class="flip-grid">
            {cards_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
