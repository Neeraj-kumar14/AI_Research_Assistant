from langdetect import detect, DetectorFactory

# Make detection deterministic
DetectorFactory.seed = 0

LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "ur": "Urdu",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese (Traditional)"
}


def detect_language(text: str):

    try:

        lang_code = detect(text[:5000])

        return LANGUAGE_MAP.get(
            lang_code,
            lang_code.upper()
        )

    except Exception:

        return "Unknown"