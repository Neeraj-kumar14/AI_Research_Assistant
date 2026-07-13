from docx import Document


def load_docx(uploaded_file):

    doc = Document(uploaded_file)

    pages = []

    full_text = []

    for para in doc.paragraphs:

        if para.text.strip():

            full_text.append(para.text)

    pages.append(
        {
            "page": 1,
            "text": "\n".join(full_text),
            "source": uploaded_file.name
        }
    )

    return pages