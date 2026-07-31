import os
from collections import Counter

import fitz  # PyMuPDF
from PIL import Image

from utils.ocr import extract_text_from_image
from utils.llm import transcribe_handwriting
from utils.mistral_ocr import extract_text_from_image as mistral_ocr_extract
from utils.mistral_ocr import is_available as mistral_ocr_available

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

# Render resolution for OCR fallback. 3x zoom (~216 DPI equivalent)
# gives EasyOCR meaningfully more pixels per character than the old 2x
# (~150 DPI) — small body text and footnotes were previously landing
# right at the edge of what the detector can read reliably. Override
# via OCR_ZOOM if this is too slow/memory-heavy for your deployment.
_OCR_ZOOM = float(os.getenv("OCR_ZOOM", "3.0"))

# A page can have a real text layer that's essentially useless for
# OCR purposes — e.g. a single "3" page-number, or a couple of stray
# characters from a decorative header — while the actual body content
# is a scanned image. Treating any non-empty text() as "this page is
# fine, skip OCR" (the old behavior) silently dropped that content.
# Below this many characters, the text layer is treated as absent and
# the page falls through to OCR instead. Override via
# MIN_TEXT_LAYER_CHARS.
MIN_TEXT_LAYER_CHARS = int(os.getenv("MIN_TEXT_LAYER_CHARS", "20"))

# A text layer can "exist" (pass the character-count check above) and
# still be unusable garbage. The most common cause: the PDF's embedded
# font has a broken or missing ToUnicode CMap, so PyMuPDF extracts a
# character for every glyph, but almost all of those characters decode
# to the *same wrong letter* — e.g. a full page of real body text comes
# back as a wall of "IIIIIIII IIIII IIIIIIII". This happens with PDFs
# produced by some "image/notes to PDF" converters and isn't rare.
# Since the page's rendered pixels are still fine, the fix is to detect
# this case and treat it the same as "no text layer" so the page falls
# through to OCR below, instead of silently feeding garbage into the
# LLM (which then hallucinates or reports the document is meaningless).
#
# Real text in any language never has one letter dominate this heavily
# — even highly repetitive prose tops out with its most common letter
# around 12-15% of all letters (measured on English/Hindi samples). A
# ratio at or above this threshold is a reliable sign of a font-mapping
# bug, not real content. Override via GARBLED_TEXT_DOMINANT_CHAR_RATIO.
GARBLED_TEXT_DOMINANT_CHAR_RATIO = float(os.getenv("GARBLED_TEXT_DOMINANT_CHAR_RATIO", "0.35"))

# Below this many letters, frequency ratios are too noisy to judge
# reliably (a short heading can legitimately repeat one letter a lot).
GARBLED_TEXT_MIN_LETTERS = int(os.getenv("GARBLED_TEXT_MIN_LETTERS", "30"))

# EasyOCR is a printed/scene-text engine — it's unreliable on cursive
# handwriting almost regardless of preprocessing. Below this length,
# a vision-capable chat model is tried as a second pass before giving
# up on the page. Override via MIN_OCR_RESULT_CHARS.
MIN_OCR_RESULT_CHARS = int(os.getenv("MIN_OCR_RESULT_CHARS", "20"))

# Length alone misses a common failure mode: on cursive handwriting,
# EasyOCR often produces a long string of confident-*looking* garbage
# (misread strokes as random letters/digits/Devanagari) rather than a
# short one — long enough to pass the length check above, but wrong
# throughout. Mean detection confidence catches this: handwriting
# misreads reliably score low even when the resulting text is long.
# Below this, the page is treated as needing the vision fallback too.
# Override via OCR_LOW_CONFIDENCE_FALLBACK.
LOW_CONFIDENCE_FALLBACK_THRESHOLD = float(os.getenv("OCR_LOW_CONFIDENCE_FALLBACK", "0.55"))

# Whether to even attempt the vision-model fallback at all. It costs an
# extra LLM call per page that trips the threshold above, so it can be
# disabled (e.g. no Groq vision access, or to save quota) via
# ENABLE_HANDWRITING_FALLBACK=false.
_ENABLE_HANDWRITING_FALLBACK = os.getenv("ENABLE_HANDWRITING_FALLBACK", "true").lower() != "false"


def _is_garbled_text(text: str) -> bool:
    """True if `text` looks like corrupted output from a broken font
    mapping rather than real content (see GARBLED_TEXT_DOMINANT_CHAR_RATIO
    above for why this happens and why the ratio check is reliable)."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < GARBLED_TEXT_MIN_LETTERS:
        return False
    top_count = Counter(letters).most_common(1)[0][1]
    return (top_count / len(letters)) >= GARBLED_TEXT_DOMINANT_CHAR_RATIO


def _ocr_page(page):
    """Render a page to an image and run it through OCR. Used for
    pages with no extractable text layer, or one too sparse to be the
    real page content (i.e. scanned pages).

    Three tiers, tried in order, each only reached if the previous one
    looks unreliable:

    1. EasyOCR — free, offline, no API call. Always tried first.
    2. Mistral OCR — a paid API call, but a stronger general-purpose
       document OCR engine, notably on real-world (not clean/scanned-
       in-a-scanner) Hindi/Marathi/Tamil/etc. pages, which is exactly
       where EasyOCR is weakest. Only reached if configured
       (MISTRAL_API_KEY set) and EasyOCR's own result looks
       unreliable.
    3. The Groq vision handwriting model — last resort, mainly for
       genuinely cursive handwriting that neither OCR engine above was
       trained on.

    "Looks unreliable" is EasyOCR's result being short OR its own mean
    detection confidence being low. Checking confidence in addition to
    length matters because a full page of misread cursive can produce
    plenty of characters, just wrong ones throughout — length alone
    would miss that.
    """
    pix = page.get_pixmap(matrix=fitz.Matrix(_OCR_ZOOM, _OCR_ZOOM), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    text, mean_confidence = extract_text_from_image(image, return_confidence=True)

    needs_fallback = (
        len(text.strip()) < MIN_OCR_RESULT_CHARS
        or mean_confidence < LOW_CONFIDENCE_FALLBACK_THRESHOLD
    )

    if needs_fallback and mistral_ocr_available():
        mistral_text = mistral_ocr_extract(image)
        if mistral_text.strip():
            return mistral_text

    if _ENABLE_HANDWRITING_FALLBACK and needs_fallback:
        vision_text = transcribe_handwriting(image)
        if vision_text.strip():
            return vision_text

    return text


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
        stripped = text.strip() if text else ""
        garbled = len(stripped) >= MIN_TEXT_LAYER_CHARS and _is_garbled_text(stripped)

        if len(stripped) >= MIN_TEXT_LAYER_CHARS and not garbled:
            pages.append(
                {
                    "page": page_num,
                    "text": text,
                    "source": uploaded_file.name
                }
            )
            continue

        # No usable text layer — either a scanned page, one with only a
        # stray character or two of "real" text, or (see `garbled`
        # above) a page whose text layer is corrupted by a broken font
        # mapping. Fall back to OCR, up to the per-document OCR cap.
        if ocr_pages_used < MAX_OCR_PAGES:
            ocr_pages_used += 1
            ocr_text = _ocr_page(page)
            # Prefer OCR output, but don't throw away a short-but-real
            # text layer if OCR itself came back empty (e.g. a mostly
            # blank page with just a page number). Never fall back to a
            # *garbled* text layer though — that's not real content and
            # is worse than having nothing for this page.
            final_text = ocr_text if ocr_text and ocr_text.strip() else ("" if garbled else stripped)
            if final_text:
                pages.append(
                    {
                        "page": page_num,
                        "text": final_text,
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
