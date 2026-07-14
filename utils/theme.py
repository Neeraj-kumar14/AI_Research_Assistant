"""
Design system for the AI Research Assistant.

Concept: a digital study desk. Ink-navy for structure and authority,
forest-green as the working accent (like a highlighter), warm gold used
sparingly for emphasis (like a wax seal / library gold leaf). Serif for
headings (academic, printed-page feel), clean sans for body copy, mono
for citations and page references — because a citation is data, not prose.

Signature element: source citations render as small rotated index cards,
echoing physical research cards rather than generic pill badges.
"""

import streamlit as st

# ---- Design tokens --------------------------------------------------------

COLOR_INK = "#1B2A4A"          # primary text / headings
COLOR_INK_SOFT = "#41507A"     # secondary text
COLOR_PAPER = "#FAFAF7"        # page background
COLOR_PAPER_RAISED = "#FFFFFF" # card background
COLOR_PAPER_MUTED = "#F1EFE7"  # sidebar / muted panels
COLOR_ACCENT = "#2F6F4E"       # forest green — primary actions
COLOR_ACCENT_DARK = "#234F38"
COLOR_GOLD = "#B8860B"         # sparing emphasis — badges, highlights
COLOR_BORDER = "#E4E0D4"
COLOR_ERROR = "#A3402A"

FONT_DISPLAY = "'Source Serif 4', Georgia, serif"
FONT_BODY = "'Inter', -apple-system, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"


def inject_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {{
            font-family: {FONT_BODY};
            color: {COLOR_INK};
        }}

        .stApp {{
            background-color: {COLOR_PAPER};
        }}

        /* ---- Headings ---- */
        h1, h2, h3 {{
            font-family: {FONT_DISPLAY} !important;
            color: {COLOR_INK} !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
        }}

        /* ---- Hero ---- */
        .study-hero {{
            padding: 2.2rem 2.4rem;
            background: linear-gradient(135deg, {COLOR_PAPER_RAISED} 0%, {COLOR_PAPER_MUTED} 100%);
            border: 1px solid {COLOR_BORDER};
            border-radius: 14px;
            margin-bottom: 1.6rem;
        }}
        .study-hero .eyebrow {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: {COLOR_ACCENT_DARK};
            margin-bottom: 0.4rem;
        }}
        .study-hero h1 {{
            font-size: 2.15rem !important;
            margin: 0 0 0.5rem 0 !important;
        }}
        .study-hero p {{
            font-size: 1.02rem;
            color: {COLOR_INK_SOFT};
            max-width: 620px;
            margin: 0;
        }}

        /* ---- Feature grid ---- */
        .feature-card {{
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 12px;
            padding: 1.1rem 1.2rem;
            height: 100%;
        }}
        .feature-card .ico {{
            font-size: 1.3rem;
            margin-bottom: 0.35rem;
            display: block;
        }}
        .feature-card .title {{
            font-weight: 600;
            font-size: 0.95rem;
            color: {COLOR_INK};
            margin-bottom: 0.2rem;
        }}
        .feature-card .desc {{
            font-size: 0.83rem;
            color: {COLOR_INK_SOFT};
            line-height: 1.4;
        }}

        /* ---- Section label (hairline + small caps, used only where it
               genuinely marks a distinct section, not decoration) ---- */
        .section-label {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: {COLOR_INK_SOFT};
            border-bottom: 1px solid {COLOR_BORDER};
            padding-bottom: 0.4rem;
            margin: 1.4rem 0 0.9rem 0;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: {COLOR_PAPER_MUTED};
            border-right: 1px solid {COLOR_BORDER};
        }}
        section[data-testid="stSidebar"] .stButton button {{
            width: 100%;
            border-radius: 8px;
            border: 1px solid {COLOR_BORDER};
            background-color: {COLOR_PAPER_RAISED};
            color: {COLOR_INK};
            font-weight: 500;
            font-size: 0.88rem;
            text-align: left;
            padding: 0.5rem 0.8rem;
            transition: border-color 0.15s ease, color 0.15s ease;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color: {COLOR_ACCENT};
            color: {COLOR_ACCENT_DARK};
        }}

        /* Primary action buttons anywhere */
        .stButton > button[kind="primary"] {{
            background-color: {COLOR_ACCENT};
            border: none;
            border-radius: 8px;
            font-weight: 500;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {COLOR_ACCENT_DARK};
        }}

        /* ---- Source "index card" citations — the signature element ---- */
        .source-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.6rem;
        }}
        .index-card {{
            font-family: {FONT_MONO};
            font-size: 0.76rem;
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-left: 3px solid {COLOR_GOLD};
            border-radius: 4px;
            padding: 0.3rem 0.6rem;
            color: {COLOR_INK_SOFT};
            box-shadow: 1px 2px 0 rgba(27, 42, 74, 0.05);
        }}
        .index-card.web {{
            border-left-color: {COLOR_ACCENT};
        }}
        .index-card a {{
            color: {COLOR_INK_SOFT};
            text-decoration: none;
        }}
        .index-card a:hover {{
            color: {COLOR_ACCENT_DARK};
            text-decoration: underline;
        }}

        /* ---- Quiz question card ---- */
        .quiz-card {{
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 12px;
            padding: 1.4rem 1.5rem;
            margin-bottom: 1rem;
        }}
        .quiz-progress-label {{
            font-family: {FONT_MONO};
            font-size: 0.75rem;
            color: {COLOR_INK_SOFT};
            letter-spacing: 0.05em;
        }}

        /* ---- Flashcard ---- */
        .flash-q {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            color: {COLOR_ACCENT_DARK};
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        /* ---- Chat message polish ---- */
        [data-testid="stChatMessage"] {{
            border-radius: 12px;
        }}

        /* ---- Misc ---- */
        .stCaption, div[data-testid="stCaptionContainer"] {{
            font-family: {FONT_MONO} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="study-hero">
            <div class="eyebrow">Research · Read · Retain</div>
            <h1>AI Research Assistant</h1>
            <p>Upload a PDF or DOCX and work through it the way you would with
            a research partner — ask questions, pull citations, generate
            study notes, flashcards, and quizzes, with the option to fall
            back to the web when your document runs out of answers.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_grid():
    features = [
        ("📄", "Chat with your document", "Ask questions and get answers grounded in the exact page they came from."),
        ("🌐", "Hybrid web fallback", "When the document doesn't have it, the assistant searches the web automatically."),
        ("📝", "Study notes", "Turn any document into structured, exam-ready notes."),
        ("🧠", "Flashcards", "Auto-generated Q&A cards for quick review."),
        ("❓", "Interactive quiz", "Ten multiple-choice questions with scoring and review."),
        ("🌍", "Multilingual", "Ask in Hindi, Marathi, Tamil, and more — it answers in kind."),
    ]
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <span class="ico">{icon}</span>
                    <div class="title">{title}</div>
                    <div class="desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def animated_loader(steps=None):
    """HTML for a sliding progress bar + staggered cycling status text.
    Not tied to real progress (the underlying call is a single blocking
    API request) — it's a perceived-progress indicator so a 10-20s wait
    doesn't feel dead."""
    if steps is None:
        steps = ["Reading your document", "Identifying key concepts", "Drafting questions", "Finalizing"]

    step_divs = ""
    for i, s in enumerate(steps):
        delay = round(i * (2.4 / len(steps)), 2)
        step_divs += f'<div class="loader-step" style="animation-delay:{delay}s;">{s}&hellip;</div>'

    return f"""
    <div class="gen-loader">
        <div class="loader-track"><div class="loader-bar"></div></div>
        <div class="loader-steps">{step_divs}</div>
    </div>
    <style>
    .gen-loader {{ padding: 0.9rem 0 0.4rem 0; }}
    .loader-track {{
        width: 100%; height: 6px; background: {COLOR_PAPER_MUTED};
        border-radius: 6px; overflow: hidden; margin-bottom: 0.7rem;
    }}
    .loader-bar {{
        width: 35%; height: 100%; border-radius: 6px;
        background: linear-gradient(90deg, {COLOR_ACCENT}, {COLOR_GOLD});
        animation: loaderMove 1.3s ease-in-out infinite;
    }}
    @keyframes loaderMove {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(380%); }}
    }}
    .loader-steps {{
        position: relative; height: 1.3rem;
        font-family: {FONT_MONO}; font-size: 0.78rem; color: {COLOR_INK_SOFT};
    }}
    .loader-step {{
        position: absolute; top: 0; left: 0; opacity: 0;
        animation: loaderFade 2.4s ease-in-out infinite;
    }}
    @keyframes loaderFade {{
        0%, 100% {{ opacity: 0; }}
        8%, 22% {{ opacity: 1; }}
        30% {{ opacity: 0; }}
    }}
    </style>
    """
