import math

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status, Depends, Request
from src.pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from src.detections.schemas import DetectionResult, TextDetectionRequest, UrlDetectionRequest
from src.auth.models import User
from src.auth.dependencies import get_current_user, get_optional_user
from src.database import get_db
from src.detections.service import detect_image, detect_text, detect_text_guest, detect_url, get_history, get_guest_identifier, get_detection, delete_detection
from src.detections.exceptions import DetectionNotFound, GuestLimitReached

router = APIRouter(prefix="/detection", tags=["detection"])

@router.post("/text", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
async def detect_text_endpoint(
    payload: TextDetectionRequest,
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user is not None:
        return await detect_text(db, current_user.id, payload.text)

    try:
        return await detect_text_guest(db, get_guest_identifier(request), payload.text)
    except GuestLimitReached:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "GUEST_LIMIT_REACHED", "message": "Batas deteksi gratis habis. Silakan login."},
        )

@router.post("/url", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
async def detect_url_endpoint(
    payload: UrlDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await detect_url(db, current_user.id, payload.url)

@router.post("/image", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
async def detect_image_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    image_bytes = await file.read()
    return await detect_image(db, current_user.id, image_bytes)

@router.get("/history", response_model=Page[DetectionResult])
async def get_history_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    items, total = await get_history(db, current_user.id, page, size)
    total_pages = math.ceil(total / size) if total > 0 else 0

    return Page(items=items, total=total, page=page, size=size, total_pages=total_pages)

@router.get("/history/{detection_id}", response_model=DetectionResult)
async def get_detection_by_id_endpoint(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await get_detection(db, current_user.id, detection_id)
    except DetectionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")

@router.delete("/history/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detection_by_id_endpoint(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        await delete_detection(db, current_user.id, detection_id)
    except DetectionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")