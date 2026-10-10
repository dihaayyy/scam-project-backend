import hashlib

from datetime import datetime, timedelta, timezone
from fastapi import Request

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.detections.models import Detection, GuestUsage
from src.detections.exceptions import DetectionNotFound, GuestLimitReached
from src.detections.ml_client import classify_text, classify_url, extract_text_from_image

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

async def detect_url(db: AsyncSession, user_id: int, url: str) -> Detection:
    url = url.strip()
    result = await classify_url(url)

    detection = Detection(
        user_id = user_id,
        input_type = "url",
        input_text = url,
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

async def get_history(db: AsyncSession, user_id: int, page: int, size: int ) -> tuple[list[Detection], int]:
    offset = (page - 1) * size

    count_result = await db.execute(
        select(func.count()).select_from(Detection).where(Detection.user_id == user_id)   
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Detection)
        .where(Detection.user_id == user_id)
        .order_by(Detection.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    items = list(result.scalars().all())

    return items, total

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

def get_guest_identifier(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    else:
        ip = "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()

async def detect_text_guest(db: AsyncSession, identifier: str, text: str) -> dict:
    now = datetime.now(timezone.utc)
    usage = await db.get(GuestUsage, identifier, with_for_update=True)

    if usage is None:
        usage = GuestUsage(identifier=identifier, count=0, window_start=now)
        db.add(usage)
    elif now - usage.window_start > timedelta(hours=settings.guest_limit_window_hours):
        usage.count = 0
        usage.window_start = now
        
    if usage.count >= settings.guest_detection_limit:
        raise GuestLimitReached()

    result = await classify_text(text)
    usage.count += 1
    await db.commit()

    return {
        "id": None, "input_type": "text", "input_text": text, "extracted_text": None,
        "verdict": result.verdict, "confidence_score": result.confidence_score,
        "category": result.category, "created_at": now,
    }
