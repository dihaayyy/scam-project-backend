from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.detections.models import Detection
from src.detections.exceptions import DetectionNotFound
from src.detections.ml_client import classify_text, extract_text_from_image

async def detect_text(db: AsyncSession, user_id: int, text: str) -> Detection:
    result = await classify_text(text)

    detection = Detection(
        user_id = user_id,
        input_type = "text",
        input_text = text,
        verdict = result.verdict,
        confidence_score = result.confidence_score,
        category = result.category
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    return detection

async def detect_image(db: AsyncSession, user_id: int, image_bytes: bytes) -> Detection:
    extracted_text = await extract_text_from_image(image_bytes)
    result = await classify_text(extracted_text)

    detection = Detection(
            user_id = user_id,
            input_type = "image",
            verdict = result.verdict,
            confidence_score = result.confidence_score,
            category = result.category
        )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    return detection

async def get_history(db: AsyncSession, user_id: int) -> list[Detection]:
    result = await db.execute(
        select(Detection).where(Detection.user_id == user_id).order_by(Detection.created_at.desc())
    )
    return list(result.scalars().all())

async def get_detection(db: AsyncSession, user_id: int, detection_id: int) -> Detection:
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id, Detection.user_id == user_id)
    )
    detection = result.scalar_one_or_none()

    if detection is None:
        raise DetectionNotFound()

    return detection

async def delete_detection(db: AsyncSession, user_id: int, detection_id: int) -> None:
    detection = await get_detection(db, user_id, detection_id)
    await db.delete(detection)
    await db.commit()