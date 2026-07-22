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
# "st-key-<key>" — used here to hide the auto-advance / auto-submit
# trigger buttons without touching every other button on the page.
_HIDE_AUTOADVANCE_CSS = """
<style>
div[class*="st-key-auto_advance_"],
div[class*="st-key-auto_submit_quiz"] { display: none !important; }
</style>
"""

# Palette status codes — deliberately non-overlapping substrings so the
# `div[class*="st-key-palette_<code>_"]` selectors below can't accidentally
# also match a different status (e.g. "answered" is a substring of
# "answeredmarked", so codes like that are avoided).
_PALETTE_CSS = """
<style>
div[class*="st-key-palette_"] button {
    border-radius: 8px !important;
    padding: 0.3rem 0 !important;
    font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    border: 1px solid transparent !important;
    min-height: 2.1rem !important;
}
div[class*="st-key-palette_pnv_"] button {
    background: #F1EFE7 !important;
    color: #6B6455 !important;
    border-color: #E4E0D4 !important;
}
div[class*="st-key-palette_pvu_"] button {
    background: #FBE4DC !important;
    color: #A3402A !important;
    border-color: #E9B9A8 !important;
}
div[class*="st-key-palette_pans_"] button {
    background: #2F6F4E !important;
    color: #FFFFFF !important;
}
div[class*="st-key-palette_pflg_"] button {
    background: #7C4FA0 !important;
    color: #FFFFFF !important;
}
div[class*="st-key-palette_pafl_"] button {
    background: linear-gradient(135deg, #2F6F4E 50%, #7C4FA0 50%) !important;
    color: #FFFFFF !important;
}
div[class*="st-key-palette_"] button[kind="primary"] {
    outline: 2px solid #1B2A4A !important;
    outline-offset: 1px !important;
}
.quiz-legend-row {
    display: flex; flex-wrap: wrap; gap: 0.55rem;
    font-size: 0.68rem; font-family: 'IBM Plex Mono', ui-monospace, monospace;
    color: #41507A; margin: 0.4rem 0 0.7rem 0;
}
.quiz-legend-dot {
    display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 3px;
    margin-right: 0.3rem; vertical-align: middle;
}
</style>
"""


def render_quiz():
    if st.session_state.get("quiz_stage") != "active" or not st.session_state.get("quiz"):
        return

    # Defensive defaults — lets this file work even if app.py's session
    # defaults haven't been updated with these newer keys yet.
    st.session_state.setdefault("quiz_visited", {})
    st.session_state.setdefault("quiz_flagged", {})
    st.session_state.setdefault("quiz_timer_mode", "per_question")
    st.session_state.setdefault("quiz_total_time_limit", 0)
    st.session_state.setdefault("quiz_start_time", None)

    st.markdown(_QUIZ_CSS, unsafe_allow_html=True)
    st.markdown(_HIDE_AUTOADVANCE_CSS, unsafe_allow_html=True)

    quiz = st.session_state.quiz
    current = st.session_state.current_question
    q = quiz[current]
    total = len(quiz)
    progress_pct = int(((current + 1) / total) * 100)

    timer_mode = st.session_state.quiz_timer_mode
    time_limit = st.session_state.get("quiz_time_per_question", 0)
    total_limit = st.session_state.quiz_total_time_limit

    # Mark this question as visited — it never gets locked or disabled;
    # the palette in the sidebar lets you jump to any question at any time.
    st.session_state.quiz_visited[current] = True

    _render_question_palette()

    st.markdown('<div class="quiz-topbar">', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([4, 1.6, 1])
    with col_a:
        st.markdown('<div class="section-label">❓ Interactive quiz</div>', unsafe_allow_html=True)
    with col_b:
        is_flagged = st.session_state.quiz_flagged.get(current, False)
        flag_label = "🚩 Marked" if is_flagged else "🚩 Mark for review"
        if st.button(
            flag_label,
            key=f"flag_{current}",
            use_container_width=True,
            disabled=st.session_state.quiz_submitted,
        ):
            st.session_state.quiz_flagged[current] = not is_flagged
            st.rerun()
    with col_c:
        if st.button("✕ Exit", key="quiz_exit", use_container_width=True):
            _exit_quiz()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="quiz-progress-label">QUESTION {current + 1} OF {total}</div>'
        f'<div class="quiz-progress-track"><div class="quiz-progress-fill" style="width:{progress_pct}%;"></div></div>',
        unsafe_allow_html=True,
    )

    if timer_mode == "total" and total_limit and not st.session_state.quiz_submitted:
        timed_out = _render_total_timer(total_limit)
        if timed_out:
            _score_quiz()
            st.rerun()
    elif timer_mode == "per_question" and time_limit and not st.session_state.quiz_submitted:
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

    # Hidden trigger the timer clicks when time runs out.
    if timer_mode == "total" and total_limit and not st.session_state.quiz_submitted:
        if st.button("TOTAL_TIMEUP", key="auto_submit_quiz"):
            _score_quiz()
            st.rerun()
    elif timer_mode == "per_question" and time_limit and not st.session_state.quiz_submitted:
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


def _status_for(i, current, answers, flagged, visited):
    """Returns one of the non-overlapping palette status codes for
    question i: pnv (not visited), pvu (visited, unanswered),
    pans (answered), pflg (marked for review only), pafl (answered AND
    marked for review)."""
    is_answered = i in answers
    is_flagged = bool(flagged.get(i))
    is_visited = bool(visited.get(i)) or i == current

    if is_answered and is_flagged:
        return "pafl"
    if is_answered:
        return "pans"
    if is_flagged:
        return "pflg"
    if is_visited:
        return "pvu"
    return "pnv"


def _render_question_palette():
    """Sidebar question palette: jump to any question at any time, and see
    at a glance which ones are answered, visited-but-skipped, marked for
    review, or not opened yet. Nothing is ever locked or disabled."""
    quiz = st.session_state.quiz
    total = len(quiz)
    current = st.session_state.current_question
    answers = st.session_state.quiz_answers
    flagged = st.session_state.quiz_flagged
    visited = st.session_state.quiz_visited

    with st.sidebar:
        st.divider()
        st.markdown(
            '<div style=\'font-family:"Source Serif 4",serif;font-size:1.02rem;'
            'font-weight:600;color:#1B2A4A;margin-bottom:0.2rem;\'>🗂 Question palette</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_PALETTE_CSS, unsafe_allow_html=True)

        answered_ct = len(answers)
        flagged_ct = sum(1 for v in flagged.values() if v)
        st.caption(f"{answered_ct}/{total} answered · {flagged_ct} marked for review")

        st.markdown(
            '<div class="quiz-legend-row">'
            '<span><span class="quiz-legend-dot" style="background:#2F6F4E;"></span>Answered</span>'
            '<span><span class="quiz-legend-dot" style="background:#A3402A;"></span>Visited</span>'
            '<span><span class="quiz-legend-dot" style="background:#7C4FA0;"></span>Marked</span>'
            '<span><span class="quiz-legend-dot" style="background:#F1EFE7;border:1px solid #E4E0D4;"></span>New</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        cols_per_row = 5
        for row_start in range(0, total, cols_per_row):
            row_indices = list(range(row_start, min(row_start + cols_per_row, total)))
            cols = st.columns(len(row_indices))
            for col, i in zip(cols, row_indices):
                status = _status_for(i, current, answers, flagged, visited)
                with col:
                    if st.button(
                        str(i + 1),
                        key=f"palette_{status}_{i}",
                        use_container_width=True,
                        type="primary" if i == current else "secondary",
                    ):
                        st.session_state.current_question = i
                        st.session_state.quiz_question_start_time = None
                        st.rerun()

        if st.session_state.quiz_submitted:
            st.caption("Quiz submitted — palette is now just for review.")


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
    st.session_state.quiz_flagged = {}
    st.session_state.quiz_visited = {}
    st.session_state.quiz_start_time = None
    st.session_state.quiz_total_time_limit = 0


def _render_timer(current, time_limit):
    """Renders an animated countdown for the current question (per-question
    timer mode). Returns True once it detects time has already fully
    elapsed server-side (belt-and-braces alongside the JS-driven
    auto-advance click)."""
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


def _render_total_timer(total_seconds):
    """Renders an animated countdown for the WHOLE quiz (total timer mode).
    Unlike the per-question timer, this is anchored to quiz_start_time,
    which is set once when the quiz begins and never reset by navigation —
    so it keeps counting down no matter which question you're viewing or
    how many times you jump around via the palette."""
    start = st.session_state.get("quiz_start_time")
    if start is None:
        start = time.time()
        st.session_state.quiz_start_time = start

    elapsed = time.time() - start
    remaining = max(0.0, total_seconds - elapsed)

    if remaining <= 0:
        return True

    pct = remaining / total_seconds
    mins, secs = divmod(int(remaining), 60)
    label = f"{mins:02d}:{secs:02d}"

    components_html(
        f"""
        <div id="qtt-wrap" style="font-family: 'IBM Plex Mono', ui-monospace, monospace;">
          <div style="display:flex; align-items:center; gap:0.6rem;">
            <div style="font-size:0.72rem; color:#41507A; white-space:nowrap;">⏱ TOTAL TIME LEFT</div>
            <div style="flex:1; height:8px; background:#F1EFE7; border-radius:6px; overflow:hidden;">
              <div id="qtt-bar" style="height:100%; border-radius:6px; width:{pct * 100:.2f}%;
                   background: linear-gradient(90deg, #2F6F4E, #B8860B); transition: width 1s linear, background-color 0.3s ease;"></div>
            </div>
            <div id="qtt-label" style="font-size:0.85rem; font-weight:600; color:#1B2A4A; min-width:3.6em; text-align:right;">{label}</div>
          </div>
        </div>
        <script>
        (function() {{
            let remaining = {remaining};
            const total = {total_seconds};
            const bar = document.getElementById('qtt-bar');
            const label = document.getElementById('qtt-label');

            function fmt(s) {{
                s = Math.max(0, Math.ceil(s));
                const m = Math.floor(s / 60);
                const sec = s % 60;
                return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
            }}

            function paint() {{
                const pct = Math.max(0, remaining / total) * 100;
                bar.style.width = pct + '%';
                label.textContent = fmt(remaining);
                if (remaining <= total * 0.1) {{
                    bar.style.background = '#A3402A';
                }} else if (remaining <= total * 0.25) {{
                    bar.style.background = 'linear-gradient(90deg, #B8860B, #A3402A)';
                }}
            }}

            paint();
            const interval = setInterval(function() {{
                remaining -= 1;
                if (remaining <= 0) {{
                    remaining = 0;
                    paint();
                    clearInterval(interval);
                    try {{
                        const btns = window.parent.document.querySelectorAll('button');
                        for (const b of btns) {{
                            if (b.innerText && b.innerText.indexOf('TOTAL_TIMEUP') !== -1) {{
                                b.click();
                                break;
                            }}
                        }}
                    }} catch (e) {{}}
                    return;
                }}
                paint();
            }}, 1000);
        }})();
        </script>
        """,
        height=36,
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
