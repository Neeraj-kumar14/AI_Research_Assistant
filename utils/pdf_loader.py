import fitz  # PyMuPDF


def load_pdf(uploaded_file):
    """PyMuPDF instead of pypdf: noticeably faster text extraction,
    which matters most on large (20-50MB) multi-page documents where
    this loop is run once per page.
    """

    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []

    for page_num, page in enumerate(doc, start=1):

        text = page.get_text()

        if text and text.strip():

            pages.append(
                {
                    "page": page_num,
                    "text": text,
                    "source": uploaded_file.name
                }
            )

    doc.close()

    return pages
