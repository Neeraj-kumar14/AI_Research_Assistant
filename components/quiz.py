import streamlit as st

_QUIZ_CSS = """
<style>
@keyframes qFadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.quiz-card {
    animation: qFadeInUp 0.35s ease-out;
}
.quiz-option-row .stButton > button {
    text-align: left;
    justify-content: flex-start;
    border-radius: 10px;
    border: 1px solid #E4E0D4;
    background: #FFFFFF;
    padding: 0.65rem 1rem;
    font-size: 0.92rem;
    transition: border-color 0.15s ease, background-color 0.15s ease, transform 0.1s ease;
}
.quiz-option-row .stButton > button:hover:not(:disabled) {
    border-color: #2F6F4E;
    transform: translateX(3px);
}
.quiz-option-row .stButton > button[kind="primary"] {
    background: #EFF3EE !important;
    border: 1px solid #2F6F4E !important;
    color: #1B2A4A !important;
    font-weight: 600 !important;
}
.quiz-progress-track {
    width: 100%;
    height: 8px;
    background: #F1EFE7;
    border-radius: 6px;
    overflow: hidden;
    margin: 0.35rem 0 0.9rem 0;
}
.quiz-progress-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #2F6F4E, #B8860B);
    transition: width 0.4s ease;
}
</style>
"""


def render_quiz():
    if not st.session_state.get("quiz"):
        return

    st.markdown(_QUIZ_CSS, unsafe_allow_html=True)

    quiz = st.session_state.quiz
    current = st.session_state.current_question
    q = quiz[current]
    total = len(quiz)
    progress_pct = int(((current + 1) / total) * 100)

    st.markdown('<div class="section-label">❓ Interactive quiz</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="quiz-progress-label">QUESTION {current + 1} OF {total}</div>'
        f'<div class="quiz-progress-track"><div class="quiz-progress-fill" style="width:{progress_pct}%;"></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
    st.markdown(f"**{q['question']}**")

    st.markdown('<div class="quiz-option-row">', unsafe_allow_html=True)
    # Keyed by letter (A/B/C/D), set at click-time below — not by
    # re-deriving the letter later via options.index(selected_text),
    # which would silently misattribute the answer if a quiz ever has
    # two identical option strings.
    selected_letter = st.session_state.quiz_answers.get(current)
    letters = ["A", "B", "C", "D"]

    for letter, option in zip(letters, q["options"]):
        is_selected = selected_letter == letter
        label = f"{'✓  ' if is_selected else ''}{letter}.  {option}"
        if st.button(
            label,
            key=f"quiz_{current}_{letter}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
            disabled=st.session_state.quiz_submitted,
        ):
            st.session_state.quiz_answers[current] = letter
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if current > 0:
            if st.button("⬅ Previous", use_container_width=True):
                st.session_state.current_question -= 1
                st.rerun()

    with col2:
        if current < total - 1:
            if st.button("Next ➡", use_container_width=True, type="primary"):
                st.session_state.current_question += 1
                st.rerun()
        else:
            if st.button("✅ Submit quiz", use_container_width=True, type="primary"):
                _score_quiz()
                st.rerun()

    if st.session_state.quiz_submitted:
        _render_results()

    if st.session_state.review_mode:
        _render_review()


def _score_quiz():
    quiz = st.session_state.quiz
    score = 0

    for i, q in enumerate(quiz):
        selected_letter = st.session_state.quiz_answers.get(i)
        if selected_letter and selected_letter == q["answer"]:
            score += 1

    st.session_state.quiz_score = score
    st.session_state.quiz_submitted = True


def _render_results():
    quiz = st.session_state.quiz
    total = len(quiz)
    score = st.session_state.quiz_score
    percentage = (score / total) * 100

    st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
    st.markdown("### 🏆 Quiz complete")
    st.markdown(f"**Score:** {score}/{total} &nbsp;·&nbsp; **{percentage:.1f}%**")
    st.markdown(
        f'<div class="quiz-progress-track"><div class="quiz-progress-fill" style="width:{percentage}%;"></div></div>',
        unsafe_allow_html=True,
    )

    if percentage >= 90:
        st.success("Excellent work.")
    elif percentage >= 75:
        st.success("Very good.")
    elif percentage >= 60:
        st.warning("Solid — a little more review will help.")
    else:
        st.error("Worth another pass through the material.")

    if st.button("📖 Review answers"):
        st.session_state.review_mode = True
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_review():
    quiz = st.session_state.quiz

    st.markdown('<div class="section-label">📖 Review</div>', unsafe_allow_html=True)

    for i, q in enumerate(quiz):
        st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
        st.markdown(f"**{i + 1}. {q['question']}**")

        selected_letter = st.session_state.quiz_answers.get(i)
        if selected_letter:
            st.markdown(f"Your answer: **{selected_letter}** &nbsp;·&nbsp; Correct: **{q['answer']}**")
            if selected_letter == q["answer"]:
                st.success("Correct")
            else:
                st.error("Incorrect")

        st.info(q["explanation"])
        st.markdown("</div>", unsafe_allow_html=True)
