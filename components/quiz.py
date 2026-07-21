import time

import streamlit as st
from streamlit.components.v1 import html as components_html

_QUIZ_CSS = """
<style>
@keyframes qFadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes qPopIn {
    0%   { opacity: 0; transform: scale(0.94); }
    100% { opacity: 1; transform: scale(1); }
}
.quiz-card {
    animation: qFadeInUp 0.35s ease-out;
}
.quiz-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.2rem;
}
.quiz-exit-note {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    color: #41507A;
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
    animation: qPopIn 0.2s ease-out;
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
.quiz-result-burst {
    text-align: center;
    font-size: 2.1rem;
    animation: qPopIn 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    margin-bottom: 0.2rem;
}
</style>
"""

# Class Streamlit auto-assigns to a keyed element's wrapper is
# "st-key-<key>" — used here to hide the auto-advance buttons without
# touching every other button on the page.
_HIDE_AUTOADVANCE_CSS = """
<style>
div[class*="st-key-auto_advance_"] { display: none !important; }
</style>
"""


def render_quiz():
    if st.session_state.get("quiz_stage") != "active" or not st.session_state.get("quiz"):
        return

    st.markdown(_QUIZ_CSS, unsafe_allow_html=True)
    st.markdown(_HIDE_AUTOADVANCE_CSS, unsafe_allow_html=True)

    quiz = st.session_state.quiz
    current = st.session_state.current_question
    q = quiz[current]
    total = len(quiz)
    progress_pct = int(((current + 1) / total) * 100)
    time_limit = st.session_state.get("quiz_time_per_question", 0)

    st.markdown('<div class="quiz-topbar">', unsafe_allow_html=True)
    col_a, col_b = st.columns([5, 1])
    with col_a:
        st.markdown('<div class="section-label">❓ Interactive quiz</div>', unsafe_allow_html=True)
    with col_b:
        if st.button("✕ Exit", key="quiz_exit", use_container_width=True):
            _exit_quiz()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="quiz-progress-label">QUESTION {current + 1} OF {total}</div>'
        f'<div class="quiz-progress-track"><div class="quiz-progress-fill" style="width:{progress_pct}%;"></div></div>',
        unsafe_allow_html=True,
    )

    if time_limit and not st.session_state.quiz_submitted:
        timed_out = _render_timer(current, time_limit)
        if timed_out:
            _advance_or_submit(current, total)
            st.rerun()

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

    # Hidden trigger the timer clicks when time runs out on this question.
    if time_limit and not st.session_state.quiz_submitted:
        if st.button(f"TIMEUP_{current}", key=f"auto_advance_{current}"):
            _advance_or_submit(current, total)
            st.rerun()

    col1, col2 = st.columns(2)

    with col1:
        if current > 0:
            if st.button("⬅ Previous", use_container_width=True):
                st.session_state.current_question -= 1
                st.session_state.quiz_question_start_time = None
                st.rerun()

    with col2:
        if current < total - 1:
            if st.button("Next ➡", use_container_width=True, type="primary"):
                st.session_state.current_question += 1
                st.session_state.quiz_question_start_time = None
                st.rerun()
        else:
            if st.button("✅ Submit quiz", use_container_width=True, type="primary"):
                _score_quiz()
                st.rerun()

    if st.session_state.quiz_submitted:
        _render_results()

    if st.session_state.review_mode:
        _render_review()


def _advance_or_submit(current, total):
    """Called when a question's timer runs out: move on, or submit on the last one."""
    if current < total - 1:
        st.session_state.current_question += 1
        st.session_state.quiz_question_start_time = None
    else:
        _score_quiz()


def _exit_quiz():
    st.session_state.quiz_stage = None
    st.session_state.quiz = None
    st.session_state.quiz_answers = {}
    st.session_state.quiz_score = 0
    st.session_state.quiz_submitted = False
    st.session_state.review_mode = False
    st.session_state.current_question = 0
    st.session_state.quiz_question_start_time = None


def _render_timer(current, time_limit):
    """Renders an animated countdown for the current question. Returns True
    once it detects time has already fully elapsed server-side (belt-and-
    braces alongside the JS-driven auto-advance click)."""
    start = st.session_state.get("quiz_question_start_time")
    if start is None:
        start = time.time()
        st.session_state.quiz_question_start_time = start

    elapsed = time.time() - start
    remaining = max(0.0, time_limit - elapsed)

    if remaining <= 0:
        return True

    pct = remaining / time_limit

    components_html(
        f"""
        <div id="qt-wrap" style="font-family: 'IBM Plex Mono', ui-monospace, monospace;">
          <div style="display:flex; align-items:center; gap:0.6rem;">
            <div style="flex:1; height:8px; background:#F1EFE7; border-radius:6px; overflow:hidden;">
              <div id="qt-bar" style="height:100%; border-radius:6px; width:{pct * 100:.2f}%;
                   background: linear-gradient(90deg, #2F6F4E, #B8860B); transition: width 0.2s linear, background-color 0.3s ease;"></div>
            </div>
            <div id="qt-label" style="font-size:0.78rem; color:#41507A; min-width:2.4em; text-align:right;">{int(remaining)}s</div>
          </div>
        </div>
        <script>
        (function() {{
            let remaining = {remaining};
            const total = {time_limit};
            const bar = document.getElementById('qt-bar');
            const label = document.getElementById('qt-label');

            function paint() {{
                const pct = Math.max(0, remaining / total) * 100;
                bar.style.width = pct + '%';
                label.textContent = Math.max(0, Math.ceil(remaining)) + 's';
                if (remaining <= total * 0.25) {{
                    bar.style.background = '#A3402A';
                }} else if (remaining <= total * 0.5) {{
                    bar.style.background = 'linear-gradient(90deg, #B8860B, #A3402A)';
                }}
            }}

            paint();
            const interval = setInterval(function() {{
                remaining -= 0.2;
                if (remaining <= 0) {{
                    remaining = 0;
                    paint();
                    clearInterval(interval);
                    try {{
                        const btns = window.parent.document.querySelectorAll('button');
                        for (const b of btns) {{
                            if (b.innerText && b.innerText.indexOf('TIMEUP_{current}') !== -1) {{
                                b.click();
                                break;
                            }}
                        }}
                    }} catch (e) {{}}
                    return;
                }}
                paint();
            }}, 200);
        }})();
        </script>
        """,
        height=32,
    )
    return False


def _score_quiz():
    quiz = st.session_state.quiz
    score = 0

    for i, q in enumerate(quiz):
        selected_letter = st.session_state.quiz_answers.get(i)
        if selected_letter and selected_letter == q["answer"]:
            score += 1

    st.session_state.quiz_score = score
    st.session_state.quiz_submitted = True
    st.session_state.quiz_question_start_time = None


def _render_results():
    quiz = st.session_state.quiz
    total = len(quiz)
    score = st.session_state.quiz_score
    percentage = (score / total) * 100

    st.markdown('<div class="quiz-card">', unsafe_allow_html=True)

    if percentage >= 90:
        st.markdown('<div class="quiz-result-burst">🎉🏆🎉</div>', unsafe_allow_html=True)
    elif percentage >= 75:
        st.markdown('<div class="quiz-result-burst">🎉</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="quiz-result-burst">📘</div>', unsafe_allow_html=True)

    st.markdown("### Quiz complete")
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

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📖 Review answers", use_container_width=True):
            st.session_state.review_mode = True
            st.rerun()
    with col2:
        if st.button("🔁 New quiz", use_container_width=True):
            _exit_quiz()
            st.session_state.quiz_stage = "setup"
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
        else:
            st.markdown(f"Your answer: **(skipped)** &nbsp;·&nbsp; Correct: **{q['answer']}**")
            st.error("Not answered")

        st.info(q["explanation"])
        st.markdown("</div>", unsafe_allow_html=True)
