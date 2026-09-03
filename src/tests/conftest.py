from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.config import settings
from src.main import app
from src.auth.utils import create_access_token

_base, _, _db_name = settings.database_url.rpartition("/")
TEST_DATABASE_URL = settings.database_test_url or f"{_base}/{_db_name}_test"

@pytest_asyncio.fixture
async def db_session():
    """Bikin engine + semua tabel sebelum test, hapus semua tabel setelah test.

    Tiap test dapat database yang benar-benar bersih (isolasi penuh).
    """
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    """HTTP client yang memanggil app FastAPI langsung (tanpa server nyala).

    get_db di-override supaya endpoint pakai session test, bukan DB development.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    """autouse=True -> otomatis aktif di SEMUA test. Email tidak pernah benar-benar dikirim."""
    monkeypatch.setattr("src.auth.service.send_otp_email", AsyncMock())
    monkeypatch.setattr("src.auth.service.send_password_reset_email", AsyncMock())

# ---------- Fixture bantuan: user yang sudah terdaftar & terverifikasi + token ----------

REGISTER_PAYLOAD = {
    "name": "Abdul Tester",
    "email": "abdul.testing@email.com",
    "password": "abdultester123",
}

@pytest_asyncio.fixture
async def auth_headers(client, db_session):
    """Daftar user, tandai verified langsung di DB, kembalikan header Authorization."""
    from sqlalchemy import select

    from src.auth.models import User

    await client.post("/auth/register", json=REGISTER_PAYLOAD)

    user = (
        await db_session.execute(
            select(User).where(User.email == REGISTER_PAYLOAD["email"])
        )
    ).scalar_one()
    user.is_verified = True
    await db_session.commit()

    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}