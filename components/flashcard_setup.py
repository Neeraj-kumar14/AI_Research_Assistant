import streamlit as st

from utils.llm import generate_flashcards
from utils.theme import animated_loader
from components.flashcards import parse_flashcards

_SETUP_CSS = """
<style>
@keyframes fcSetupIn {
    from { opacity: 0; transform: translateY(16px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes fcCountPop {
    0%   { transform: scale(1); }
    40%  { transform: scale(1.18); }
    100% { transform: scale(1); }
}
.fc-setup-slide {
    animation: fcSetupIn 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.fc-setup-eyebrow {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #B8860B;
    margin-bottom: 0.3rem;
}
.fc-setup-sub {
    color: #41507A;
    font-size: 0.94rem;
    margin-bottom: 1.2rem;
}
.fc-setup-label {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #41507A;
    margin: 1.1rem 0 0.5rem 0;
}
.fc-count-display {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0.2rem 0 0.6rem 0;
}
.fc-count-number {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #1B2A4A;
    animation: fcCountPop 0.25s ease;
}
.fc-count-unit {
    font-size: 0.9rem;
    color: #6B7280;
}
.fc-pill-row .stButton > button {
    border-radius: 999px !important;
    border: 1px solid #E4E0D4 !important;
    background: #FAFAF7 !important;
    color: #1B2A4A !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 0.2rem !important;
    transition: transform 0.12s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.fc-pill-row .stButton > button:hover:not(:disabled) {
    border-color: #B8860B !important;
    transform: translateY(-1px);
}
.fc-pill-row .stButton > button[kind="primary"] {
    background: #B8860B !important;
    border-color: #B8860B !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
.fc-diff-row .stButton > button {
    border-radius: 999px !important;
    border: 1px solid #E4E0D4 !important;
    background: #FAFAF7 !important;
    color: #1B2A4A !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 0.2rem !important;
    transition: transform 0.12s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.fc-diff-row .stButton > button:hover:not(:disabled) {
    border-color: #2F6F4E !important;
    transform: translateY(-1px);
}
.fc-diff-row .stButton > button[kind="primary"] {
    background: #2F6F4E !important;
    border-color: #2F6F4E !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
.fc-setup-actions .stButton > button[kind="primary"] {
    animation: fcPulseReady 2.2s ease-in-out infinite;
}
@keyframes fcPulseReady {
    0%, 100% { box-shadow: 0 0 0 0 rgba(184, 134, 11, 0.0); }
    50% { box-shadow: 0 0 0 6px rgba(184, 134, 11, 0.12); }
}
</style>
"""

_QUICK_COUNTS = [5, 10, 15, 20, 30]
_DIFFICULTIES = ["Easy", "Medium", "Hard", "Mixed"]


def _setup_body():
    st.markdown(_SETUP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="fc-setup-slide">', unsafe_allow_html=True)
    st.markdown('<div class="fc-setup-eyebrow">Flashcards · Setup</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="fc-setup-sub">Pick how many cards, how tough they should be, '
        'and (optionally) a topic to focus on.</div>',
        unsafe_allow_html=True,
    )

    # ---- Card count -------------------------------------------------
    st.markdown('<div class="fc-setup-label">Number of cards</div>', unsafe_allow_html=True)
    st.markdown('<div class="fc-pill-row">', unsafe_allow_html=True)
    cols = st.columns(len(_QUICK_COUNTS))
    for col, count in zip(cols, _QUICK_COUNTS):
        with col:
            is_selected = st.session_state.flashcard_num == count
            if st.button(
                str(count),
                key=f"fccount_{count}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.flashcard_num = count
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="fc-count-display">'
        f'<span class="fc-count-number">{st.session_state.flashcard_num}</span>'
        f'<span class="fc-count-unit">cards - drag to fine-tune (3-50)</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.slider(
        "Number of cards",
        min_value=3,
        max_value=50,
        key="flashcard_num",
        label_visibility="collapsed",
    )

    # ---- Difficulty ---------------------------------------------------
    st.markdown('<div class="fc-setup-label">Difficulty</div>', unsafe_allow_html=True)
    st.markdown('<div class="fc-diff-row">', unsafe_allow_html=True)
    cols = st.columns(len(_DIFFICULTIES))
    for col, level in zip(cols, _DIFFICULTIES):
        with col:
            is_selected = st.session_state.flashcard_difficulty == level
            if st.button(
                level,
                key=f"fcdiff_{level}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.flashcard_difficulty = level
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Optional focus topic ------------------------------------------
    st.markdown('<div class="fc-setup-label">Focus on a topic (optional)</div>', unsafe_allow_html=True)
    st.text_input(
        "Focus topic",
        key="flashcard_focus",
        placeholder="e.g. Chapter 3, photosynthesis, key dates...",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Actions --------------------------------------------------------
    st.markdown('<div class="fc-setup-actions">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Cancel", use_container_width=True, key="fc_cancel"):
            st.session_state.flashcard_stage = None
            st.rerun()
    with col2:
        if st.button("Start deck", use_container_width=True, type="primary", key="fc_start"):
            loader = st.empty()
            loader.markdown(
                animated_loader(
                    ["Reading your document", "Pulling out key facts", "Writing questions", "Shuffling the deck"]
                ),
                unsafe_allow_html=True,
            )
            try:
                raw = generate_flashcards(
                    st.session_state.pdf_text,
                    language=st.session_state.document_language,
                    num_cards=st.session_state.flashcard_num,
                    difficulty=st.session_state.flashcard_difficulty,
                    focus=st.session_state.flashcard_focus.strip() or None,
                )
                cards = parse_flashcards(raw)
            except Exception as e:
                loader.empty()
                st.error(f"Groq Error:\n\n{e}")
                st.stop()
            loader.empty()

            if not cards:
                st.error("Couldn't parse flashcards from the response. Try again.")
                st.stop()

            st.session_state.flashcards = cards
            st.session_state.flashcard_order = list(range(len(cards)))
            st.session_state.flashcard_current = 0
            st.session_state.flashcard_known = {}
            st.session_state.flashcard_starred = {}
            st.session_state.flashcard_direction = "next"
            st.session_state.flashcard_view = "deck"
            st.session_state.flashcard_stage = "active"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


@st.dialog("Set up your flashcard deck", width="large")
def _flashcard_setup_dialog():
    _setup_body()


def render_flashcard_setup():
    """Opens the flashcard setup as a floating modal window (st.dialog)
    instead of an inline page section, so it visually pops up on top of
    whatever the user was doing."""
    _flashcard_setup_dialog()
