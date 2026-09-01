from dataclasses import dataclass

@dataclass
class ClassificationResult:
    verdict: str
    confidence_score: float
    category: str | None

async def extract_text_from_image(image_bytes: bytes) -> str:
    # TODO: ganti dengan OCR asli
    return "[placeholder] extracted text from image"

async def classify_text(text: str) -> ClassificationResult:
    #TODO: ganti dengan model NLP asli
    return ClassificationResult(verdict="safe", confidence_score=0.5, category=None)
  