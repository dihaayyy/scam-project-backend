from fastapi import APIRouter, File, HTTPException, UploadFile, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.detections.schemas import DetectionResult, TextDetectionRequest
from src.auth.models import User
from src.auth.dependencies import get_current_user
from src.database import get_db
from src.detections.service import detect_image, detect_image, detect_text, get_history, get_detection
from src.detections.exceptions import DetectionNotFound

router = APIRouter(prefix="/detection", tags=["detection"])

@router.post("/text", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
async def detect_text_endpoint(
    payload: TextDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await detect_text(db, current_user.id, payload.text)

@router.post("/image", response_model=DetectionResult, status_code=status.HTTP_201_CREATED)
async def detect_image_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    image_bytes = await file.read()
    return await detect_image(db, current_user, image_bytes)

@router.get("/history", response_model=list[DetectionResult])
async def get_history_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_history(db, current_user.id)

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