"""
Design system for the AI Research Assistant — v2.

Concept: a floating study console at night. Deep-space navy/black base,
glassmorphic panels (blurred, translucent, thin light borders) that look
like they're hovering in 3D space, and a cyan -> violet -> pink signal
gradient used for anything "alive" (progress, XP, active state). Headings
use a squared-off geometric display face for a HUD feel; body stays a
clean humanist sans for readability; mono is reserved for
telemetry-style read-outs (citations, stats, timers) — because a
citation or a score is data, not prose.

Signature element: the hero renders as a tilted glass console floating
over an animated perspective grid floor with drifting neon orbs — the
"3D landing page" — and CSS custom properties (--paper-raised, --ink,
etc.) are exposed at :root so other components that already reference
`var(--paper-raised, #fff)` (e.g. the quiz setup dialog) pick up the
dark theme automatically without needing their own edits.
"""

import streamlit as st

# ---- Design tokens --------------------------------------------------------

COLOR_BG = "#05060F"            # page background — near-black navy
COLOR_BG_2 = "#0B0F22"          # secondary background stop (gradient)
COLOR_INK = "#EAF0FF"           # primary text — near-white, cool
COLOR_INK_SOFT = "#9FB0D9"      # secondary text — muted periwinkle
COLOR_PAPER_RAISED = "rgba(255,255,255,0.055)"   # glass panel fill
COLOR_PAPER_MUTED = "rgba(255,255,255,0.035)"    # dimmer glass fill
COLOR_BORDER = "rgba(255,255,255,0.14)"
COLOR_ACCENT = "#22D3EE"        # cyan — primary actions / links
COLOR_ACCENT_DARK = "#0FA8C4"
COLOR_VIOLET = "#7C5CFF"        # secondary accent — hero glow, badges
COLOR_PINK = "#FF3EA5"          # tertiary accent — gamified highlights
COLOR_GOLD = "#FFD166"          # XP / streak / emphasis
COLOR_SUCCESS = "#3DDC97"
COLOR_ERROR = "#FF5C7A"

FONT_DISPLAY = "'Space Grotesk', 'Sora', -apple-system, sans-serif"
FONT_BODY = "'Inter', -apple-system, sans-serif"
FONT_MONO = "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace"


def inject_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {{
            --bg: {COLOR_BG};
            --ink: {COLOR_INK};
            --ink-soft: {COLOR_INK_SOFT};
            --paper-raised: {COLOR_PAPER_RAISED};
            --paper-muted: {COLOR_PAPER_MUTED};
            --border: {COLOR_BORDER};
            --accent: {COLOR_ACCENT};
            --violet: {COLOR_VIOLET};
            --pink: {COLOR_PINK};
            --gold: {COLOR_GOLD};
            --success: {COLOR_SUCCESS};
            --error: {COLOR_ERROR};
        }}

        html, body, [class*="css"] {{
            font-family: {FONT_BODY};
            color: {COLOR_INK};
        }}

        .stApp {{
            background:
                radial-gradient(ellipse 900px 500px at 15% -10%, rgba(124,92,255,0.20), transparent 60%),
                radial-gradient(ellipse 800px 500px at 110% 10%, rgba(34,211,238,0.14), transparent 60%),
                linear-gradient(180deg, {COLOR_BG} 0%, {COLOR_BG_2} 100%);
            background-attachment: fixed;
        }}

        /* ---- Hide default Streamlit chrome ---- */
        .stAppDeployButton {{ display: none !important; }}
        footer {{ visibility: hidden; height: 0; }}
        header[data-testid="stHeader"] {{ background: transparent; }}
        #MainMenu {{ visibility: hidden; }}

        .block-container {{
            max-width: 54rem;
            margin: 0 auto;
            padding-top: 1.5rem;
            padding-bottom: 9rem;
        }}

        /* ---- Headings ---- */
        h1, h2, h3 {{
            font-family: {FONT_DISPLAY} !important;
            color: {COLOR_INK} !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
        }}
        p, span, div, label {{ color: {COLOR_INK}; }}
        a {{ color: {COLOR_ACCENT}; }}

        /* ---- Top bar — glass nav ---- */
        .app-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 54rem;
            margin: 0 auto 0.9rem auto;
            padding: 0.65rem 1.1rem;
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 16px;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 8px 28px rgba(0,0,0,0.35);
        }}
        .app-topbar .brand {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-family: {FONT_DISPLAY};
            font-weight: 600;
            font-size: 1.08rem;
            color: {COLOR_INK};
        }}
        .app-topbar .brand .mark {{
            width: 30px; height: 30px;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, {COLOR_ACCENT}, {COLOR_VIOLET});
            color: #05060F;
            border-radius: 9px;
            font-size: 1rem;
            box-shadow: 0 0 16px rgba(34,211,238,0.5);
        }}
        .app-topbar .status {{
            font-family: {FONT_MONO};
            font-size: 0.74rem;
            color: {COLOR_INK_SOFT};
            letter-spacing: 0.02em;
        }}

        /* ---- Sticky header: topbar + study-tool pills stay put while
               you scroll through a long summary/notes/chat, instead of
               having to scroll back up to reach them each time. ---- */
        .st-key-sticky_header {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: linear-gradient(180deg, {COLOR_BG} 78%, rgba(5,6,15,0) 100%);
            backdrop-filter: blur(10px);
            padding-top: 0.4rem;
            padding-bottom: 0.5rem;
            margin-bottom: 0.3rem;
        }}

        /* ---- Study-tool pills (toolbar row once a doc is loaded) ---- */
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
            backdrop-filter: blur(10px);
        }}
        .st-key-toolbar_row .stButton > button:hover,
        .st-key-toolbar_row .stDownloadButton > button:hover {{
            border-color: {COLOR_ACCENT};
            color: {COLOR_ACCENT};
            box-shadow: 0 0 12px rgba(34,211,238,0.25);
        }}
        .st-key-toolbar_row {{ margin-bottom: 0.6rem; }}

        /* ==========================================================
           Chat messages
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
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 16px;
            padding: 0.6rem 1rem;
            max-width: 82%;
            margin-left: auto;
            backdrop-filter: blur(10px);
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {{
            padding: 0.15rem 0;
        }}
        [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {{
            box-shadow: none;
        }}

        /* ==========================================================
           3D hero — the "landing page" console
           ========================================================== */
        .hero-3d-scene {{
            position: relative;
            perspective: 1400px;
            padding: 3.2rem 0 2.6rem 0;
            margin-bottom: 1.6rem;
            overflow: visible;
        }}
        .hero-grid-floor {{
            position: absolute;
            left: 50%;
            bottom: -20px;
            width: 160%;
            height: 220px;
            transform: translateX(-50%) rotateX(78deg);
            background-image:
                linear-gradient(rgba(34,211,238,0.28) 1px, transparent 1px),
                linear-gradient(90deg, rgba(124,92,255,0.28) 1px, transparent 1px);
            background-size: 42px 42px;
            -webkit-mask-image: linear-gradient(to top, black, transparent 85%);
            mask-image: linear-gradient(to top, black, transparent 85%);
            animation: heroGridDrift 7s linear infinite;
            pointer-events: none;
            z-index: 0;
        }}
        @keyframes heroGridDrift {{
            from {{ background-position: 0 0, 0 0; }}
            to   {{ background-position: 0 42px, 42px 0; }}
        }}
        .hero-orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(50px);
            opacity: 0.55;
            pointer-events: none;
            z-index: 0;
            animation: heroOrbFloat 9s ease-in-out infinite;
        }}
        .hero-orb-1 {{ width: 260px; height: 260px; left: -60px; top: 10px; background: {COLOR_VIOLET}; }}
        .hero-orb-2 {{ width: 220px; height: 220px; right: -50px; top: 40px; background: {COLOR_ACCENT}; animation-delay: -3s; }}
        .hero-orb-3 {{ width: 180px; height: 180px; right: 20%; bottom: -40px; background: {COLOR_PINK}; opacity: 0.35; animation-delay: -6s; }}
        @keyframes heroOrbFloat {{
            0%, 100% {{ transform: translateY(0) scale(1); }}
            50% {{ transform: translateY(-18px) scale(1.06); }}
        }}
        .study-hero {{
            position: relative;
            z-index: 1;
            padding: 2.4rem 2.6rem;
            background: linear-gradient(155deg, rgba(255,255,255,0.075), rgba(255,255,255,0.02));
            border: 1px solid {COLOR_BORDER};
            border-radius: 22px;
            backdrop-filter: blur(22px);
            -webkit-backdrop-filter: blur(22px);
            box-shadow:
                0 24px 60px rgba(0,0,0,0.45),
                inset 0 1px 0 rgba(255,255,255,0.14);
            transform: rotateX(3deg);
            transform-style: preserve-3d;
            transition: transform 0.5s cubic-bezier(0.22,1,0.36,1);
            animation: heroSettle 0.9s cubic-bezier(0.16,1,0.3,1);
        }}
        .study-hero:hover {{ transform: rotateX(0deg) translateY(-4px); }}
        @keyframes heroSettle {{
            from {{ opacity: 0; transform: rotateX(14deg) translateY(26px); }}
            to   {{ opacity: 1; transform: rotateX(3deg) translateY(0); }}
        }}
        .study-hero .eyebrow {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            background: linear-gradient(90deg, {COLOR_ACCENT}, {COLOR_VIOLET});
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 0.5rem;
        }}
        .study-hero h1 {{
            font-size: 2.35rem !important;
            margin: 0 0 0.6rem 0 !important;
            background: linear-gradient(100deg, #FFFFFF 30%, {COLOR_ACCENT} 75%, {COLOR_VIOLET} 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }}
        .study-hero p {{
            font-size: 1.02rem;
            color: {COLOR_INK_SOFT};
            max-width: 620px;
            margin: 0;
            line-height: 1.55;
        }}

        /* ---- Feature grid — floating 3D glass tiles ---- */
        .feature-card {{
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 16px;
            padding: 1.2rem 1.3rem;
            height: 100%;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            transform-style: preserve-3d;
            transition: transform 0.35s cubic-bezier(0.22,1,0.36,1), box-shadow 0.35s ease, border-color 0.35s ease;
            box-shadow: 0 10px 26px rgba(0,0,0,0.28);
        }}
        .feature-card:hover {{
            transform: perspective(700px) rotateX(6deg) rotateY(-6deg) translateY(-5px);
            border-color: rgba(34,211,238,0.45);
            box-shadow: 0 18px 40px rgba(0,0,0,0.4), 0 0 22px rgba(34,211,238,0.18);
        }}
        .feature-card .ico {{
            font-size: 1.35rem;
            margin-bottom: 0.4rem;
            display: block;
            filter: drop-shadow(0 0 8px rgba(34,211,238,0.35));
        }}
        .feature-card .title {{
            font-family: {FONT_DISPLAY};
            font-weight: 600;
            font-size: 0.96rem;
            color: {COLOR_INK};
            margin-bottom: 0.25rem;
        }}
        .feature-card .desc {{
            font-size: 0.83rem;
            color: {COLOR_INK_SOFT};
            line-height: 1.45;
        }}

        /* ---- Section label ---- */
        .section-label {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: {COLOR_INK_SOFT};
            border-bottom: 1px solid {COLOR_BORDER};
            padding-bottom: 0.4rem;
            margin: 1.4rem 0 0.9rem 0;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: rgba(5,6,15,0.92);
            border-right: 1px solid {COLOR_BORDER};
            backdrop-filter: blur(16px);
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
            color: {COLOR_ACCENT};
        }}

        /* ==========================================================
           Pinned composer bar
           ========================================================== */
        [data-testid="stBottomBlockContainer"] {{
            background: {COLOR_BG};
            padding-top: 0.6rem;
        }}
        [data-testid="stBottomBlockContainer"] > div {{
            max-width: 54rem;
            margin: 0 auto;
        }}
        [data-testid="stChatInput"] {{
            border-radius: 22px !important;
            border: 1px solid rgba(34,211,238,0.3) !important;
            background: #0B0F22 !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }}
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] textarea {{
            background: transparent !important;
        }}
        [data-testid="stChatInput"] textarea {{
            font-family: {FONT_BODY} !important;
            color: {COLOR_INK} !important;
        }}
        [data-testid="stChatInput"] textarea::placeholder {{
            color: {COLOR_INK_SOFT} !important;
            opacity: 1 !important;
        }}
        [data-testid="stChatInput"] button {{
            background: transparent !important;
            color: {COLOR_INK_SOFT} !important;
        }}
        [data-testid="stChatInput"] button:hover {{
            color: {COLOR_ACCENT} !important;
        }}
        [data-testid="stChatInputSubmitButton"] {{
            background: linear-gradient(120deg, {COLOR_ACCENT}, {COLOR_VIOLET}) !important;
            color: #05060F !important;
        }}
        [data-testid="stChatInputSubmitButton"]:hover {{ color: #05060F !important; }}
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
            color: {COLOR_ACCENT} !important;
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
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 999px;
            padding: 0.22rem 0.7rem 0.22rem 0.6rem;
            color: {COLOR_INK_SOFT};
        }}
        .doc-chip .dot {{
            width: 6px; height: 6px; border-radius: 50%;
            background: {COLOR_ACCENT};
            box-shadow: 0 0 6px {COLOR_ACCENT};
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
            background: #0B0F22 !important;
        }}

        /* Primary action buttons anywhere */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(120deg, {COLOR_ACCENT}, {COLOR_VIOLET}) !important;
            color: #05060F !important;
            border: none !important;
            border-radius: 8px;
            font-weight: 600 !important;
            box-shadow: 0 0 16px rgba(34,211,238,0.25);
        }}
        .stButton > button[kind="primary"]:hover {{
            filter: brightness(1.08);
            box-shadow: 0 0 22px rgba(34,211,238,0.4);
        }}
        .stButton > button[kind="secondary"] {{
            background: {COLOR_PAPER_RAISED} !important;
            color: {COLOR_INK} !important;
            border: 1px solid {COLOR_BORDER} !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            border-color: {COLOR_ACCENT} !important;
            color: {COLOR_ACCENT} !important;
        }}

        /* ---- Source "index card" citations ---- */
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
            border-radius: 6px;
            padding: 0.3rem 0.6rem;
            color: {COLOR_INK_SOFT};
            box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        }}
        .index-card.web {{ border-left-color: {COLOR_ACCENT}; }}
        .index-card a {{ color: {COLOR_INK_SOFT}; text-decoration: none; }}
        .index-card a:hover {{ color: {COLOR_ACCENT}; text-decoration: underline; }}

        /* ---- Quiz / flashcard fallback labels (fully re-themed in
               their own component files, kept here as a safety net) ---- */
        .quiz-card {{
            background: {COLOR_PAPER_RAISED};
            border: 1px solid {COLOR_BORDER};
            border-radius: 14px;
            padding: 1.4rem 1.5rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(14px);
        }}
        .quiz-progress-label {{
            font-family: {FONT_MONO};
            font-size: 0.75rem;
            color: {COLOR_INK_SOFT};
            letter-spacing: 0.05em;
        }}
        .flash-q {{
            font-family: {FONT_MONO};
            font-size: 0.72rem;
            color: {COLOR_ACCENT};
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        [data-testid="stChatMessage"] {{ border-radius: 12px; }}
        .stCaption, div[data-testid="stCaptionContainer"] {{ font-family: {FONT_MONO} !important; color: {COLOR_INK_SOFT} !important; }}
        [data-testid="stMarkdownContainer"] {{ color: {COLOR_INK}; }}
        [data-testid="stMetricValue"] {{ color: {COLOR_INK} !important; }}
        [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] {{
            background: {COLOR_PAPER_RAISED} !important;
            border-color: {COLOR_BORDER} !important;
        }}
        input, textarea {{ color: {COLOR_INK} !important; }}
        hr {{ border-color: {COLOR_BORDER} !important; }}

        /* ==========================================================
           Floating modals (st.dialog) & popovers (st.popover) —
           Streamlit renders these in a portal with its own light
           default panel, so without an explicit override they show up
           as a plain white card even though the rest of the app is
           dark. This re-skins every such panel to match the glass
           console look used everywhere else.
           ========================================================== */
        div[data-testid="stDialog"] {{
            background: rgba(2,3,10,0.72) !important;
            backdrop-filter: blur(4px);
        }}
        div[data-testid="stDialog"] > div,
        div[data-testid="stDialog"] div[role="dialog"] {{
            background: linear-gradient(160deg, #0D1024 0%, #05060F 100%) !important;
            border: 1px solid {COLOR_BORDER} !important;
            border-radius: 20px !important;
            box-shadow: 0 30px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.08) !important;
        }}
        div[data-testid="stDialog"] * {{
            color: {COLOR_INK};
        }}
        div[data-testid="stDialog"] p,
        div[data-testid="stDialog"] span,
        div[data-testid="stDialog"] label {{
            color: {COLOR_INK_SOFT};
        }}
        div[data-testid="stDialog"] h1,
        div[data-testid="stDialog"] h2,
        div[data-testid="stDialog"] h3,
        div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] h1 {{
            color: {COLOR_INK} !important;
            font-family: {FONT_DISPLAY} !important;
        }}
        div[data-testid="stDialog"] [data-testid="baseButton-headerNoPadding"],
        div[data-testid="stDialog"] button[aria-label="Close"] {{
            color: {COLOR_INK_SOFT} !important;
            background: transparent !important;
        }}
        div[data-testid="stDialog"] [data-baseweb="input"],
        div[data-testid="stDialog"] [data-baseweb="textarea"],
        div[data-testid="stDialog"] input,
        div[data-testid="stDialog"] textarea {{
            background: {COLOR_PAPER_RAISED} !important;
            border-color: {COLOR_BORDER} !important;
            color: {COLOR_INK} !important;
        }}
        div[data-testid="stDialog"] hr {{ border-color: {COLOR_BORDER} !important; }}

        /* st.popover panels ("Manage documents", the ⚙ search-mode
           options) render via BaseWeb into the same body-level portal
           as the dialog, so they need the same treatment. */
        div[data-baseweb="popover"] {{
            background: transparent !important;
        }}
        div[data-baseweb="popover"] > div,
        div[data-testid="stPopoverBody"] {{
            background: linear-gradient(160deg, #0D1024 0%, #05060F 100%) !important;
            border: 1px solid {COLOR_BORDER} !important;
            border-radius: 14px !important;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5) !important;
        }}
        div[data-baseweb="popover"] * {{ color: {COLOR_INK}; }}
        div[data-baseweb="popover"] .stCaption,
        div[data-baseweb="popover"] p {{ color: {COLOR_INK_SOFT} !important; }}
        div[data-baseweb="popover"] [data-baseweb="radio"] label {{ color: {COLOR_INK} !important; }}

        /* ---- Instant press feedback — every button reacts the moment
               it's clicked instead of only updating once the rerun
               finishes, so a slow LLM call doesn't read as "did nothing". ---- */
        .stButton > button, .stDownloadButton > button {{
            transition: transform 0.08s ease, filter 0.12s ease, box-shadow 0.12s ease, border-color 0.15s ease;
        }}
        .stButton > button:active, .stDownloadButton > button:active {{
            transform: scale(0.965);
            filter: brightness(0.94);
        }}

        /* ---- Study-tool pill row: allow wrapping instead of
               squeezing every pill into one fixed-width line ---- */
        .st-key-toolbar_row [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            row-gap: 0.5rem;
        }}
        .st-key-toolbar_row [data-testid="stHorizontalBlock"] > div {{
            flex: 1 1 auto !important;
            min-width: 8.2rem;
            width: auto !important;
        }}

        /* ==========================================================
           Responsive
           ========================================================== */
        @media (max-width: 640px) {{
            .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; padding-bottom: 10rem; }}
            .hero-3d-scene {{ padding: 1.6rem 0 1.4rem 0; }}
            .study-hero {{ padding: 1.5rem 1.3rem; transform: none; }}
            .study-hero h1 {{ font-size: 1.55rem !important; }}
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
        @media (prefers-reduced-motion: reduce) {{
            .hero-grid-floor, .hero-orb, .study-hero {{ animation: none !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_scroll_preserver():
    """Every button click triggers a full Streamlit rerun, which by
    default snaps the page back to the top — jarring once someone has
    scrolled down into a long chat/notes/quiz. This remembers the
    scroll position (sessionStorage, so it survives the rerun) and
    restores it right after the new page paints.

    Runs inside a components.html iframe (not a plain st.markdown
    <script>, which browsers won't execute) and reaches back out to
    the real page via window.parent, same pattern already used by the
    flashcard swipe handler."""
    from streamlit.components.v1 import html as components_html

    components_html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const KEY = "ara_scroll_y";

            function getScroller() {
                return doc.querySelector('section[data-testid="stMain"]') || doc.scrollingElement;
            }

            function save() {
                const el = getScroller();
                if (el) sessionStorage.setItem(KEY, String(el.scrollTop));
            }

            function restore() {
                const el = getScroller();
                const y = sessionStorage.getItem(KEY);
                if (el && y !== null) el.scrollTop = parseInt(y, 10);
            }

            const el = getScroller();
            if (el && !el.dataset.scrollBound) {
                el.dataset.scrollBound = "1";
                el.addEventListener("scroll", function() {
                    clearTimeout(window.__araScrollTimer);
                    window.__araScrollTimer = setTimeout(save, 100);
                });
            }
            restore();
            setTimeout(restore, 80);
            setTimeout(restore, 250);
        })();
        </script>
        """,
        height=0,
    )


def render_topbar(status: str = ""):
    """Slim glass nav bar — app name on the left, a one-line status
    (doc count / language) on the right once something has been loaded."""
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
    """The 3D landing hero: a tilted glass console floating over an
    animated perspective grid with drifting neon orbs."""
    st.markdown(
        """
        <div class="hero-3d-scene">
            <div class="hero-orb hero-orb-1"></div>
            <div class="hero-orb hero-orb-2"></div>
            <div class="hero-orb hero-orb-3"></div>
            <div class="hero-grid-floor"></div>
            <div class="study-hero">
                <div class="eyebrow">Research · Read · Retain</div>
                <h1>What are we studying today?</h1>
                <p>Attach a PDF or DOCX with the + button below and ask questions
                the way you would with a research partner — pull citations,
                generate study notes, and turn the material into flashcards and
                quizzes that actually keep you on your toes, with the option to
                fall back to the web when your document runs out of answers.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_grid():
    features = [
        ("📄", "Chat with your document", "Ask questions and get answers grounded in the exact page they came from."),
        ("🌐", "Hybrid web fallback", "When the document doesn't have it, the assistant searches the web automatically."),
        ("📝", "Study notes", "Turn any document into structured, exam-ready notes."),
        ("🧠", "Flashcards", "Swipeable, gamified Q&A cards with streaks, XP, and combo bonuses."),
        ("❓", "Interactive quiz", "Timed multiple-choice with live scoring, streak bonuses, and confetti."),
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
    Not tied to real progress — it's a perceived-progress indicator so a
    10-20s wait doesn't feel dead."""
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
        border: 1px solid {COLOR_BORDER};
    }}
    .loader-bar {{
        width: 35%; height: 100%; border-radius: 6px;
        background: linear-gradient(90deg, {COLOR_ACCENT}, {COLOR_VIOLET}, {COLOR_PINK});
        animation: loaderMove 1.3s ease-in-out infinite;
        box-shadow: 0 0 10px rgba(34,211,238,0.5);
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
