from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


def export_notes_to_pdf(notes, filename="study_notes.pdf"):

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    story = []

    for line in notes.split("\n"):

        line = line.strip()

        if not line:
            continue

        if line.startswith("# "):

            story.append(
                Paragraph(f"<b><font size=18>{line[2:]}</font></b>", styles["Heading1"])
            )

        elif line.startswith("## "):

            story.append(
                Paragraph(f"<b><font size=15>{line[3:]}</font></b>", styles["Heading2"])
            )

        elif line.startswith("### "):

            story.append(
                Paragraph(f"<b><font size=13>{line[4:]}</font></b>", styles["Heading3"])
            )

        else:

            story.append(
                Paragraph(line, styles["BodyText"])
            )

    doc.build(story)

    return filename