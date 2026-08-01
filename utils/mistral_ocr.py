import base64
import io
import os

# Mistral's OCR model is a strong, actively-maintained document OCR
# engine with reported gains specifically on Indic scripts (Hindi,
# Bengali, Tamil, Gujarati, etc.) over general-purpose OCR — exactly
# the gap EasyOCR is weakest at on real (not clean/synthetic) scans.
# It's a paid, network-dependent API call though, so it's used only as
# an optional second-tier fallback: EasyOCR stays the free, offline,
# always-available default, and this is reached for specifically when
# EasyOCR's own result looks unreliable (see utils/pdf_loader.py).
#
# Configure via .env:
#   MISTRAL_API_KEY           = required to enable this fallback at all
#   MISTRAL_OCR_MODEL          = optional, defaults to mistral-ocr-latest
#   ENABLE_MISTRAL_OCR_FALLBACK = optional, defaults to true whenever
#                                 MISTRAL_API_KEY is set; set to "false"
#                                 to keep the key configured but skip
#                                 this fallback (e.g. to save quota).
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_OCR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
_ENABLE_MISTRAL_OCR_FALLBACK = (
    os.getenv("ENABLE_MISTRAL_OCR_FALLBACK", "true").lower() != "false"
)

# Same reasoning as REQUEST_TIMEOUT_SECONDS in utils/llm.py: without an
# explicit bound, a stalled request hangs far longer than a user will
# wait, with no visible error — bound it so it fails fast and the page
# just falls through to whatever the next fallback (or nothing) is.
REQUEST_TIMEOUT_SECONDS = 45

_client = None


def is_available() -> bool:
    """Whether the Mistral OCR fallback is configured and enabled.
    Checked by callers before doing the (comparatively expensive) work
    of encoding an image, so a deployment with no MISTRAL_API_KEY set
    never pays even that small cost."""
    return bool(MISTRAL_API_KEY) and _ENABLE_MISTRAL_OCR_FALLBACK


def _get_client():
    global _client
    if _client is None:
        # Imported lazily for the same reason EasyOCR is loaded lazily
        # in utils/ocr.py — most requests never touch OCR at all, so
        # this shouldn't cost import time/memory for every process
        # start.
        # from mistralai import Mistral
        from mistralai.client import Mistral
        _client = Mistral(api_key=MISTRAL_API_KEY)
    return _client


def _image_to_data_url(image, max_long_edge=2500, quality=90) -> str:
    """Downscale (if needed) and JPEG-encode a PIL image into a data:
    URL for the OCR API. Mirrors _image_to_data_url in utils/llm.py,
    but with a larger cap — this is a dedicated OCR model rather than
    a general vision chat model, so it's worth giving it more pixels
    to work with for small body text."""
    image = image.convert("RGB")
    long_edge = max(image.size)
    if long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        image = image.resize(
            (round(image.width * scale), round(image.height * scale))
        )
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def extract_text_from_image(image) -> str:
    """Run a page image through the Mistral OCR API and return its
    extracted text (Markdown, from the model's single returned page).

    Returns "" on any failure (missing/invalid key, rate limit,
    timeout, network error) rather than raising — this is always a
    fallback path in the caller (utils/pdf_loader.py), and a broken
    Mistral call should never crash a PDF upload that EasyOCR (or the
    existing handwriting fallback) could otherwise have handled.
    """
    if not is_available():
        return ""

    try:
        client = _get_client()
        data_url = _image_to_data_url(image)
        response = client.ocr.process(
            model=MISTRAL_OCR_MODEL,
            document={"type": "image_url", "image_url": data_url},
        )
        pages = getattr(response, "pages", None)
        if not pages:
            return ""
        # A single page image always yields exactly one result page —
        # multi-page `pages` responses only happen for document_url
        # (PDF) inputs, which this function doesn't send.
        return pages[0].markdown or ""
    except Exception as e:
        print(f"mistral_ocr.extract_text_from_image failed: {e}")
        return ""
