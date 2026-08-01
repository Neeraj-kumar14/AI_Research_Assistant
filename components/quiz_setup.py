import streamlit as st

from utils.llm import generate_quiz
from utils.errors import show_llm_error
from utils.theme import animated_loader

_SETUP_CSS = """
<style>
@keyframes qSlideIn {
    from { opacity: 0; transform: translateY(16px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
.quiz-setup-slide {
    background: var(--paper-raised, rgba(255,255,255,0.055));
    border: 1px solid rgba(255,255,255,0.14);
    backdrop-filter: blur(20px);
    border-radius: 16px;
    padding: 2rem 2.2rem 1.6rem 2.2rem;
    max-width: 640px;
    margin: 1rem auto 0 auto;
    animation: qSlideIn 0.4s cubic-bezier(0.22, 1, 0.36, 1);
    box-shadow: 0 20px 50px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.1);
}
.quiz-setup-eyebrow {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #22D3EE;
    margin-bottom: 0.3rem;
}
.quiz-setup-title {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.7rem;
    font-weight: 600;
    color: #EAF0FF;
    margin: 0 0 0.3rem 0;
}
.quiz-setup-sub {
    color: #9FB0D9;
    font-size: 0.94rem;
    margin-bottom: 1.5rem;
}
.quiz-setup-label {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9FB0D9;
    margin: 1.1rem 0 0.5rem 0;
}
.quiz-setup-hint {
    color: #9FB0D9;
    font-size: 0.78rem;
    margin: -0.3rem 0 0.4rem 0;
}
.quiz-pill-row .stButton > button {
    border-radius: 999px !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    background: rgba(255,255,255,0.045) !important;
    color: #EAF0FF !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 0.2rem !important;
    transition: transform 0.12s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.15s ease, background-color 0.15s ease;
}
.quiz-pill-row .stButton > button:hover:not(:disabled) {
    border-color: #22D3EE !important;
    transform: translateY(-1px);
}
.quiz-pill-row .stButton > button[kind="primary"] {
    background: linear-gradient(120deg, #22D3EE, #7C5CFF) !important;
    border-color: #22D3EE !important;
    color: #05060F !important;
    font-weight: 600 !important;
    animation: qPillPop 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes qPillPop {
    0%   { transform: scale(0.9); }
    60%  { transform: scale(1.06); }
    100% { transform: scale(1); }
}
.quiz-setup-actions .stButton > button[kind="primary"] {
    animation: qPulseReady 2.2s ease-in-out infinite;
}
@keyframes qPulseReady {
    0%, 100% { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.0); }
    50% { box-shadow: 0 0 0 6px rgba(34, 211, 238, 0.16); }
}
@media (prefers-reduced-motion: reduce) {
    .quiz-setup-actions .stButton > button[kind="primary"] { animation: none !important; }
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
        if st.button("✕ Cancel", use_container_width=True, key="quiz_setup_cancel"):
            st.session_state.quiz_stage = None
            st.rerun()
    with col2:
        if st.button("🚀 Start quiz", use_container_width=True, type="primary", key="quiz_setup_start"):
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
                show_llm_error(e, action="generate the quiz")
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
