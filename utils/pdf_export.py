import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_UNDERSCORE_BOLD_RE = re.compile(r"__(.+?)__")
_ITALIC_STAR_RE = re.compile(r"\*(.+?)\*")
_ITALIC_UNDERSCORE_RE = re.compile(r"(?<!\w)_(.+?)_(?!\w)")
_NUMBERED_RE = re.compile(r"^(\d+)[.)]\s+(.*)")
_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


def _escape_xml(text: str) -> str:
    """ReportLab's Paragraph parses a small XML/HTML-like markup, so raw
    '&', '<', '>' in the source text have to be escaped BEFORE any of our
    own <b>/<i> tags are added below -- otherwise either the source text
    breaks the parser, or (if escaped after) our own tags would get
    escaped right along with it."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _convert_inline_markdown(text: str) -> str:
    """Converts inline **bold**, __bold__, *italic*, and _italic_ spans
    into the <b>/<i> tags ReportLab's Paragraph understands. This is the
    core of the fix: previously these markers passed straight through
    as literal asterisks/underscores instead of actually formatting the
    text."""
    text = _escape_xml(text)
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _UNDERSCORE_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _ITALIC_STAR_RE.sub(r"<i>\1</i>", text)
    text = _ITALIC_UNDERSCORE_RE.sub(r"<i>\1</i>", text)
    return text


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="NotesBullet",
            parent=styles["BodyText"],
            leftIndent=16,
            bulletIndent=4,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="NotesNumbered",
            parent=styles["BodyText"],
            leftIndent=16,
            spaceAfter=4,
        )
    )
    styles["BodyText"].spaceAfter = 6
    return styles


def export_notes_to_pdf(notes, filename="study_notes.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = _build_styles()
    story = []

    for raw_line in notes.split("\n"):
        line = raw_line.strip()

        if not line:
            continue

        if _HR_RE.match(line):
            story.append(Spacer(1, 10))
            continue

        if line.startswith("# "):
            story.append(
                Paragraph(f"<b><font size=18>{_convert_inline_markdown(line[2:])}</font></b>", styles["Heading1"])
            )
            continue

        if line.startswith("## "):
            story.append(
                Paragraph(f"<b><font size=15>{_convert_inline_markdown(line[3:])}</font></b>", styles["Heading2"])
            )
            continue

        if line.startswith("### "):
            story.append(
                Paragraph(f"<b><font size=13>{_convert_inline_markdown(line[4:])}</font></b>", styles["Heading3"])
            )
            continue

        if line.startswith(("- ", "* ")):
            story.append(
                Paragraph(f"\u2022  {_convert_inline_markdown(line[2:])}", styles["NotesBullet"])
            )
            continue

        numbered_match = _NUMBERED_RE.match(line)
        if numbered_match:
            number, rest = numbered_match.groups()
            story.append(
                Paragraph(f"{number}.  {_convert_inline_markdown(rest)}", styles["NotesNumbered"])
            )
            continue

        story.append(Paragraph(_convert_inline_markdown(line), styles["BodyText"]))

    doc.build(story)

    return filename
