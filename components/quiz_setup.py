import streamlit as st

from utils.llm import generate_quiz
from utils.theme import animated_loader

_SETUP_CSS = """
<style>
@keyframes qSlideIn {
    from { opacity: 0; transform: translateY(16px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
.quiz-setup-slide {
    background: var(--paper-raised, #FFFFFF);
    border: 1px solid #E4E0D4;
    border-radius: 16px;
    padding: 2rem 2.2rem 1.6rem 2.2rem;
    max-width: 640px;
    margin: 1rem auto 0 auto;
    animation: qSlideIn 0.4s cubic-bezier(0.22, 1, 0.36, 1);
    box-shadow: 0 6px 24px rgba(27, 42, 74, 0.06);
}
.quiz-setup-eyebrow {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #2F6F4E;
    margin-bottom: 0.3rem;
}
.quiz-setup-title {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.7rem;
    font-weight: 600;
    color: #1B2A4A;
    margin: 0 0 0.3rem 0;
}
.quiz-setup-sub {
    color: #41507A;
    font-size: 0.94rem;
    margin-bottom: 1.5rem;
}
.quiz-setup-label {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #41507A;
    margin: 1.1rem 0 0.5rem 0;
}
.quiz-setup-hint {
    color: #6B6455;
    font-size: 0.78rem;
    margin: -0.3rem 0 0.4rem 0;
}
.quiz-pill-row .stButton > button {
    border-radius: 999px !important;
    border: 1px solid #E4E0D4 !important;
    background: #FAFAF7 !important;
    color: #1B2A4A !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 0.2rem !important;
    transition: transform 0.12s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.quiz-pill-row .stButton > button:hover:not(:disabled) {
    border-color: #2F6F4E !important;
    transform: translateY(-1px);
}
.quiz-pill-row .stButton > button[kind="primary"] {
    background: #2F6F4E !important;
    border-color: #2F6F4E !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
.quiz-setup-actions .stButton > button[kind="primary"] {
    animation: qPulseReady 2.2s ease-in-out infinite;
}
@keyframes qPulseReady {
    0%, 100% { box-shadow: 0 0 0 0 rgba(47, 111, 78, 0.0); }
    50% { box-shadow: 0 0 0 6px rgba(47, 111, 78, 0.10); }
}
</style>
"""

_QUESTION_COUNTS = [5, 10, 15, 20]

_TIMER_MODES = [
    ("⏱ Per question", "per_question"),
    ("⏳ Whole quiz", "total"),
]

_TIME_OPTIONS = [
    ("No limit", 0),
    ("15s / question", 15),
    ("30s / question", 30),
    ("45s / question", 45),
    ("60s / question", 60),
]

# Whole-quiz timer, optional, capped at 2 hours (120 minutes) as requested.
_TOTAL_TIME_OPTIONS = [
    ("No limit", 0),
    ("15 min", 15),
    ("30 min", 30),
    ("45 min", 45),
    ("60 min", 60),
    ("90 min", 90),
    ("120 min", 120),
]


def render_quiz_setup():
    st.markdown(_SETUP_CSS, unsafe_allow_html=True)

    # Defensive defaults, same reasoning as in quiz.py.
    st.session_state.setdefault("quiz_timer_mode", "per_question")
    st.session_state.setdefault("quiz_total_minutes", 0)
    st.session_state.setdefault("quiz_total_time_limit", 0)
    st.session_state.setdefault("quiz_flagged", {})
    st.session_state.setdefault("quiz_visited", {})
    st.session_state.setdefault("quiz_start_time", None)

    st.markdown('<div class="quiz-setup-slide">', unsafe_allow_html=True)
    st.markdown('<div class="quiz-setup-eyebrow">Quiz · Setup</div>', unsafe_allow_html=True)
    st.markdown('<div class="quiz-setup-title">Set up your quiz</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="quiz-setup-sub">Choose how many questions, whether you want a timer '
        'per question or for the whole attempt, then start whenever you\'re ready.</div>',
        unsafe_allow_html=True,
    )

    # ---- Number of questions ----
    st.markdown('<div class="quiz-setup-label">Number of questions</div>', unsafe_allow_html=True)
    st.markdown('<div class="quiz-pill-row">', unsafe_allow_html=True)
    cols = st.columns(len(_QUESTION_COUNTS))
    for col, count in zip(cols, _QUESTION_COUNTS):
        with col:
            is_selected = st.session_state.quiz_num_questions == count
            if st.button(
                f"{count}",
                key=f"qcount_{count}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.quiz_num_questions = count
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Timer mode: per-question (existing) or whole-quiz (new) ----
    st.markdown('<div class="quiz-setup-label">Timer</div>', unsafe_allow_html=True)
    st.markdown('<div class="quiz-setup-hint">Optional — pick a limit per question, one limit for the '
                'entire quiz (up to 2 hours), or leave both at "No limit".</div>', unsafe_allow_html=True)
    st.markdown('<div class="quiz-pill-row">', unsafe_allow_html=True)
    cols = st.columns(len(_TIMER_MODES))
    for col, (label, mode) in zip(cols, _TIMER_MODES):
        with col:
            is_selected = st.session_state.quiz_timer_mode == mode
            if st.button(
                label,
                key=f"qtimermode_{mode}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.quiz_timer_mode = mode
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.quiz_timer_mode == "per_question":
        st.markdown('<div class="quiz-setup-label">Time per question</div>', unsafe_allow_html=True)
        st.markdown('<div class="quiz-pill-row">', unsafe_allow_html=True)
        cols = st.columns(len(_TIME_OPTIONS))
        for col, (label, seconds) in zip(cols, _TIME_OPTIONS):
            with col:
                is_selected = st.session_state.quiz_time_per_question == seconds
                if st.button(
                    label,
                    key=f"qtime_{seconds}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.quiz_time_per_question = seconds
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="quiz-setup-label">Total time for the quiz</div>', unsafe_allow_html=True)
        st.markdown('<div class="quiz-pill-row">', unsafe_allow_html=True)
        cols = st.columns(len(_TOTAL_TIME_OPTIONS))
        for col, (label, minutes) in zip(cols, _TOTAL_TIME_OPTIONS):
            with col:
                is_selected = st.session_state.quiz_total_minutes == minutes
                if st.button(
                    label,
                    key=f"qtotalmin_{minutes}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.quiz_total_minutes = minutes
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="quiz-setup-hint">The countdown starts when the quiz begins and keeps running '
            'no matter which question you\'re on — it auto-submits at zero.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="quiz-setup-actions">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("✕ Cancel", use_container_width=True):
            st.session_state.quiz_stage = None
            st.rerun()
    with col2:
        if st.button("🚀 Start quiz", use_container_width=True, type="primary"):
            loader = st.empty()
            loader.markdown(
                animated_loader(
                    ["Reading your document", "Identifying key concepts", "Drafting questions", "Finalizing quiz"]
                ),
                unsafe_allow_html=True,
            )
            try:
                quiz = generate_quiz(
                    st.session_state.pdf_text,
                    language=st.session_state.document_language,
                    num_questions=st.session_state.quiz_num_questions,
                )
            except Exception as e:
                loader.empty()
                st.error(f"Groq Error:\n\n{e}")
                st.stop()
            loader.empty()

            st.session_state.quiz = quiz
            st.session_state.quiz_stage = "active"
            st.session_state.current_question = 0
            st.session_state.quiz_answers = {}
            st.session_state.quiz_score = 0
            st.session_state.quiz_submitted = False
            st.session_state.review_mode = False
            st.session_state.quiz_question_start_time = None

            # Reset per-attempt tracking for the palette + timers.
            st.session_state.quiz_flagged = {}
            st.session_state.quiz_visited = {0: True}
            st.session_state.quiz_start_time = None
            st.session_state.quiz_total_time_limit = (
                st.session_state.quiz_total_minutes * 60
                if st.session_state.quiz_timer_mode == "total"
                else 0
            )

            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
