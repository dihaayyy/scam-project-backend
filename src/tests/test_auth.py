import pytest
import pytest_asyncio
from sqlalchemy import select

from src.auth.models import User

REGISTER_PAYLOAD = {
    "name": "Abdul Tester",
    "email": "abdul.testing@email.com",
    "password": "abdultester123",
}


# ---------------------- REGISTER ----------------------

async def test_register_sukses(client):
    resp = await client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "abdul.testing@email.com"
    assert body["name"] == "Abdul Tester"
    assert body["is_verified"] is False
    assert "id" in body
    # Password (atau hash-nya) TIDAK boleh bocor di response
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_email_duplikat_ditolak_409(client):
    await client.post("/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert resp.status_code == 409


async def test_register_email_tidak_valid_ditolak_422(client):
    resp = await client.post(
        "/auth/register",
        json={**REGISTER_PAYLOAD, "email": "bukan-email"},
    )
    assert resp.status_code == 422


async def test_register_field_kurang_ditolak_422(client):
    resp = await client.post("/auth/register", json={"email": "a@b.com"})
    assert resp.status_code == 422


# ---------------------- VERIFY OTP ----------------------

@pytest_asyncio.fixture
async def registered_user(client, db_session):
    """User baru daftar; kembalikan row User (termasuk otp_code-nya)."""
    await client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = (
        await db_session.execute(
            select(User).where(User.email == REGISTER_PAYLOAD["email"])
        )
    ).scalar_one()
    return user


async def test_verify_otp_sukses(client, registered_user, db_session):
    resp = await client.post(
        "/auth/verify-otp",
        json={"email": registered_user.email, "otp_code": registered_user.otp_code},
    )

    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True

    await db_session.refresh(registered_user)
    assert registered_user.is_verified is True
    assert registered_user.otp_code is None  # OTP dihapus setelah dipakai


async def test_verify_otp_kode_salah_ditolak_400(client, registered_user):
    resp = await client.post(
        "/auth/verify-otp",
        json={"email": registered_user.email, "otp_code": "000000"},
    )
    assert resp.status_code == 400


async def test_verify_otp_kadaluarsa_ditolak_400(client, registered_user, db_session):
    from datetime import datetime, timedelta, timezone

    registered_user.otp_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    resp = await client.post(
        "/auth/verify-otp",
        json={"email": registered_user.email, "otp_code": registered_user.otp_code},
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


# ---------------------- LOGIN ----------------------

async def test_login_sukses_mengembalikan_access_token(client, registered_user, db_session):
    registered_user.is_verified = True
    await db_session.commit()

    resp = await client.post(
        "/auth/login",
        json={"email": registered_user.email, "password": REGISTER_PAYLOAD["password"]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "Bearer"
    # refresh token dikirim lewat httpOnly cookie
    assert "refresh_token" in resp.cookies


async def test_login_password_salah_ditolak_401(client, registered_user, db_session):
    registered_user.is_verified = True
    await db_session.commit()

    resp = await client.post(
        "/auth/login",
        json={"email": registered_user.email, "password": "password-salah"},
    )
    assert resp.status_code == 401


async def test_login_user_belum_verifikasi_ditolak_403(client, registered_user):
    resp = await client.post(
        "/auth/login",
        json={"email": registered_user.email, "password": REGISTER_PAYLOAD["password"]},
    )
    assert resp.status_code == 403


async def test_login_email_tidak_terdaftar_ditolak_401(client):
    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "apa-aja"},
    )
    assert resp.status_code == 401


# ---------------------- GET /auth/me ----------------------

async def test_me_tanpa_token_ditolak(client):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)  # HTTPBearer default -> 403


async def test_me_dengan_token_valid(client, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "abdul.testing@email.com"


async def test_me_token_ngawur_ditolak_401(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer token-palsu"})
    assert resp.status_code == 401

# ==================== RESEND OTP ====================

async def test_resend_otp_sukses(client, registered_user, db_session):
    resp = await client.post("/auth/resend-otp", json={"email": registered_user.email})

    assert resp.status_code == 200
    assert "resent" in resp.json()["message"].lower()

    await db_session.refresh(registered_user)
    assert registered_user.otp_code is not None
    assert registered_user.otp_expires_at is not None


async def test_resend_otp_email_tidak_terdaftar_404(client):
    resp = await client.post("/auth/resend-otp", json={"email": "nobody@example.com"})
    assert resp.status_code == 404


async def test_resend_otp_user_sudah_verified_400(client, registered_user, db_session):
    registered_user.is_verified = True
    await db_session.commit()

    resp = await client.post("/auth/resend-otp", json={"email": registered_user.email})
    assert resp.status_code == 400


# ==================== FORGOT / RESET PASSWORD ====================

@pytest_asyncio.fixture
async def verified_user(client, db_session):
    await client.post("/auth/register", json=REGISTER_PAYLOAD)
    user = (
        await db_session.execute(
            select(User).where(User.email == REGISTER_PAYLOAD["email"])
        )
    ).scalar_one()
    user.is_verified = True
    await db_session.commit()
    return user


async def test_forgot_password_selalu_200_walau_email_tidak_ada(client):
    """Tidak boleh membocorkan apakah suatu email terdaftar (anti user-enumeration)."""
    resp = await client.post(
        "/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200


async def test_forgot_password_user_verified_menghasilkan_otp(client, verified_user, db_session):
    resp = await client.post(
        "/auth/forgot-password", json={"email": verified_user.email}
    )
    assert resp.status_code == 200

    await db_session.refresh(verified_user)
    assert verified_user.otp_code is not None
    assert verified_user.otp_expires_at is not None


async def test_reset_password_sukses_lalu_login_pakai_password_baru(client, verified_user, db_session):
    await client.post("/auth/forgot-password", json={"email": verified_user.email})
    await db_session.refresh(verified_user)
    otp = verified_user.otp_code

    resp = await client.post(
        "/auth/reset-password",
        json={
            "email": verified_user.email,
            "otp_code": otp,
            "new_password": "passwordBaru456",
        },
    )
    assert resp.status_code == 200

    # password lama tidak berlaku lagi
    login_lama = await client.post(
        "/auth/login",
        json={"email": verified_user.email, "password": REGISTER_PAYLOAD["password"]},
    )
    assert login_lama.status_code == 401

    # password baru berhasil
    login_baru = await client.post(
        "/auth/login",
        json={"email": verified_user.email, "password": "passwordBaru456"},
    )
    assert login_baru.status_code == 200


async def test_reset_password_otp_salah_400(client, verified_user):
    await client.post("/auth/forgot-password", json={"email": verified_user.email})

    resp = await client.post(
        "/auth/reset-password",
        json={
            "email": verified_user.email,
            "otp_code": "000000",
            "new_password": "apa-aja",
        },
    )
    assert resp.status_code == 400


async def test_reset_password_otp_kadaluarsa_400(client, verified_user, db_session):
    from datetime import datetime, timedelta, timezone

    await client.post("/auth/forgot-password", json={"email": verified_user.email})
    await db_session.refresh(verified_user)
    otp = verified_user.otp_code

    verified_user.otp_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    resp = await client.post(
        "/auth/reset-password",
        json={"email": verified_user.email, "otp_code": otp, "new_password": "x"},
    )
    assert resp.status_code == 400
