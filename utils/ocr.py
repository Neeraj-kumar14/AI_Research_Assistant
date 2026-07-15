import threading

import numpy as np
from PIL import Image

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


def _get_reader():
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                import easyocr
                _reader = easyocr.Reader(["en", "hi"], gpu=False)
    return _reader


def extract_text_from_image(image):

    if isinstance(image, Image.Image):
        image = np.array(image)

    # OCR is CPU-heavy with no GPU to offload to — gate it so many
    # concurrent users' OCR calls don't all fight for the same cores
    # at once (see utils/concurrency.py).
    with cpu_job():
        reader = _get_reader()
        result = reader.readtext(image, detail=0)

    return "\n".join(result)
