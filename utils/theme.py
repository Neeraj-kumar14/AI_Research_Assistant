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
        @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {{
            font-family: {FONT_BODY};
            color: {COLOR_INK};
        }}

        .stApp {{
            background-color: {COLOR_PAPER};
        }}

        /* ---- Hide default Streamlit chrome that reads as "unfinished
               app" rather than a finished product (deploy button, footer,
               the ghost top header bar). The hamburger menu is left
               alone so Settings/Print/etc. are still reachable. ---- */
        .stAppDeployButton {{ display: none !important; }}
        footer {{ visibility: hidden; height: 0; }}
        header[data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ---- Centered, chat-app-style column. No sidebar anymore, so
               content is capped to a comfortable reading width and
               centered, the way ChatGPT/Claude lay out the transcript. ---- */
        .block-container {{
            max-width: 52rem;
            margin: 0 auto;
            padding-top: 1.5rem;
            padding-bottom: 9rem; /* room for the pinned composer */
        }}

        /* ---- Headings ---- */
        h1, h2, h3 {{
            font-family: {FONT_DISPLAY} !important;
            color: {COLOR_INK} !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
        }}

        /* ---- App title bar (replaces the old sidebar branding) ---- */
        .app-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 52rem;
            margin: 0 auto 0.4rem auto;
            padding: 0.3rem 0.1rem 0.9rem 0.1rem;
        }}
        .app-topbar .brand {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
            font-family: {FONT_DISPLAY};
            font-weight: 600;
            font-size: 1.12rem;
            color: {COLOR_INK};
        }}
        .app-topbar .brand .mark {{
            width: 30px; height: 30px;
            display: flex; align-items: center; justify-content: center;
            background: {COLOR_ACCENT};
            color: white;
            border-radius: 8px;
            font-size: 1rem;
        }}
        .app-topbar .status {{
            font-family: {FONT_MONO};
            font-size: 0.74rem;
            color: {COLOR_INK_SOFT};
        }}

        /* ---- Quick study-tool pills, shown once a document is loaded
               (this is where the sidebar's "Study tools" buttons live
               now). ---- */
        .st-key-toolbar_row .stButton > button,
        .st-key-toolbar_row .stDownloadButton > button {{
            border-radius: 999px;
            border: 1px solid {COLOR_BORDER};
            background: {COLOR_PAPER_RAISED};
            color: {COLOR_INK};
            font-size: 0.83rem;
            font-weight: 500;
            padding: 0.35rem 0.9rem;
            white-space: nowrap;
        }}
        .st-key-toolbar_row .stButton > button:hover,
        .st-key-toolbar_row .stDownloadButton > button:hover {{
            border-color: {COLOR_ACCENT};
            color: {COLOR_ACCENT_DARK};
        }}
        .st-key-toolbar_row {{
            margin-bottom: 0.6rem;
        }}

        /* ==========================================================
           Chat messages — ChatGPT/Claude style: user turns are a right
           -aligned soft bubble, assistant turns are plain full-width
           text (no boxy card), so the transcript reads like a
           conversation instead of a stack of form panels.
           ========================================================== */
        [data-testid="stChatMessage"] {{
            background: transparent;
            border: none;
            padding: 0.35rem 0;
            gap: 0.65rem;
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
            flex-direction: row-reverse;
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
            background: {COLOR_PAPER_MUTED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 16px;
            padding: 0.6rem 1rem;
            max-width: 82%;
            margin-left: auto;
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {{
            padding: 0.15rem 0;
        }}
        [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {{
            box-shadow: none;
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

        /* ---- Sidebar ---- (only used now by the in-quiz question
               palette, a genuinely separate navigational aid, not the
               old document/tools sidebar — kept styled to match) ---- */
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

        /* ==========================================================
           Pinned composer bar (st.bottom()) — the chat input, plus,
           directly above it, the "everything I've added" document-chip
           row and the "+" attachments/tools popover. Main replacement
           for the old sidebar.
           ========================================================== */
        [data-testid="stBottomBlockContainer"] {{
            background: linear-gradient(180deg, rgba(250,250,247,0) 0%, {COLOR_PAPER} 28%);
            backdrop-filter: blur(6px);
            padding-top: 0.6rem;
        }}
        [data-testid="stBottomBlockContainer"] > div {{
            max-width: 52rem;
            margin: 0 auto;
        }}
        [data-testid="stChatInput"] {{
            border-radius: 22px !important;
            border: 1px solid {COLOR_BORDER} !important;
            background: {COLOR_PAPER_RAISED} !important;
            box-shadow: 0 2px 10px rgba(27, 42, 74, 0.06);
        }}
        [data-testid="stChatInput"] textarea {{
            font-family: {FONT_BODY} !important;
        }}
        .st-key-composer_plus [data-testid="stPopoverButton"] {{
            border-radius: 50% !important;
            width: 2.15rem;
            height: 2.15rem;
            padding: 0 !important;
            font-size: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid {COLOR_BORDER} !important;
            background: {COLOR_PAPER_RAISED} !important;
            color: {COLOR_INK} !important;
        }}
        .st-key-composer_plus [data-testid="stPopoverButton"]:hover {{
            border-color: {COLOR_ACCENT} !important;
            color: {COLOR_ACCENT_DARK} !important;
        }}
        .doc-chip-row {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.4rem;
            margin: 0 0 0.45rem 0.1rem;
        }}
        .doc-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-family: {FONT_MONO};
            font-size: 0.74rem;
            background: {COLOR_PAPER_MUTED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 999px;
            padding: 0.22rem 0.7rem 0.22rem 0.6rem;
            color: {COLOR_INK_SOFT};
        }}
        .doc-chip .dot {{
            width: 6px; height: 6px; border-radius: 50%;
            background: {COLOR_ACCENT};
            flex-shrink: 0;
        }}
        .composer-stats {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            color: {COLOR_INK_SOFT};
            margin: 0 0 0.4rem 0.15rem;
        }}
        [data-testid="stPopoverBody"] {{
            border-radius: 12px;
            border: 1px solid {COLOR_BORDER};
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

        /* ==========================================================
           Responsive — narrow / mobile viewports.
           ========================================================== */
        @media (max-width: 640px) {{
            .block-container {{
                padding-left: 0.8rem;
                padding-right: 0.8rem;
                padding-bottom: 10rem;
            }}
            .study-hero {{ padding: 1.4rem 1.2rem; }}
            .study-hero h1 {{ font-size: 1.5rem !important; }}
            .study-hero p {{ font-size: 0.92rem; }}
            .app-topbar .brand {{ font-size: 1rem; }}
            .app-topbar .status {{ display: none; }}
            [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
                max-width: 92%;
            }}
            .st-key-toolbar_row .stButton > button,
            .st-key-toolbar_row .stDownloadButton > button {{
                font-size: 0.78rem;
                padding: 0.32rem 0.65rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_topbar(status: str = ""):
    """Slim header that replaces the old sidebar's branding — app name
    on the left, a one-line status (doc count / language) on the right
    once something has been loaded."""
    st.markdown(
        f"""
        <div class="app-topbar">
            <div class="brand"><span class="mark">📚</span> AI Research Assistant</div>
            <div class="status">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="study-hero">
            <div class="eyebrow">Research · Read · Retain</div>
            <h1>What are we studying today?</h1>
            <p>Attach a PDF or DOCX with the + button below and ask questions
            the way you would with a research partner — pull citations,
            generate study notes, flashcards, and quizzes, with the option to
            fall back to the web when your document runs out of answers.</p>
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
