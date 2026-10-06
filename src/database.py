from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.config import settings

# Di serverless, koneksi tidak disimpan di pool milik aplikasi; pooling ditangani Supabase pooler.
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    **({"poolclass": NullPool} if settings.vercel else {}),
)

async_session_factory = async_sessionmaker(engine,expire_on_commit=False)

class Base (DeclarativeBase):
    pass

async def get_db():
    async with async_session_factory() as session:
        yield session