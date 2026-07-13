import easyocr
import numpy as np
from PIL import Image


# Load OCR model only once
reader = easyocr.Reader(
    ["en", "hi"],
    gpu=False
)


def extract_text_from_image(image):

    if isinstance(image, Image.Image):

        image = np.array(image)

    result = reader.readtext(
        image,
        detail=0
    )

    return "\n".join(result)