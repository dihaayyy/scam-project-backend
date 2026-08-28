from auth.utils import create_access_token, create_refresh_token
from fastapi import APIRouter, status, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import EmailAlreadyRegistered, InvalidCredentials
from src.auth.schemas import Token, UserLogin, UserRead, UserCreate
from src.auth.service import authenticate_user, create_user
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

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, credentials.email, credentials.password)
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
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