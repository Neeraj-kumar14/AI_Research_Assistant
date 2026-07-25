import os

import fitz  # PyMuPDF
from PIL import Image

from utils.ocr import extract_text_from_image

# Hard ceiling on pages processed per upload. On a free/shared, RAM-
# limited deployment with many concurrent users, one very large PDF
# (hundreds of pages) can single-handedly blow the process's memory
# budget while it's being chunked and embedded. Truncating here (not
# after chunking/embedding) means the expensive work is never done on
# the part we'd discard anyway. Override via MAX_PDF_PAGES env var.
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "300"))

# Separate, much lower cap on how many pages get OCR'd per upload.
# OCR (EasyOCR on CPU, no GPU) is far slower per page than the plain
# text extraction path — a scanned 300-page PDF could otherwise take
# many minutes and monopolize a CPU slot for that whole time on a
# shared deployment. Pages beyond this cap that have no text layer are
# just skipped (same as before this fix existed) rather than OCR'd.
# Override via MAX_OCR_PAGES env var.
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "30"))

# Render resolution for OCR fallback. 2x zoom (~150 DPI equivalent)
# balances OCR accuracy against memory/time per page; going much higher
# meaningfully slows OCR for little accuracy gain on typical scans.
_OCR_ZOOM = 2.0


def _ocr_page(page):
    """Render a page to an image and run it through OCR. Used only for
    pages with no extractable text layer (i.e. scanned pages)."""
    pix = page.get_pixmap(matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return extract_text_from_image(image)


def load_pdf(uploaded_file):
    """PyMuPDF instead of pypdf: noticeably faster text extraction,
    which matters most on large (20-50MB) multi-page documents where
    this loop is run once per page.

    Pages with a real text layer use that text directly. Pages with no
    text layer at all (scanned/image-only pages) fall back to OCR, up
    to MAX_OCR_PAGES — beyond that they're skipped, same as if OCR
    didn't exist, so one huge scanned document can't stall the app for
    everyone.
    """

    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages = []
    total_pages = doc.page_count
    truncated = total_pages > MAX_PDF_PAGES
    ocr_pages_used = 0
    ocr_skipped = 0

    for page_num, page in enumerate(doc, start=1):

        if page_num > MAX_PDF_PAGES:
            break

        text = page.get_text()

        if text and text.strip():
            pages.append(
                {
                    "page": page_num,
                    "text": text,
                    "source": uploaded_file.name
                }
            )
            continue

        # No text layer — likely a scanned page. Fall back to OCR, up
        # to the per-document OCR cap.
        if ocr_pages_used < MAX_OCR_PAGES:
            ocr_pages_used += 1
            ocr_text = _ocr_page(page)
            if ocr_text and ocr_text.strip():
                pages.append(
                    {
                        "page": page_num,
                        "text": ocr_text,
                        "source": uploaded_file.name
                    }
                )
        else:
            ocr_skipped += 1

    doc.close()

    if truncated:
        pages.append(
            {
                "page": MAX_PDF_PAGES + 1,
                "text": (
                    f"[Note: this document has {total_pages} pages. Only the "
                    f"first {MAX_PDF_PAGES} were processed to keep the app "
                    f"responsive for all users. Ask about earlier sections, "
                    f"or split the file and upload the rest separately.]"
                ),
                "source": uploaded_file.name,
            }
        )

    if ocr_skipped:
        pages.append(
            {
                "page": pages[-1]["page"] + 1 if pages else 1,
                "text": (
                    f"[Note: {ocr_skipped} scanned page(s) had no text layer "
                    f"and were not OCR'd because this upload hit the "
                    f"{MAX_OCR_PAGES}-page OCR limit. Their content is "
                    f"missing from what you can ask about.]"
                ),
                "source": uploaded_file.name,
            }
        )

    return pages
