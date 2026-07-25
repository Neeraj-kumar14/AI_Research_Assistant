import os

from docx import Document

# DOCX has no natural page boundary here (the whole doc loads as one
# "page"), so the cap is on total characters rather than page count.
# Same reasoning as MAX_PDF_PAGES in pdf_loader.py: cap before
# chunking/embedding, not after, so oversized uploads don't cost
# memory/CPU on the part that gets discarded anyway.
MAX_DOCX_CHARS = int(os.getenv("MAX_DOCX_CHARS", "600000"))  # ~ a few hundred pages of text


def load_docx(uploaded_file):

    doc = Document(uploaded_file)

    pages = []

    full_text = []

    for para in doc.paragraphs:

        if para.text.strip():

            full_text.append(para.text)

    text = "\n".join(full_text)
    truncated = len(text) > MAX_DOCX_CHARS

    if truncated:
        text = text[:MAX_DOCX_CHARS]

    pages.append(
        {
            "page": 1,
            "text": text,
            "source": uploaded_file.name
        }
    )

    if truncated:
        pages.append(
            {
                "page": 2,
                "text": (
                    "[Note: this document was truncated to keep the app "
                    "responsive for all users. Ask about earlier sections, "
                    "or split the file and upload the rest separately.]"
                ),
                "source": uploaded_file.name,
            }
        )

    return pages