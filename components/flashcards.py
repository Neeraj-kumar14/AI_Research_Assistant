import random
import re
import html

import streamlit as st
import streamlit.components.v1 as components

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
.fc-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.2rem;
}
.fc-progress-track {
    width: 100%;
    height: 8px;
    background: #F1EFE7;
    border-radius: 6px;
    overflow: hidden;
    margin: 0.35rem 0 0.5rem 0;
}
.fc-progress-fill {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, #B8860B, #2F6F4E);
    transition: width 0.4s ease;
}
.fc-stats-row {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.76rem;
    color: #41507A;
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
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.02em;
    color: #6B7280;
    margin: 0.1rem 0 0.5rem 0;
}
.fc-swipe-hint b {
    color: #2F6F4E;
}
.fc-swipe-hint b.fc-hint-no {
    color: #A3402A;
}
.fc-toggle {
    display: none;
}
.fc-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    display: block;
    cursor: pointer;
    transition: transform 0.5s;
    transform-style: preserve-3d;
}
.fc-toggle:checked ~ .fc-card-inner {
    transform: rotateY(180deg);
}
.fc-card-face {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    border-radius: 16px;
    border: 1px solid #E4E0D4;
    padding: 1.6rem 1.8rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    gap: 0.6rem;
    box-shadow: 0 6px 20px rgba(27, 42, 74, 0.07);
}
.fc-card-front {
    background: #FFFFFF;
}
.fc-card-back {
    background: #EFF3EE;
    transform: rotateY(180deg);
}
.fc-card-label-q {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #B8860B;
}
.fc-card-label-a {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #2F6F4E;
}
.fc-card-text {
    font-size: 1.12rem;
    color: #1B2A4A;
    line-height: 1.5;
    max-height: 190px;
    overflow-y: auto;
}
.fc-card-hint {
    font-size: 0.72rem;
    color: #6B7280;
    margin-top: auto;
}
.fc-star-badge {
    position: absolute;
    top: 0.7rem;
    right: 0.9rem;
    font-size: 1.1rem;
}
.fc-done-burst {
    text-align: center;
    font-size: 2.1rem;
    animation: fcPopIn 0.45s cubic-bezier(0.22, 1, 0.36, 1);
    margin-bottom: 0.2rem;
}
.fc-know-btn .stButton > button {
    border: 1px solid #2F6F4E !important;
    color: #2F6F4E !important;
    border-radius: 10px !important;
}
.fc-know-btn .stButton > button:hover:not(:disabled) {
    background: #EFF3EE !important;
}
.fc-learning-btn .stButton > button {
    border: 1px solid #A3402A !important;
    color: #A3402A !important;
    border-radius: 10px !important;
}
.fc-learning-btn .stButton > button:hover:not(:disabled) {
    background: #FBEDE8 !important;
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


def _inject_swipe_handler():
    """Makes the currently-rendered .fc-single-card draggable with touch/
    mouse, showing live KNOW-IT / LEARNING badges as it's dragged, and
    firing the real 'Know it' / 'Still learning' Streamlit buttons once
    the drag passes a threshold — so a swipe behaves exactly like
    tapping those buttons, just more interactive."""
    components.html(
        """
        <script>
        (function() {
            function attach() {
                const doc = window.parent.document;
                const card = doc.querySelector('.fc-single-card');
                if (!card || card.dataset.swipeBound === "1") return;
                card.dataset.swipeBound = "1";

                let startX = 0, startY = 0, dx = 0, dragging = false, moved = false;

                const likeBadge = doc.createElement('div');
                likeBadge.textContent = '✅ KNOW IT';
                likeBadge.style.cssText =
                    'position:absolute;top:14px;left:14px;padding:6px 12px;' +
                    'border:3px solid #2F6F4E;color:#2F6F4E;font-weight:700;' +
                    'border-radius:8px;transform:rotate(-10deg);opacity:0;' +
                    'pointer-events:none;font-family:monospace;font-size:0.85rem;' +
                    'z-index:20;background:rgba(255,255,255,0.92);';
                const nopeBadge = doc.createElement('div');
                nopeBadge.textContent = '❌ LEARNING';
                nopeBadge.style.cssText =
                    'position:absolute;top:14px;right:14px;padding:6px 12px;' +
                    'border:3px solid #A3402A;color:#A3402A;font-weight:700;' +
                    'border-radius:8px;transform:rotate(10deg);opacity:0;' +
                    'pointer-events:none;font-family:monospace;font-size:0.85rem;' +
                    'z-index:20;background:rgba(255,255,255,0.92);';
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
                        if (moved) { e.preventDefault(); }
                    });
                }
            }
            attach();
            setTimeout(attach, 150);
            setTimeout(attach, 500);
        })();
        </script>
        """,
        height=0,
    )


def render_flashcard_deck():
    """Full-slide, one-card-at-a-time deck with flip + swipe-in animation,
    know/still-learning tracking, starring, and shuffle."""
    if st.session_state.get("flashcard_stage") != "active" or not st.session_state.get("flashcards"):
        return

    st.markdown(_DECK_CSS, unsafe_allow_html=True)

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
        if st.button("🔀 Shuffle", use_container_width=True):
            random.shuffle(st.session_state.flashcard_order)
            st.session_state.flashcard_current = 0
            st.session_state.flashcard_direction = "next"
            st.rerun()
    with col_view2:
        if st.button("🔲 View all cards", use_container_width=True):
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

    _inject_swipe_handler()

    if st.button("⭐ Unstar" if is_starred else "⭐ Star this card", key=f"star_{card_index}", use_container_width=True):
        st.session_state.flashcard_starred[card_index] = not is_starred
        st.rerun()

    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅ Previous", use_container_width=True, disabled=current == 0):
            st.session_state.flashcard_current -= 1
            st.session_state.flashcard_direction = "prev"
            st.rerun()
    with col_next:
        if st.button("Skip ➡", use_container_width=True):
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()

    col_learning, col_know = st.columns(2)
    with col_learning:
        st.markdown('<div class="fc-learning-btn">', unsafe_allow_html=True)
        if st.button("❌ Still learning", key=f"learning_{card_index}", use_container_width=True):
            st.session_state.flashcard_known[card_index] = False
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with col_know:
        st.markdown('<div class="fc-know-btn">', unsafe_allow_html=True)
        if st.button("✅ Know it", key=f"know_{card_index}", use_container_width=True):
            st.session_state.flashcard_known[card_index] = True
            st.session_state.flashcard_current += 1
            st.session_state.flashcard_direction = "next"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def _render_grid_view(cards):
    st.markdown('<div class="section-label">🔲 All cards</div>', unsafe_allow_html=True)
    render_flashcards(cards, key_prefix="fc-grid")
    if st.button("◀ Back to deck", use_container_width=True):
        st.session_state.flashcard_view = "deck"
        st.rerun()


def _render_deck_complete(total, known_count, learning_count, starred_count):
    st.markdown('<div class="fc-single-card" style="height:auto;">', unsafe_allow_html=True)
    st.markdown('<div class="fc-done-burst">🎉</div>', unsafe_allow_html=True)
    st.markdown("### Deck complete")
    st.markdown(
        f"**{known_count}/{total}** marked know-it &nbsp;·&nbsp; "
        f"**{learning_count}/{total}** still learning &nbsp;·&nbsp; "
        f"**{starred_count}** starred"
    )

    if learning_count:
        st.warning(f"{learning_count} card(s) marked \"still learning\" — review those again with a restart.")
    else:
        st.success("You marked every card as known. Nice work.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔁 Restart deck", use_container_width=True):
            st.session_state.flashcard_current = 0
            st.session_state.flashcard_known = {}
            st.session_state.flashcard_direction = "next"
            st.rerun()
    with col2:
        if st.button("🔲 Review all", use_container_width=True):
            st.session_state.flashcard_view = "grid"
            st.rerun()
    with col3:
        if st.button("🆕 New deck", use_container_width=True):
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
