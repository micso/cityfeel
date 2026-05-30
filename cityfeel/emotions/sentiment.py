import logging
import os
import re
import threading

import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    raise RuntimeError("Brak GEMINI_API_KEY w zmiennych środowiskowych.")
                genai.configure(api_key=api_key)
                _model = genai.GenerativeModel("gemini-2.5-flash")
                logger.info("Gemini model załadowany.")
    return _model


_PROMPT = """Oceń sentyment poniższego tekstu w skali 1-5:
1 = bardzo negatywny
2 = negatywny
3 = neutralny
4 = pozytywny
5 = bardzo pozytywny

Odpowiedz TYLKO jedną cyfrą (1, 2, 3, 4 lub 5). Nic więcej.

Tekst: {text}"""


def analyze(text: str) -> dict:
    """
    Analizuje sentyment tekstu przez Gemini API.
    Zwraca {'score': float 1.0–5.0, 'label': 'negative'|'neutral'|'positive'}
    lub {'score': None, 'label': None} gdy brak tekstu lub błąd.
    """
    if not text or not text.strip():
        return {"score": None, "label": None}

    try:
        model = _get_model()
        response = model.generate_content(_PROMPT.format(text=text[:1000]))
        raw = response.text.strip()

        match = re.search(r"[1-5]", raw)
        if not match:
            logger.warning("Gemini zwrócił nieoczekiwany wynik: %r", raw)
            return {"score": None, "label": None}

        score = float(match.group())
        if score <= 2:
            label = "negative"
        elif score == 3:
            label = "neutral"
        else:
            label = "positive"

        return {"score": score, "label": label}
    except Exception:
        logger.exception("Błąd analizy sentymentu (Gemini) dla tekstu: %.80s", text)
        return {"score": None, "label": None}
