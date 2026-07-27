import os
import threading

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from utils.concurrency import cpu_job

# The EasyOCR reader pulls in a torch-backed detection + recognition
# model (en+hi). Loading it eagerly at import time meant every process
# start paid that memory/time cost even for users who never touch OCR
# (most PDF/DOCX chat and study-notes flows never call this file at
# all). Loading it lazily, on first real use, means idle memory stays
# lower and startup stays fast — the one-time load cost just moves to
# whichever request first needs OCR.
_reader = None
_reader_lock = threading.Lock()

# Detections below this confidence are dropped rather than included in
# the extracted text. Scanned/photographed pages reliably produce a
# handful of near-random low-confidence hits (stray marks, watermark
# edges, page-border noise) that previously got concatenated straight
# into the output and corrupted it. Real words on reasonable-quality
# scans almost always score well above this; genuinely low-quality or
# handwritten source material can dip below it, so it's set generously
# rather than aggressively. Override via OCR_MIN_CONFIDENCE.
MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "0.35"))

# EasyOCR (like most OCR engines) gets unreliable on text under ~20px
# tall. Low-DPI page renders and phone-camera photos routinely fall
# below that. Anything smaller than this on its long edge gets scaled
# up before detection. Override via OCR_MIN_LONG_EDGE.
MIN_LONG_EDGE = int(os.getenv("OCR_MIN_LONG_EDGE", "1500"))


def _get_reader():
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                import easyocr
                _reader = easyocr.Reader(["en", "hi"], gpu=False)
    return _reader


def _preprocess(image: Image.Image) -> Image.Image:
    """Clean a page render up before handing it to EasyOCR.

    EasyOCR's detector is trained on natural-scene text, and is
    noticeably more accurate on documents when given a contrast-
    normalized, sharpened, adequately-sized grayscale image rather
    than a raw RGB render straight off a PDF or camera. This is the
    single biggest lever for accuracy short of switching engines.
    """
    # Color doesn't help text recognition, and a 3-channel image just
    # triples the pixels the detector has to process for no gain.
    image = ImageOps.grayscale(image)

    # Autocontrast stretches the existing brightness range to fill
    # 0-255. Scans and phone photos are very often mid-gray and
    # low-contrast (uneven lighting, faded toner, camera glare) — this
    # alone recovers a lot of legibility. `cutoff` trims a small
    # fraction of extreme pixels first so a few pure-black/white
    # outliers (staple shadows, page edges) don't compress the
    # stretch for the actual text.
    image = ImageOps.autocontrast(image, cutoff=1)

    # Mild unsharp mask counteracts the blur from phone-camera photos
    # and low-DPI renders, crisping character edges for the detector
    # without the ringing artifacts a stronger sharpen would add.
    image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))

    # Upscale if the page render is small — otherwise text height
    # ends up below what the detector reads reliably.
    long_edge = max(image.size)
    if long_edge < MIN_LONG_EDGE:
        scale = MIN_LONG_EDGE / long_edge
        new_size = (round(image.width * scale), round(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)

    return image


def _reading_order(results):
    """Reassemble EasyOCR's detections into normal reading order.

    EasyOCR returns detections in whatever order its detector happened
    to find them in, not top-to-bottom/left-to-right — joined naively,
    a real page's text comes back shuffled (this is a common cause of
    "OCR text is garbled" complaints even when every individual word
    was read correctly). This buckets detections into text rows by
    vertical position, then sorts each row left-to-right, so multi-
    column layouts and ordinary paragraphs both come out readable.
    """
    if not results:
        return []

    items = []
    for bbox, text, conf in results:
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        items.append(
            {
                "text": text,
                "y": sum(ys) / len(ys),
                "x": min(xs),
                "height": max(ys) - min(ys) or 1,
            }
        )

    items.sort(key=lambda i: i["y"])

    rows = []
    for item in items:
        placed = False
        for row in rows:
            # Treat as the same line if vertical centers are within
            # roughly half a line-height of each other.
            row_height = max(i["height"] for i in row["items"])
            if abs(item["y"] - row["y"]) < max(item["height"], row_height) * 0.6:
                row["items"].append(item)
                row["y"] = sum(i["y"] for i in row["items"]) / len(row["items"])
                placed = True
                break
        if not placed:
            rows.append({"y": item["y"], "items": [item]})

    rows.sort(key=lambda r: r["y"])

    lines = []
    for row in rows:
        row["items"].sort(key=lambda i: i["x"])
        lines.append(" ".join(i["text"] for i in row["items"]))

    return lines


def extract_text_from_image(image, min_confidence=None):
    """Extract text from a page image (PIL Image or numpy array).

    Preprocesses the image for legibility, runs EasyOCR with detection
    thresholds loosened enough to catch faint/small text, drops
    low-confidence noise, and reassembles what's left into reading
    order rather than the detector's raw (unordered) output.
    """
    if min_confidence is None:
        min_confidence = MIN_CONFIDENCE

    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)

    image = _preprocess(image)

    # OCR is CPU-heavy with no GPU to offload to — gate it so many
    # concurrent users' OCR calls don't all fight for the same cores
    # at once (see utils/concurrency.py).
    with cpu_job():
        reader = _get_reader()
        results = reader.readtext(
            np.array(image),
            detail=1,
            # Defaults are tuned for natural-scene photos (street
            # signs, etc.); documents need the detector to be more
            # willing to call faint/thin text a text region.
            text_threshold=0.6,
            low_text=0.35,
            contrast_ths=0.1,
            adjust_contrast=0.5,
        )

    filtered = [r for r in results if r[2] >= min_confidence]

    return "\n".join(_reading_order(filtered))
