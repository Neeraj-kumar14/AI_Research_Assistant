import json
import random
import re
import html

import streamlit as st
from streamlit.components.v1 import html as components_html

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


# ---- Gamification: XP / streak bookkeeping --------------------------------

def _xp_for_level(level: int) -> int:
    """XP threshold to reach `level` — a gentle upward curve (100, 220,
    360, 520...) so early levels click by fast and it keeps giving a
    reason to push through the deck."""
    total = 0
    for lv in range(1, level):
        total += 100 + (lv - 1) * 20
    return total


def _level_for_xp(xp: int) -> int:
    level = 1
    while xp >= _xp_for_level(level + 1):
        level += 1
    return level


def _register_answer(known: bool):
    """Updates XP/streak state after a Know it / Still learning tap and
    queues up the toast + sound + confetti that should fire on next render."""
    st.session_state.setdefault("flashcard_xp", 0)
    st.session_state.setdefault("flashcard_streak", 0)
    st.session_state.setdefault("flashcard_best_streak", 0)

    old_xp = st.session_state.flashcard_xp
    old_level = _level_for_xp(old_xp)
    streak = st.session_state.flashcard_streak

    if known:
        streak += 1
        gain = 10 + min(streak, 6) * 5  # 15..40 XP, scales with streak
    else:
        streak = 0
        gain = 4  # small participation XP so missing one never feels like a wall

    new_xp = old_xp + gain
    new_level = _level_for_xp(new_xp)

    st.session_state.flashcard_xp = new_xp
    st.session_state.flashcard_streak = streak
    st.session_state.flashcard_best_streak = max(st.session_state.flashcard_best_streak, streak)

    effect = {"sound": "know" if known else "learning", "toast": f"+{gain} XP", "confetti": False, "big": False}

    if new_level > old_level:
        effect.update(sound="levelup", confetti=True, toast=f"⭐ LEVEL {new_level}! +{gain} XP")
    elif known and streak >= 3 and streak % 3 == 0:
        effect.update(confetti=True, toast=f"🔥 {streak}-streak! +{gain} XP")
    elif known and streak >= 2:
        effect["toast"] = f"+{gain} XP · 🔥 x{streak}"

    st.session_state.flashcard_pending_effect = effect


_COLORS_JS = "['#22D3EE','#7C5CFF','#FF3EA5','#FFD166','#3DDC97']"


def _effect_script(effect):
    """Best-effort synthesized sound (Web Audio, no audio files) + a
    floating XP toast + an optional confetti burst — all injected into
    the parent document so they aren't clipped by the component iframe."""
    if not effect:
        return ""

    sound = effect.get("sound")
    toast = effect.get("toast")
    confetti = effect.get("confetti")
    big = effect.get("big")

    sound_js = ""
    if sound == "pop":
        sound_js = "tone(720,0.08,'triangle',0,0.10);"
    elif sound == "know":
        sound_js = "tone(660,0.09,'sine',0,0.11);tone(990,0.11,'sine',0.07,0.11);"
    elif sound == "learning":
        sound_js = "tone(220,0.16,'sine',0,0.08);"
    elif sound == "levelup":
        sound_js = (
            "tone(523,0.1,'square',0,0.09);tone(659,0.1,'square',0.1,0.09);"
            "tone(784,0.1,'square',0.2,0.09);tone(1046,0.2,'square',0.3,0.1);"
        )
    elif sound == "fanfare":
        sound_js = (
            "tone(523,0.12,'triangle',0,0.1);tone(659,0.12,'triangle',0.12,0.1);"
            "tone(784,0.12,'triangle',0.24,0.1);tone(1046,0.3,'triangle',0.36,0.12);"
        )

    confetti_js = f"confettiBurst({320 if big else 70}, {_COLORS_JS}, {'true' if big else 'false'});" if confetti else ""
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
                    x: big ? Math.random() * canvas.width : cx + (Math.random() - 0.5) * 180,
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
            const maxFrame = big ? 150 : 85;
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
    effect = st.session_state.pop("flashcard_pending_effect", None)
    if effect:
        components_html(_effect_script(effect), height=1)


_DECK_CSS = """
<style>
@keyframes fcFadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fcSlideInRight {
    from { opacity: 0; transform: translateX(46px) rotate(3deg); }
    to   { opacity: 1; transform: translateX(0) rotate(0deg); }
}
@keyframes fcSlideInLeft {
    from { opacity: 0; transform: translateX(-46px) rotate(-3deg); }
    to   { opacity: 1; transform: translateX(0) rotate(0deg); }
}
@keyframes fcPopIn {
    0%   { opacity: 0; transform: scale(0.94); }
    100% { opacity: 1; transform: scale(1); }
}
@keyframes fcLevelGlow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,209,102,0.0); }
    50%      { box-shadow: 0 0 16px 3px rgba(255,209,102,0.35); }
}
.fc-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.2rem;
}
.fc-xp-bar-wrap {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.5rem 0 0.6rem 0;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.fc-xp-badge {
    flex-shrink: 0;
    font-size: 0.74rem;
    font-weight: 700;
    color: #05060F;
    background: linear-gradient(120deg, #FFD166, #FF3EA5);
    padding: 0.22rem 0.6rem;
    border-radius: 999px;
    animation: fcLevelGlow 2.4s ease-in-out infinite;
    white-space: nowrap;
}
.fc-xp-track {
    flex: 1;
    height: 8px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    overflow: hidden;
}
.fc-xp-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #22D3EE, #7C5CFF, #FF3EA5);
    transition: width 0.5s cubic-bezier(0.22,1,0.36,1);
}
.fc-streak-badge {
    flex-shrink: 0;
    font-size: 0.76rem;
    color: #FFD166;
    white-space: nowrap;
}
.fc-progress-track {
    width: 100%;
    height: 8px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    overflow: hidden;
    margin: 0.35rem 0 0.5rem 0;
}
.fc-progress-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #7C5CFF, #22D3EE);
    transition: width 0.4s ease;
}
.fc-stats-row {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.76rem;
    color: #9FB0D9;
    margin-bottom: 0.7rem;
}
.fc-deck-wrap.fc-anim-next {
    animation: fcSlideInRight 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.fc-deck-wrap.fc-anim-prev {
    animation: fcSlideInLeft 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
.fc-single-card {
    perspective: 1400px;
    height: 320px;
    max-width: 560px;
    margin: 0.4rem auto 0.6rem auto;
    position: relative;
    touch-action: pan-y;
    will-change: transform;
}
.fc-swipe-hint {
    text-align: center;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.02em;
    color: #9FB0D9;
    margin: 0.1rem 0 0.5rem 0;
}
.fc-swipe-hint b { color: #3DDC97; }
.fc-swipe-hint b.fc-hint-no { color: #FF5C7A; }
.fc-toggle { display: none; }
.fc-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    display: block;
    cursor: pointer;
    transition: transform 0.5s;
    transform-style: preserve-3d;
}
.fc-toggle:checked ~ .fc-card-inner { transform: rotateY(180deg); }
.fc-card-face {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.16);
    padding: 1.6rem 1.8rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    gap: 0.6rem;
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    box-shadow: 0 18px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.12);
}
.fc-card-front {
    background: linear-gradient(155deg, rgba(124,92,255,0.16), rgba(255,255,255,0.04));
}
.fc-card-back {
    background: linear-gradient(155deg, rgba(34,211,238,0.16), rgba(255,255,255,0.04));
    transform: rotateY(180deg);
}
.fc-card-label-q {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #FFD166;
}
.fc-card-label-a {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #22D3EE;
}
.fc-card-text {
    font-size: 1.12rem;
    color: #EAF0FF;
    line-height: 1.5;
    max-height: 190px;
    overflow-y: auto;
}
.fc-card-hint { font-size: 0.72rem; color: #9FB0D9; margin-top: auto; }
.fc-star-badge {
    position: absolute;
    top: 0.7rem;
    right: 0.9rem;
    font-size: 1.1rem;
    filter: drop-shadow(0 0 6px rgba(255,209,102,0.6));
}
.fc-done-burst {
    text-align: center;
    font-size: 2.3rem;
    animation: fcPopIn 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    margin-bottom: 0.2rem;
}
.fc-know-btn .stButton > button {
    border: 1px solid #3DDC97 !important;
    color: #3DDC97 !important;
    border-radius: 10px !important;
    background: rgba(61,220,151,0.08) !important;
}
.fc-know-btn .stButton > button:hover:not(:disabled) { background: rgba(61,220,151,0.18) !important; }
.fc-learning-btn .stButton > button {
    border: 1px solid #FF5C7A !important;
    color: #FF5C7A !important;
    border-radius: 10px !important;
    background: rgba(255,92,122,0.08) !important;
}
.fc-learning-btn .stButton > button:hover:not(:disabled) { background: rgba(255,92,122,0.18) !important; }
.fc-single-card { transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.fc-single-card:hover { transform: translateY(-4px) scale(1.01); }
.fc-single-card:hover .fc-card-face { box-shadow: 0 22px 50px rgba(0,0,0,0.55), 0 0 30px rgba(124,92,255,0.18); }
.fc-star-badge { animation: fcPopIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
.fc-progress-fill, .fc-xp-fill { position: relative; overflow: hidden; }
.fc-progress-fill::after, .fc-xp-fill::after {
    content: "";
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.45), transparent);
    animation: fcShine 1.8s ease-in-out infinite;
}
@keyframes fcShine {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
.fc-topbar, .fc-stats-row, .fc-xp-bar-wrap { animation: fcFadeInUp 0.35s ease both; }
@media (prefers-reduced-motion: reduce) {
    .fc-progress-fill::after, .fc-xp-fill::after { animation: none !important; }
    .fc-single-card:hover { transform: none; }
    .fc-xp-badge { animation: none !important; }
}
</style>
"""


def render_flashcards(cards, key_prefix="fc"):
    """Grid of flip cards — used for the "all cards" review view. Pure CSS
    (checkbox hack) so no Streamlit rerun is needed to flip."""

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
        .flip-card {{ perspective: 1200px; height: 190px; }}
        .flip-toggle {{ display: none; }}
        .flip-card-inner {{
            position: relative;
            width: 100%;
            height: 100%;
            display: block;
            cursor: pointer;
            transition: transform 0.5s;
            transform-style: preserve-3d;
        }}
        .flip-toggle:checked ~ .flip-card-inner {{ transform: rotateY(180deg); }}
        .flip-card-face {{
            position: absolute;
            inset: 0;
            backface-visibility: hidden;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.14);
            padding: 1rem 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.35rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 10px 24px rgba(0,0,0,0.35);
        }}
        .flip-card-front {{ background: linear-gradient(155deg, rgba(124,92,255,0.14), rgba(255,255,255,0.03)); }}
        .flip-card-back {{
            background: linear-gradient(155deg, rgba(34,211,238,0.14), rgba(255,255,255,0.03));
            transform: rotateY(180deg);
        }}
        .flash-q {{
            font-family: 'JetBrains Mono', ui-monospace, monospace;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #FFD166;
        }}
        .flash-a {{
            font-family: 'JetBrains Mono', ui-monospace, monospace;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #22D3EE;
        }}
        .flip-card-text {{
            font-size: 0.92rem;
            color: #EAF0FF;
            line-height: 1.4;
            overflow-y: auto;
            max-height: 90px;
        }}
        .flip-hint {{ font-size: 0.68rem; color: #9FB0D9; margin-top: auto; }}
        </style>
        <div class="flip-grid">
            {cards_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inject_swipe_handler(card_id):
    """Makes the currently-rendered .fc-single-card draggable with touch/
    mouse, showing live KNOW-IT / LEARNING badges as it's dragged, and
    firing the real 'Know it' / 'Still learning' Streamlit buttons once
    the drag passes a threshold. Also plays a short "pop" tone directly
    on tap-to-flip, bound inside the same user-gesture click handler so
    it isn't blocked by autoplay policies.

    Also fixes the "next card shows the answer instead of the question"
    bug: Streamlit reuses the underlying DOM node for this markdown block
    across reruns and only patches attributes, so the flip checkbox's live
    `checked` property can survive from the previous card even though the
    new card's HTML never sets it. We force it back to unchecked whenever
    the card actually changed, while leaving it alone on reruns that
    re-render the *same* card (e.g. after starring it) so we don't undo
    the user's flip."""
    script = """
        <script>
        (function() {
            const doc = window.parent.document;
            const currentCardId = "__CARD_ID__";
            if (doc.body.dataset.fcLastCardId !== currentCardId) {
                doc.body.dataset.fcLastCardId = currentCardId;
                const toggle = doc.getElementById(currentCardId);
                if (toggle) toggle.checked = false;
            }

            function getCtx() {
                const w = window.parent;
                try {
                    if (!w.__fcAudio) w.__fcAudio = new (w.AudioContext || w.webkitAudioContext)();
                    if (w.__fcAudio.state === 'suspended') w.__fcAudio.resume().catch(function(){});
                    return w.__fcAudio;
                } catch (e) { return null; }
            }
            function pop() {
                const ctx = getCtx(); if (!ctx) return;
                const t0 = ctx.currentTime;
                const osc = ctx.createOscillator(); const gain = ctx.createGain();
                osc.type = 'triangle'; osc.frequency.setValueAtTime(720, t0);
                gain.gain.setValueAtTime(0, t0);
                gain.gain.linearRampToValueAtTime(0.09, t0 + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.001, t0 + 0.09);
                osc.connect(gain); gain.connect(ctx.destination);
                osc.start(t0); osc.stop(t0 + 0.12);
            }

            function attach() {
                const card = doc.querySelector('.fc-single-card');
                if (!card || card.dataset.swipeBound === "1") return;
                card.dataset.swipeBound = "1";

                let startX = 0, startY = 0, dx = 0, dragging = false, moved = false;

                const likeBadge = doc.createElement('div');
                likeBadge.textContent = '✅ KNOW IT';
                likeBadge.style.cssText =
                    'position:absolute;top:14px;left:14px;padding:6px 12px;' +
                    'border:3px solid #3DDC97;color:#3DDC97;font-weight:700;' +
                    'border-radius:8px;transform:rotate(-10deg);opacity:0;' +
                    'pointer-events:none;font-family:monospace;font-size:0.85rem;' +
                    'z-index:20;background:rgba(5,6,15,0.85);';
                const nopeBadge = doc.createElement('div');
                nopeBadge.textContent = '❌ LEARNING';
                nopeBadge.style.cssText =
                    'position:absolute;top:14px;right:14px;padding:6px 12px;' +
                    'border:3px solid #FF5C7A;color:#FF5C7A;font-weight:700;' +
                    'border-radius:8px;transform:rotate(10deg);opacity:0;' +
                    'pointer-events:none;font-family:monospace;font-size:0.85rem;' +
                    'z-index:20;background:rgba(5,6,15,0.85);';
                card.appendChild(likeBadge);
                card.appendChild(nopeBadge);

                const THRESHOLD = 90;

                function onDown(x, y) {
                    dragging = true;
                    moved = false;
                    startX = x;
                    startY = y;
                    dx = 0;
                    card.style.transition = 'none';
                }

                function onMove(x, y) {
                    if (!dragging) return;
                    dx = x - startX;
                    const dy = y - startY;
                    if (!moved && Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
                    moved = true;
                    const rot = dx / 18;
                    card.style.transform = 'translateX(' + dx + 'px) rotate(' + rot + 'deg)';
                    const t = Math.min(Math.abs(dx) / THRESHOLD, 1);
                    if (dx > 0) {
                        likeBadge.style.opacity = t;
                        nopeBadge.style.opacity = 0;
                    } else {
                        nopeBadge.style.opacity = t;
                        likeBadge.style.opacity = 0;
                    }
                }

                function onUp() {
                    if (!dragging) return;
                    dragging = false;
                    likeBadge.style.opacity = 0;
                    nopeBadge.style.opacity = 0;

                    if (Math.abs(dx) > THRESHOLD) {
                        const dir = dx > 0 ? 1 : -1;
                        card.style.transition = 'transform 0.35s ease';
                        card.style.transform = 'translateX(' + (dir * 700) + 'px) rotate(' + (dir * 28) + 'deg)';
                        const selector = dir > 0 ? '.fc-know-btn button' : '.fc-learning-btn button';
                        setTimeout(function() {
                            const btn = doc.querySelector(selector);
                            if (btn) btn.click();
                        }, 170);
                    } else if (moved) {
                        card.style.transition = 'transform 0.3s ease';
                        card.style.transform = 'translateX(0) rotate(0)';
                    }
                    dx = 0;
                }

                card.addEventListener('touchstart', function(e) {
                    onDown(e.touches[0].clientX, e.touches[0].clientY);
                }, {passive: true});
                card.addEventListener('touchmove', function(e) {
                    onMove(e.touches[0].clientX, e.touches[0].clientY);
                }, {passive: true});
                card.addEventListener('touchend', onUp);

                card.addEventListener('mousedown', function(e) {
                    onDown(e.clientX, e.clientY);
                });
                doc.addEventListener('mousemove', function(e) {
                    onMove(e.clientX, e.clientY);
                });
                doc.addEventListener('mouseup', onUp);

                // Don't let a drag also flip the card via its flip-toggle label.
                const label = card.querySelector('label.fc-card-inner');
                if (label) {
                    label.addEventListener('click', function(e) {
                        if (moved) { e.preventDefault(); } else { pop(); }
                    });
                }
            }
            attach();
            setTimeout(attach, 150);
            setTimeout(attach, 500);
        })();
        </script>
        """
    components_html(script.replace("__CARD_ID__", json.dumps(card_id)[1:-1]), height=1)


def render_flashcard_deck():
    """Full-slide, one-card-at-a-time deck with flip + swipe-in animation,
    know/still-learning tracking, starring, shuffle, and a full XP/streak
    gamification layer (confetti + synth sound on streak milestones,
    level-ups, and deck completion)."""
    if st.session_state.get("flashcard_stage") != "active" or not st.session_state.get("flashcards"):
        return

    st.session_state.setdefault("flashcard_xp", 0)
    st.session_state.setdefault("flashcard_streak", 0)
    st.session_state.setdefault("flashcard_best_streak", 0)

    st.markdown(_DECK_CSS, unsafe_allow_html=True)
    _fire_pending_effect()

    cards = st.session_state.flashcards
    order = st.session_state.flashcard_order
    current = st.session_state.flashcard_current
    total = len(order)

    st.markdown('<div class="fc-topbar">', unsafe_allow_html=True)
    col_a, col_b = st.columns([5, 1])
    with col_a:
        st.markdown('<div class="section-label">🧠 Flashcards</div>', unsafe_allow_html=True)
    with col_b:
        if st.button("✕ Exit", key="fc_exit", use_container_width=True):
            _exit_deck()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    xp = st.session_state.flashcard_xp
    level = _level_for_xp(xp)
    level_floor = _xp_for_level(level)
    level_ceiling = _xp_for_level(level + 1)
    xp_pct = int(((xp - level_floor) / max(1, level_ceiling - level_floor)) * 100)
    streak = st.session_state.flashcard_streak

    st.markdown(
        f'<div class="fc-xp-bar-wrap">'
        f'<div class="fc-xp-badge">⭐ LVL {level}</div>'
        f'<div class="fc-xp-track"><div class="fc-xp-fill" style="width:{xp_pct}%;"></div></div>'
        f'<div class="fc-streak-badge">{"🔥 " + str(streak) + " streak" if streak else "✨ " + str(xp) + " XP"}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    done = current >= total
    progress_pct = int((min(current, total) / total) * 100) if total else 0
    known_count = sum(1 for v in st.session_state.flashcard_known.values() if v)
    learning_count = sum(1 for v in st.session_state.flashcard_known.values() if not v)
    starred_count = sum(1 for v in st.session_state.flashcard_starred.values() if v)

    st.markdown(
        f'<div class="fc-progress-track"><div class="fc-progress-fill" style="width:{progress_pct}%;"></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="fc-stats-row">'
        f'CARD {min(current + 1, total)} OF {total} &nbsp;·&nbsp; '
        f'✅ {known_count} know it &nbsp;·&nbsp; ❌ {learning_count} still learning &nbsp;·&nbsp; '
        f'⭐ {starred_count} starred'
        f"</div>",
        unsafe_allow_html=True,
    )

    col_view1, col_view2 = st.columns(2)
    with col_view1:
        if st.button("🔀 Shuffle", use_container_width=True, key="fc_shuffle"):
            random.shuffle(st.session_state.flashcard_order)
            st.session_state.flashcard_current = 0
            st.session_state.flashcard_direction = "next"
            st.rerun()
    with col_view2:
        if st.button("🔲 View all cards", use_container_width=True, key="fc_view_all"):
            st.session_state.flashcard_view = "grid"
            st.rerun()

    if st.session_state.flashcard_view == "grid":
        _render_grid_view(cards)
        return

    if done:
        _render_deck_complete(total, known_count, learning_count, starred_count)
        return

    card_index = order[current]
    card = cards[card_index]
    is_starred = st.session_state.flashcard_starred.get(card_index, False)
    direction_class = "fc-anim-next" if st.session_state.flashcard_direction == "next" else "fc-anim-prev"
    card_id = f"fc-deck-{current}-{card_index}"

    q = html.escape(card["question"]).replace("\n", "<br>")
    a = html.escape(card["answer"]).replace("\n", "<br>")
    star_html = '<div class="fc-star-badge">⭐</div>' if is_starred else ""

    st.markdown(
        '<div class="fc-swipe-hint">👉 Swipe or drag the card: '
        '<b>right = know it</b> &nbsp;·&nbsp; <b class="fc-hint-no">left = still learning</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="fc-deck-wrap {direction_class}">
          <div class="fc-single-card">
            <input type="checkbox" id="{card_id}" class="fc-toggle" />
            <label for="{card_id}" class="fc-card-inner">
                <div class="fc-card-face fc-card-front">{star_html}
                    <div class="fc-card-label-q">Question</div>
                    <div class="fc-card-text">{q}</div>
                    <div class="fc-card-hint">Tap the card to reveal the answer · swipe to answer</div>
                </div>
                <div class="fc-card-face fc-card-back">{star_html}
                    <div class="fc-card-label-a">Answer</div>
                    <div class="fc-card-text">{a}</div>
                    <div class="fc-card-hint">Tap the card to see the question again · swipe to answer</div>
                </div>
            </label>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _inject_swipe_handler(card_id)

    if st.button("⭐ Unstar" if is_starred else "⭐ Star this card", key=f"star_{card_index}", use_container_width=True):
        st.session_state.flashcard_starred[card_index] = not is_starred
        st.rerun()

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Previous", use_container_width=True, disabled=current == 0, key="fc_deck_prev"):
            st.session_state.flashcard_current -= 1
            st.session_state.flashcard_direction = "prev"
            st.rerun()
    with col_next:
        if st.button("Skip ➡", use_container_width=True, key="fc_deck_skip"):
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()

    col_learning, col_know = st.columns(2)
    with col_learning:
        st.markdown('<div class="fc-learning-btn">', unsafe_allow_html=True)
        if st.button("❌ Still learning", key=f"learning_{card_index}", use_container_width=True):
            st.session_state.flashcard_known[card_index] = False
            _register_answer(False)
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with col_know:
        st.markdown('<div class="fc-know-btn">', unsafe_allow_html=True)
        if st.button("✅ Know it", key=f"know_{card_index}", use_container_width=True):
            st.session_state.flashcard_known[card_index] = True
            _register_answer(True)
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _render_grid_view(cards):
    st.markdown('<div class="section-label">🔲 All cards</div>', unsafe_allow_html=True)
    render_flashcards(cards, key_prefix="fc-grid")
    if st.button("◀ Back to deck", use_container_width=True, key="fc_back_to_deck"):
        st.session_state.flashcard_view = "deck"
        st.rerun()


def _render_deck_complete(total, known_count, learning_count, starred_count):
    if not st.session_state.get("flashcard_complete_celebrated"):
        st.session_state.flashcard_complete_celebrated = True
        big_win = learning_count == 0
        components_html(
            _effect_script(
                {
                    "sound": "fanfare",
                    "confetti": True,
                    "big": big_win,
                    "toast": "🏆 Deck complete!" if big_win else "🎉 Deck complete!",
                }
            ),
            height=1,
        )

    st.markdown('<div class="fc-single-card" style="height:auto;">', unsafe_allow_html=True)
    st.markdown('<div class="fc-done-burst">🎉</div>', unsafe_allow_html=True)
    st.markdown("### Deck complete")
    st.markdown(
        f"**{known_count}/{total}** marked know-it &nbsp;·&nbsp; "
        f"**{learning_count}/{total}** still learning &nbsp;·&nbsp; "
        f"**{starred_count}** starred &nbsp;·&nbsp; "
        f"**⭐ {st.session_state.flashcard_xp} XP** &nbsp;·&nbsp; "
        f"**🔥 best streak {st.session_state.flashcard_best_streak}**"
    )

    if learning_count:
        st.warning(f"{learning_count} card(s) marked \"still learning\" — review those again with a restart.")
    else:
        st.success("You marked every card as known. Nice work.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔁 Restart deck", use_container_width=True, key="fc_restart_deck"):
            st.session_state.flashcard_current = 0
            st.session_state.flashcard_known = {}
            st.session_state.flashcard_direction = "next"
            st.session_state.flashcard_complete_celebrated = False
            st.rerun()
    with col2:
        if st.button("🔲 Review all", use_container_width=True, key="fc_complete_review_all"):
            st.session_state.flashcard_view = "grid"
            st.rerun()
    with col3:
        if st.button("🆕 New deck", use_container_width=True, key="fc_new_deck"):
            _exit_deck()
            st.session_state.flashcard_stage = "setup"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _exit_deck():
    st.session_state.flashcard_stage = None
    st.session_state.flashcards = None
    st.session_state.flashcard_order = []
    st.session_state.flashcard_current = 0
    st.session_state.flashcard_known = {}
    st.session_state.flashcard_starred = {}
    st.session_state.flashcard_direction = "next"
    st.session_state.flashcard_view = "deck"
    st.session_state.flashcard_xp = 0
    st.session_state.flashcard_streak = 0
    st.session_state.flashcard_best_streak = 0
    st.session_state.flashcard_complete_celebrated = False
    st.session_state.flashcard_pending_effect = None
