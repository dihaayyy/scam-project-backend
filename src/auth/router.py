from fastapi import APIRouter, status, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.utils import create_access_token, create_refresh_token
from src.auth.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidOTP,
    OTPExpired,
    UserNotVerified,
)
from src.auth.schemas import OTPVerify, Token, UserLogin, UserRead, UserCreate
from src.auth.service import authenticate_user, create_user, verify_otp
from src.database import get_db
from src.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, user_in)
    except EmailAlreadyRegistered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered."
        )
    return user

@router.post("/verify-otp", response_model=UserRead)
async def verify_otp_endpoint(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    try:
        user = await verify_otp(db, payload.email, payload.otp_code)
    except InvalidOTP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code."
        )
    except OTPExpired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired."
        )
    return user

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, credentials.email, credentials.password)
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    except UserNotVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your account via OTP first."
        )

    access_token = create_access_token(subject=str(user.id)) 
    refresh_token = create_refresh_token(subject=str(user.id)) 

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60
    )
    return Token(access_token=access_token)