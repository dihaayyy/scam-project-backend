from dataclasses import dataclass
from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_models" / "model_spam_sms.pkl"
    
_bundle = joblib.load(MODEL_PATH)
_model = _bundle["model"]
_tfidf = _bundle["tfidf"]
_label_encoder = _bundle["le"]

LABEL_TO_VERDICT = {
    "normal": "safe",
    "promo": "suspicious",
    "penipuan": "scam",
}

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
  