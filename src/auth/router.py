from fastapi import APIRouter, status, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.utils import create_access_token, create_refresh_token
from src.auth.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidOTP,
    OTPExpired,
    UserAlreadyVerified,
    UserNotFound,
    UserNotVerified,
)
from src.auth.schemas import (
    MessageResponse, 
    OTPVerify, 
    Token, 
    UserLogin, 
    UserRead, 
    UserCreate, 
    ResendOTPRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    )
from src.auth.service import (
    authenticate_user, 
    create_user,
    verify_otp, 
    resend_otp,
    request_password_reset,
    reset_password
)
    
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

@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp_endpoint(payload: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    try:
        await resend_otp(db, payload.email)
    except UserNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    except UserAlreadyVerified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified."
        )
    return MessageResponse(message="OTP has been resent successfully.")

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    await request_password_reset(db, payload.email)
    return MessageResponse(message="If the email is registered and verified, a password reset OTP has been sent.")

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password_endpoint(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        await reset_password(db, payload.email, payload.otp_code, payload.new_password)
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
    return MessageResponse(message="Password has been reset successfully.")