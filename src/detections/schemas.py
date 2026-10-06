from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class TextDetectionRequest(BaseModel):
    text: str

class UrlDetectionRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

class DetectionResult(BaseModel):
    id: int
    input_type: Literal["text", "image", "url"]
    input_text: str | None
    extracted_text: str | None
    verdict: Literal["safe", "suspicious", "scam"]
    confidence_score: float
    category: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

