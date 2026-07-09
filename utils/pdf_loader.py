from pypdf import PdfReader


def load_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    pages = []

    for page_num, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        if text:

            pages.append(
                {
                    "page": page_num,
                    "text": text,
                    "source": uploaded_file.name
                }
            )

    return pages