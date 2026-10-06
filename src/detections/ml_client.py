import re
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent / "ml_models"
MODEL_PATH = MODELS_DIR / "model_spam_sms.pkl"
URL_MODEL_PATH = MODELS_DIR / "phishing_detector_model_light.pkl"

_bundle = joblib.load(MODEL_PATH)
_model = _bundle["model"]
_tfidf = _bundle["tfidf"]
_label_encoder = _bundle["le"]

LABEL_TO_VERDICT = {
    "normal": "safe",
    "promo": "suspicious",
    "penipuan": "scam",
}

# Model URL (beta): RandomForest dengan 8 fitur numerik, kelas 1 = phishing.
URL_FEATURE_NAMES = [
    "url_length", "qty_dot", "qty_question", "qty_slash",
    "has_ip", "is_https", "has_at_symbol", "qty_hyphen",
]

_url_model = joblib.load(URL_MODEL_PATH)
_url_model.n_jobs = 1  # prediksi satu URL tidak butuh banyak thread

# Pastikan model memakai fitur & urutan yang sama dengan extract_url_features().
if list(getattr(_url_model, "feature_names_in_", URL_FEATURE_NAMES)) != URL_FEATURE_NAMES:
    raise RuntimeError(
        f"Fitur model URL tidak cocok: {list(_url_model.feature_names_in_)}. "
        "Sesuaikan URL_FEATURE_NAMES dan extract_url_features()."
    )
# Model dilatih dengan DataFrame; hapus nama fitur agar input numpy tidak memicu warning.
if hasattr(_url_model, "feature_names_in_"):
    del _url_model.feature_names_in_

URL_LABELS = {0: "legitimate", 1: "phishing"}
URL_LABEL_TO_VERDICT = {"legitimate": "safe", "phishing": "scam"}

_IP_PATTERN = re.compile(r"(\d{1,3}\.){3}\d{1,3}")

@dataclass
class ClassificationResult:
    verdict: str
    confidence_score: float
    category: str | None

async def extract_text_from_image(image_bytes: bytes) -> str:
    # TODO: ganti dengan OCR asli
    return "[placeholder] extracted text from image"

async def classify_text(text: str) -> ClassificationResult:
    features = _tfidf.transform([text])

    predicted_index = _model.predict(features)[0]
    label = str(_label_encoder.inverse_transform([predicted_index])[0])

    probabilities = _model.predict_proba(features)[0]
    confidence_score = float(max(probabilities))

    verdict = LABEL_TO_VERDICT.get(label, "suspicious")

    return ClassificationResult(verdict=verdict, confidence_score=confidence_score, category=label)

def extract_url_features(url: str) -> list[float]:
    """Fitur untuk model URL, urutannya harus sama dengan feature_names_in_ model.

    Definisi fitur ditebak dari namanya (kode training tidak tersedia).
    Jika model dilatih ulang, sesuaikan fungsi ini dengan kode training-nya.
    """
    return [
        len(url),                                  # url_length
        url.count("."),                            # qty_dot
        url.count("?"),                            # qty_question
        url.count("/"),                            # qty_slash
        int(bool(_IP_PATTERN.search(url))),        # has_ip
        int(url.lower().startswith("https://")),   # is_https
        int("@" in url),                           # has_at_symbol
        url.count("-"),                            # qty_hyphen
    ]

async def classify_url(url: str) -> ClassificationResult:
    features = np.array([extract_url_features(url)])

    predicted_class = int(_url_model.predict(features)[0])
    label = URL_LABELS.get(predicted_class, "phishing")

    probabilities = _url_model.predict_proba(features)[0]
    confidence_score = float(max(probabilities))

    verdict = URL_LABEL_TO_VERDICT.get(label, "suspicious")

    return ClassificationResult(verdict=verdict, confidence_score=confidence_score, category=label)
  