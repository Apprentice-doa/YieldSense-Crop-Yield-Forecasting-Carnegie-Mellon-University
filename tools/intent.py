from __future__ import annotations
from src.services.summary_service import _get_client, _get_deployment

SUPPORTED_LANGUAGES = {
    "en": "English",
    "sw": "Swahili",
    "rw": "Kinyarwanda",
    "fr": "French",
    "am": "Amharic",
    "lg": "Luganda",
}


def detect_language(text: str) -> str:
    """Return the ISO 639-1 code of the language detected in text.

    Falls back to 'en' on any error.
    """
    prompt = (
        f"Detect the language of the following text and reply with ONLY the ISO 639-1 "
        f"two-letter language code (e.g. en, sw, rw, fr, am, lg). Text: {text!r}"
    )
    try:
        resp = _get_client().chat.completions.create(
            model=_get_deployment(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
        )
        code = resp.choices[0].message.content.strip().lower()[:2]
        return code if code in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"


def translate(text: str, target_language_code: str) -> str:
    """Translate text into the target language. Returns original on failure."""
    if target_language_code not in SUPPORTED_LANGUAGES:
        return text
    lang_name = SUPPORTED_LANGUAGES[target_language_code]
    prompt = (
        f"Translate the following text into {lang_name}. "
        f"Return ONLY the translated text, nothing else.\n\n{text}"
    )
    try:
        resp = _get_client().chat.completions.create(
            model=_get_deployment(),
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return text
