from datetime import datetime, timezone, timedelta

from auth.mail import send_otp_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.auth.models import User
from src.auth.schemas import UserCreate
from src.auth.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidOTP,
    OTPExpired,
    UserNotVerified,
)
from src.auth.utils import generate_otp, hash_password, verify_password

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none() is not None:
        raise EmailAlreadyRegistered(user_in.email)

    otp_code = generate_otp()
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        otp_code=otp_code,
        otp_expires_at=otp_expires_at,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await send_otp_email(user.email, otp_code)

    return user

async def verify_otp(db: AsyncSession, email: str, otp_code: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or user.otp_code != otp_code:
        raise InvalidOTP()

    if user.otp_expires_at is None or datetime.now(timezone.utc) > user.otp_expires_at:
        raise OTPExpired()

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    await db.commit()
    await db.refresh(user)

    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentials()
    if not user.is_verified:
        raise UserNotVerified()
    return user