import streamlit as st

from utils.llm import generate_study_notes, NOTE_SECTIONS
from utils.theme import animated_loader

_SETUP_CSS = """
<style>
@keyframes notesSetupIn {
    from { opacity: 0; transform: translateY(16px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}
.notes-setup-slide {
    animation: notesSetupIn 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.notes-setup-eyebrow {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #2F6F4E;
    margin-bottom: 0.3rem;
}
.notes-setup-sub {
    color: #41507A;
    font-size: 0.94rem;
    margin-bottom: 1.2rem;
}
.notes-setup-label {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #41507A;
    margin: 1.1rem 0 0.5rem 0;
}
.notes-setup-hint {
    color: #6B6455;
    font-size: 0.78rem;
    margin: -0.3rem 0 0.4rem 0;
}
.notes-style-row .stButton > button {
    border-radius: 999px !important;
    border: 1px solid #E4E0D4 !important;
    background: #FAFAF7 !important;
    color: #1B2A4A !important;
    font-size: 0.86rem !important;
    padding: 0.4rem 0.2rem !important;
    transition: transform 0.12s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.notes-style-row .stButton > button:hover:not(:disabled) {
    border-color: #2F6F4E !important;
    transform: translateY(-1px);
}
.notes-style-row .stButton > button[kind="primary"] {
    background: #2F6F4E !important;
    border-color: #2F6F4E !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
.notes-section-grid .stCheckbox {
    background: #FAFAF7;
    border: 1px solid #E4E0D4;
    border-radius: 8px;
    padding: 0.35rem 0.6rem;
    margin-bottom: 0.4rem;
}
.notes-setup-actions .stButton > button[kind="primary"] {
    animation: notesPulseReady 2.2s ease-in-out infinite;
}
@keyframes notesPulseReady {
    0%, 100% { box-shadow: 0 0 0 0 rgba(47, 111, 78, 0.0); }
    50% { box-shadow: 0 0 0 6px rgba(47, 111, 78, 0.10); }
}
</style>
"""

_STYLES = ["Concise", "Detailed", "Exam-focused"]

_SECTION_LABELS = {
    "overview": "Overview",
    "concepts": "Important Concepts",
    "definitions": "Definitions",
    "key_points": "Key Points",
    "examples": "Examples",
    "advantages": "Advantages",
    "disadvantages": "Disadvantages",
    "applications": "Applications",
    "interview_questions": "Interview Questions",
    "common_mistakes": "Common Mistakes",
    "quick_revision": "Quick Revision",
}


def _setup_body():
    st.markdown(_SETUP_CSS, unsafe_allow_html=True)
    st.markdown('<div class="notes-setup-slide">', unsafe_allow_html=True)
    st.markdown('<div class="notes-setup-eyebrow">Study Notes · Setup</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="notes-setup-sub">Choose a style, pick which sections to include, '
        'and (optionally) a topic to focus on.</div>',
        unsafe_allow_html=True,
    )

    # ---- Style ----------------------------------------------------------
    st.markdown('<div class="notes-setup-label">Style</div>', unsafe_allow_html=True)
    st.markdown('<div class="notes-setup-hint">Concise = quick-scan bullets · Detailed = full '
                'explanations · Exam-focused = built for test prep.</div>', unsafe_allow_html=True)
    st.markdown('<div class="notes-style-row">', unsafe_allow_html=True)
    cols = st.columns(len(_STYLES))
    for col, style in zip(cols, _STYLES):
        with col:
            is_selected = st.session_state.notes_style == style
            if st.button(
                style,
                key=f"notesstyle_{style}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.notes_style = style
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Sections ---------------------------------------------------------
    st.markdown('<div class="notes-setup-label">Sections to include</div>', unsafe_allow_html=True)
    st.markdown('<div class="notes-section-grid">', unsafe_allow_html=True)
    section_cols = st.columns(2)
    for i, (key, _heading) in enumerate(NOTE_SECTIONS):
        with section_cols[i % 2]:
            checked = st.checkbox(
                _SECTION_LABELS.get(key, key),
                value=key in st.session_state.notes_sections,
                key=f"notes_section_{key}",
            )
            if checked:
                st.session_state.notes_sections.add(key)
            else:
                st.session_state.notes_sections.discard(key)
    st.markdown("</div>", unsafe_allow_html=True)

    sel_count = len(st.session_state.notes_sections)
    total_count = len(NOTE_SECTIONS)
    col_all, col_none = st.columns(2)
    with col_all:
        if st.button("Select all", use_container_width=True, disabled=sel_count == total_count):
            st.session_state.notes_sections = {key for key, _ in NOTE_SECTIONS}
            st.rerun()
    with col_none:
        if st.button("Clear all", use_container_width=True, disabled=sel_count == 0):
            st.session_state.notes_sections = set()
            st.rerun()

    # ---- Optional focus topic ---------------------------------------------
    st.markdown('<div class="notes-setup-label">Focus on a topic (optional)</div>', unsafe_allow_html=True)
    st.text_input(
        "Focus topic",
        key="notes_focus",
        placeholder="e.g. Chapter 3, photosynthesis, key dates...",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Actions ------------------------------------------------------------
    st.markdown('<div class="notes-setup-actions">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Cancel", use_container_width=True, key="notes_cancel"):
            st.session_state.notes_stage = None
            st.rerun()
    with col2:
        if st.button(
            "Generate notes",
            use_container_width=True,
            type="primary",
            key="notes_generate",
            disabled=sel_count == 0,
        ):
            loader = st.empty()
            loader.markdown(
                animated_loader(
                    ["Reading your document", "Organizing key ideas", "Writing your notes", "Polishing formatting"]
                ),
                unsafe_allow_html=True,
            )
            try:
                notes = generate_study_notes(
                    st.session_state.pdf_text,
                    language=st.session_state.document_language,
                    style=st.session_state.notes_style,
                    sections=list(st.session_state.notes_sections),
                    focus=st.session_state.notes_focus.strip() or None,
                )
            except Exception as e:
                loader.empty()
                st.error(f"Groq Error:\n\n{e}")
                st.stop()
            loader.empty()

            st.session_state.study_notes = notes
            st.session_state.messages.append({"role": "user", "content": "📝 Generate Study Notes"})
            st.session_state.messages.append({"role": "assistant", "content": notes})
            st.session_state.notes_stage = None
            st.rerun()
    if sel_count == 0:
        st.caption("Pick at least one section to generate.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


@st.dialog("Set up your study notes", width="large")
def _notes_setup_dialog():
    _setup_body()


def render_notes_setup():
    """Opens the notes setup as a floating modal window (st.dialog),
    matching the flashcard setup pattern."""
    _notes_setup_dialog()
