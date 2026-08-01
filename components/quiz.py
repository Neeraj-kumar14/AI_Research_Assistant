import json
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
@keyframes qGlowPulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,209,102,0.0); }
    50%      { box-shadow: 0 0 16px 3px rgba(255,209,102,0.32); }
}
.quiz-card {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 14px 34px rgba(0,0,0,0.35);
    animation: qFadeInUp 0.35s ease-out;
}
.quiz-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.2rem;
}
.quiz-exit-note {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    color: #9FB0D9;
}
.q-xp-bar-wrap {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.5rem 0 0.6rem 0;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.q-xp-badge {
    flex-shrink: 0;
    font-size: 0.74rem;
    font-weight: 700;
    color: #05060F;
    background: linear-gradient(120deg, #FFD166, #FF3EA5);
    padding: 0.22rem 0.6rem;
    border-radius: 999px;
    animation: qGlowPulse 2.4s ease-in-out infinite;
    white-space: nowrap;
}
.q-xp-track {
    flex: 1;
    height: 8px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    overflow: hidden;
}
.q-xp-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #22D3EE, #7C5CFF, #FF3EA5);
    transition: width 0.6s cubic-bezier(0.22,1,0.36,1);
}
.quiz-option-row .stButton > button {
    text-align: left;
    justify-content: flex-start;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.045);
    color: #EAF0FF;
    padding: 0.65rem 1rem;
    backdrop-filter: blur(10px);
    animation: qFadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
    transition: border-color 0.15s ease, background-color 0.15s ease, transform 0.12s ease, box-shadow 0.15s ease;
}
.quiz-option-row div[data-testid="column"]:nth-of-type(1) .stButton > button { animation-delay: 0.02s; }
.quiz-option-row div[data-testid="column"]:nth-of-type(2) .stButton > button { animation-delay: 0.07s; }
.quiz-option-row div[data-testid="column"]:nth-of-type(3) .stButton > button { animation-delay: 0.12s; }
.quiz-option-row div[data-testid="column"]:nth-of-type(4) .stButton > button { animation-delay: 0.17s; }
.quiz-option-row .stButton > button:hover:not(:disabled) {
    border-color: #22D3EE;
    transform: translateX(4px);
    box-shadow: 0 4px 16px rgba(34,211,238,0.15);
}
.quiz-option-row .stButton > button[kind="primary"] {
    background: linear-gradient(120deg, rgba(34,211,238,0.22), rgba(124,92,255,0.22)) !important;
    border: 1px solid #22D3EE !important;
    color: #EAF0FF !important;
    font-weight: 600 !important;
    animation: qPopIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    box-shadow: 0 0 16px rgba(34,211,238,0.25);
}
.quiz-progress-track {
    width: 100%;
    height: 8px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    overflow: hidden;
    margin: 0.35rem 0 0.9rem 0;
}
.quiz-progress-fill {
    position: relative;
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #7C5CFF, #22D3EE);
    transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    overflow: hidden;
}
.quiz-progress-fill::after {
    content: "";
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    animation: qShine 1.8s ease-in-out infinite;
}
@keyframes qShine {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
.quiz-result-burst {
    text-align: center;
    font-size: 2.3rem;
    animation: qPopIn 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    margin-bottom: 0.2rem;
}
@media (prefers-reduced-motion: reduce) {
    .quiz-progress-fill::after { animation: none !important; }
    .q-xp-badge { animation: none !important; }
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
div[class*="st-key-palette_"] .stButton > button {
    border-radius: 8px !important;
    padding: 0.3rem 0 !important;
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    border: 1px solid transparent !important;
    min-height: 2.1rem !important;
    transition: transform 0.14s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease, background-color 0.2s ease !important;
    animation: qPopIn 0.25s cubic-bezier(0.22, 1, 0.36, 1) both;
}
div[class*="st-key-palette_"] .stButton > button:hover:not(:disabled) {
    transform: translateY(-2px) scale(1.05) !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.4) !important;
}
/* NOTE: these status rules must out-specificity theme.py's global
   `.stButton > button[kind="secondary"]` rule (specificity 0,2,1) or the
   generic gray secondary-button style silently wins and every status
   (other than the current, primary-styled question) renders identically.
   Including ".stButton" here raises us to 0,2,2 so our color always wins. */
div[class*="st-key-palette_pnv_"] .stButton > button {
    background: rgba(255,255,255,0.05) !important;
    color: #9FB0D9 !important;
    border-color: rgba(255,255,255,0.14) !important;
}
div[class*="st-key-palette_pvu_"] .stButton > button {
    background: rgba(255,92,122,0.38) !important;
    color: #FFE1E7 !important;
    border-color: #FF5C7A !important;
}
div[class*="st-key-palette_pans_"] .stButton > button {
    background: linear-gradient(120deg, #22D3EE, #3DDC97) !important;
    color: #05060F !important;
    border-color: transparent !important;
}
div[class*="st-key-palette_pflg_"] .stButton > button {
    background: #7C5CFF !important;
    color: #FFFFFF !important;
    border-color: transparent !important;
}
div[class*="st-key-palette_pafl_"] .stButton > button {
    background: linear-gradient(135deg, #22D3EE 50%, #7C5CFF 50%) !important;
    color: #FFFFFF !important;
    border-color: transparent !important;
}
div[class*="st-key-palette_"] .stButton > button[kind="primary"] {
    outline: 2px solid #EAF0FF !important;
    outline-offset: 1px !important;
    animation: qPopIn 0.25s cubic-bezier(0.22, 1, 0.36, 1) both, palettePulse 2s ease-in-out infinite !important;
}
@keyframes palettePulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(234, 240, 255, 0.0); }
    50%      { box-shadow: 0 0 0 4px rgba(234, 240, 255, 0.16); }
}
.quiz-legend-row {
    display: flex; flex-wrap: wrap; gap: 0.55rem;
    font-size: 0.68rem; font-family: 'JetBrains Mono', ui-monospace, monospace;
    color: #9FB0D9; margin: 0.4rem 0 0.7rem 0;
}
.quiz-legend-dot {
    display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 3px;
    margin-right: 0.3rem; vertical-align: middle;
    transition: transform 0.2s ease;
}
@media (prefers-reduced-motion: reduce) {
    div[class*="st-key-palette_"] button[kind="primary"] { animation: none !important; }
}
</style>
"""


# ---- Gamification: shared sound / confetti / toast effect layer ----------

def _xp_for_level(level: int) -> int:
    total = 0
    for lv in range(1, level):
        total += 100 + (lv - 1) * 20
    return total


def _level_for_xp(xp: int) -> int:
    level = 1
    while xp >= _xp_for_level(level + 1):
        level += 1
    return level


_COLORS_JS = "['#22D3EE','#7C5CFF','#FF3EA5','#FFD166','#3DDC97']"


def _effect_script(effect):
    """Best-effort synthesized sound (Web Audio, no audio files) + a
    floating toast + an optional confetti burst, injected into the
    parent document so they aren't clipped by the component iframe."""
    if not effect:
        return ""

    sound = effect.get("sound")
    toast = effect.get("toast")
    confetti = effect.get("confetti")
    big = effect.get("big")

    sound_js = ""
    if sound == "pop":
        sound_js = "tone(760,0.06,'triangle',0,0.08);"
    elif sound == "fanfare":
        sound_js = (
            "tone(523,0.12,'triangle',0,0.1);tone(659,0.12,'triangle',0.12,0.1);"
            "tone(784,0.12,'triangle',0.24,0.1);tone(1046,0.3,'triangle',0.36,0.12);"
        )
    elif sound == "soft":
        sound_js = "tone(300,0.18,'sine',0,0.08);tone(240,0.2,'sine',0.1,0.07);"

    confetti_js = f"confettiBurst({320 if big else 90}, {_COLORS_JS}, {'true' if big else 'false'});" if confetti else ""
    toast_js = f"showToast({json.dumps(toast)});" if toast else ""

    return f"""
    <script>
    (function() {{
        function getCtx() {{
            const w = window.parent;
            try {{
                if (!w.__fcAudio) w.__fcAudio = new (w.AudioContext || w.webkitAudioContext)();
                if (w.__fcAudio.state === 'suspended') w.__fcAudio.resume().catch(function(){{}});
                return w.__fcAudio;
            }} catch (e) {{ return null; }}
        }}
        function tone(freq, dur, type, delay, vol) {{
            const ctx = getCtx(); if (!ctx) return;
            const t0 = ctx.currentTime + (delay || 0);
            const osc = ctx.createOscillator(); const gain = ctx.createGain();
            osc.type = type || 'sine'; osc.frequency.setValueAtTime(freq, t0);
            gain.gain.setValueAtTime(0, t0);
            gain.gain.linearRampToValueAtTime(vol || 0.1, t0 + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
            osc.connect(gain); gain.connect(ctx.destination);
            osc.start(t0); osc.stop(t0 + dur + 0.03);
        }}
        function confettiBurst(n, colors, big) {{
            const doc = window.parent.document;
            const canvas = doc.createElement('canvas');
            canvas.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:99999;';
            canvas.width = doc.documentElement.clientWidth;
            canvas.height = doc.documentElement.clientHeight;
            doc.body.appendChild(canvas);
            const ctx2 = canvas.getContext('2d');
            const particles = [];
            const cx = canvas.width / 2, cy = big ? canvas.height * 0.25 : canvas.height * 0.3;
            for (let i = 0; i < n; i++) {{
                particles.push({{
                    x: big ? Math.random() * canvas.width : cx + (Math.random() - 0.5) * 200,
                    y: big ? -20 : cy,
                    vx: (Math.random() - 0.5) * (big ? 4 : 7),
                    vy: big ? Math.random() * 2 + 1 : -(Math.random() * 6 + 4),
                    size: Math.random() * 6 + 4,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    rot: Math.random() * 360,
                    vr: (Math.random() - 0.5) * 12
                }});
            }}
            let frame = 0;
            const maxFrame = big ? 160 : 90;
            function animate() {{
                frame++;
                ctx2.clearRect(0, 0, canvas.width, canvas.height);
                particles.forEach(function(p) {{
                    p.vy += 0.12; p.x += p.vx; p.y += p.vy; p.rot += p.vr;
                    ctx2.save(); ctx2.translate(p.x, p.y); ctx2.rotate(p.rot * Math.PI / 180);
                    ctx2.fillStyle = p.color;
                    ctx2.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
                    ctx2.restore();
                }});
                if (frame < maxFrame) {{ requestAnimationFrame(animate); }} else {{ canvas.remove(); }}
            }}
            animate();
        }}
        function showToast(text) {{
            const doc = window.parent.document;
            const el = doc.createElement('div');
            el.textContent = text;
            el.style.cssText = 'position:fixed;top:16%;left:50%;transform:translate(-50%,0);' +
                'background:rgba(10,14,30,0.92);border:1px solid rgba(255,209,102,0.55);color:#FFD166;' +
                'font-family:"JetBrains Mono",monospace;font-weight:700;font-size:0.95rem;' +
                'padding:0.5rem 1.1rem;border-radius:999px;z-index:99999;pointer-events:none;' +
                'box-shadow:0 10px 30px rgba(0,0,0,0.45);opacity:0;transition:all 0.35s ease;white-space:nowrap;';
            doc.body.appendChild(el);
            requestAnimationFrame(function() {{ el.style.opacity = '1'; el.style.transform = 'translate(-50%,-14px)'; }});
            setTimeout(function() {{ el.style.opacity = '0'; el.style.transform = 'translate(-50%,-34px)'; }}, 1150);
            setTimeout(function() {{ el.remove(); }}, 1550);
        }}
        {sound_js}
        {toast_js}
        {confetti_js}
    }})();
    </script>
    """


def _fire_pending_effect():
    effect = st.session_state.pop("quiz_pending_effect", None)
    if effect:
        components_html(_effect_script(effect), height=1)


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
    st.session_state.setdefault("quiz_xp", 0)
    st.session_state.setdefault("quiz_best_streak", 0)

    st.markdown(_QUIZ_CSS, unsafe_allow_html=True)
    st.markdown(_HIDE_AUTOADVANCE_CSS, unsafe_allow_html=True)
    _fire_pending_effect()

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

    answered_ct = len(st.session_state.quiz_answers)
    live_pct = int((answered_ct / total) * 100) if total else 0
    st.markdown(
        f'<div class="q-xp-bar-wrap">'
        f'<div class="q-xp-badge">📝 {answered_ct}/{total} answered</div>'
        f'<div class="q-xp-track"><div class="q-xp-fill" style="width:{live_pct}%;"></div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

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
            st.session_state.quiz_pending_effect = {"sound": "pop"}
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
            if st.button("⬅ Previous", use_container_width=True, key="quiz_prev"):
                st.session_state.current_question -= 1
                st.session_state.quiz_question_start_time = None
                st.rerun()

    with col2:
        if current < total - 1:
            if st.button("Next ➡", use_container_width=True, type="primary", key="quiz_next"):
                st.session_state.current_question += 1
                st.session_state.quiz_question_start_time = None
                st.rerun()
        else:
            if st.button("✅ Submit quiz", use_container_width=True, type="primary", key="quiz_submit"):
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
            '<div style=\'font-family:"Space Grotesk",sans-serif;font-size:1.02rem;'
            'font-weight:600;color:#EAF0FF;margin-bottom:0.2rem;\'>🗂 Question palette</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_PALETTE_CSS, unsafe_allow_html=True)

        answered_ct = len(answers)
        flagged_ct = sum(1 for v in flagged.values() if v)
        st.caption(f"{answered_ct}/{total} answered · {flagged_ct} marked for review")

        st.markdown(
            '<div class="quiz-legend-row">'
            '<span><span class="quiz-legend-dot" style="background:#22D3EE;"></span>Answered</span>'
            '<span><span class="quiz-legend-dot" style="background:#FF5C7A;"></span>Visited</span>'
            '<span><span class="quiz-legend-dot" style="background:#7C5CFF;"></span>Marked</span>'
            '<span><span class="quiz-legend-dot" style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.14);"></span>New</span>'
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
    st.session_state.quiz_xp = 0
    st.session_state.quiz_best_streak = 0
    st.session_state.quiz_pending_effect = None


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
        <div id="qt-wrap" style="font-family: 'JetBrains Mono', ui-monospace, monospace;">
          <div style="display:flex; align-items:center; gap:0.6rem;">
            <div style="flex:1; height:8px; background:rgba(255,255,255,0.08); border-radius:6px; overflow:hidden;">
              <div id="qt-bar" style="height:100%; border-radius:6px; width:{pct * 100:.2f}%;
                   background: linear-gradient(90deg, #22D3EE, #7C5CFF); transition: width 0.2s linear, background-color 0.3s ease;"></div>
            </div>
            <div id="qt-label" style="font-size:0.78rem; color:#9FB0D9; min-width:2.4em; text-align:right;">{int(remaining)}s</div>
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
                    bar.style.background = '#FF5C7A';
                }} else if (remaining <= total * 0.5) {{
                    bar.style.background = 'linear-gradient(90deg, #FFD166, #FF5C7A)';
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
        <div id="qtt-wrap" style="font-family: 'JetBrains Mono', ui-monospace, monospace;">
          <div style="display:flex; align-items:center; gap:0.6rem;">
            <div style="font-size:0.72rem; color:#9FB0D9; white-space:nowrap;">⏱ TOTAL TIME LEFT</div>
            <div style="flex:1; height:8px; background:rgba(255,255,255,0.08); border-radius:6px; overflow:hidden;">
              <div id="qtt-bar" style="height:100%; border-radius:6px; width:{pct * 100:.2f}%;
                   background: linear-gradient(90deg, #22D3EE, #7C5CFF); transition: width 1s linear, background-color 0.3s ease;"></div>
            </div>
            <div id="qtt-label" style="font-size:0.85rem; font-weight:600; color:#EAF0FF; min-width:3.6em; text-align:right;">{label}</div>
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
                    bar.style.background = '#FF5C7A';
                }} else if (remaining <= total * 0.25) {{
                    bar.style.background = 'linear-gradient(90deg, #FFD166, #FF5C7A)';
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
    """Grades the quiz and layers on the gamification pass: XP (with a
    streak bonus for consecutive correct answers) and the longest streak
    reached, then queues the results-screen confetti/sound/toast."""
    quiz = st.session_state.quiz
    score = 0
    streak = 0
    best_streak = 0
    xp = 0

    for i, q in enumerate(quiz):
        selected_letter = st.session_state.quiz_answers.get(i)
        if selected_letter and selected_letter == q["answer"]:
            score += 1
            streak += 1
            best_streak = max(best_streak, streak)
            xp += 10 + min(streak, 5) * 4
        else:
            streak = 0

    total = len(quiz)
    percentage = (score / total) * 100 if total else 0

    st.session_state.quiz_score = score
    st.session_state.quiz_submitted = True
    st.session_state.quiz_question_start_time = None
    st.session_state.quiz_xp = xp
    st.session_state.quiz_best_streak = best_streak

    if percentage >= 90:
        toast = f"🏆 {score}/{total} · Flawless run! +{xp} XP"
    elif percentage >= 60:
        toast = f"🎉 {score}/{total} correct · +{xp} XP"
    else:
        toast = f"+{xp} XP · keep going"

    st.session_state.quiz_pending_effect = {
        "sound": "fanfare" if percentage >= 60 else "soft",
        "confetti": percentage >= 50,
        "big": percentage >= 90,
        "toast": toast,
    }


def _render_results():
    quiz = st.session_state.quiz
    total = len(quiz)
    score = st.session_state.quiz_score
    percentage = (score / total) * 100
    xp = st.session_state.get("quiz_xp", 0)
    best_streak = st.session_state.get("quiz_best_streak", 0)
    level = _level_for_xp(xp)

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
    st.markdown(
        f'<div class="q-xp-bar-wrap">'
        f'<div class="q-xp-badge">⭐ LVL {level} · {xp} XP</div>'
        f'<div class="q-xp-track"><div class="q-xp-fill" style="width:{min(100, (xp % 100) + (5 if xp else 0))}%;"></div></div>'
        f'<div style="flex-shrink:0;font-size:0.76rem;color:#FFD166;font-family:\'JetBrains Mono\',monospace;">🔥 best streak {best_streak}</div>'
        f"</div>",
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
        if st.button("📖 Review answers", use_container_width=True, key="quiz_review"):
            st.session_state.review_mode = True
            st.rerun()
    with col2:
        if st.button("🔁 New quiz", use_container_width=True, key="quiz_new"):
            _exit_quiz()
            st.session_state.quiz_stage = "setup"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_review():
    quiz = st.session_state.quiz

    st.markdown('<div class="section-label">📖 Review</div>', unsafe_allow_html=True)

    streak = 0
    for i, q in enumerate(quiz):
        st.markdown('<div class="quiz-card">', unsafe_allow_html=True)
        st.markdown(f"**{i + 1}. {q['question']}**")

        selected_letter = st.session_state.quiz_answers.get(i)
        if selected_letter:
            st.markdown(f"Your answer: **{selected_letter}** &nbsp;·&nbsp; Correct: **{q['answer']}**")
            if selected_letter == q["answer"]:
                streak += 1
                flame = " 🔥" * min(streak, 3) if streak >= 2 else ""
                st.success(f"Correct{flame}")
            else:
                streak = 0
                st.error("Incorrect")
        else:
            streak = 0
            st.markdown(f"Your answer: **(skipped)** &nbsp;·&nbsp; Correct: **{q['answer']}**")
            st.error("Not answered")

        st.info(q["explanation"])
        st.markdown("</div>", unsafe_allow_html=True)
