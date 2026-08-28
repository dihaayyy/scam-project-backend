from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.schemas import UserCreate
from src.auth.exceptions import EmailAlreadyRegistered, InvalidCredentials
from src.auth.utils import hash_password, verify_password

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none() is not None:
        raise EmailAlreadyRegistered(user_in.email)

    user = User(
        email=user_in.email,
        hashed_password = hash_password(user_in.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentials()
    return user