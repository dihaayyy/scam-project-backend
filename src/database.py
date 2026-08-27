from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

engine = create_async_engine(settings.database_url, echo=True)

async_session_factory = async_sessionmaker(engine,expire_on_commit=False)

class Base (DeclarativeBase):
    pass

async def get_db():
    async with async_session_factory() as session:
        yield session