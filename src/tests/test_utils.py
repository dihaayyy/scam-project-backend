from datetime import datetime, timedelta, timezone

import jwt

from src.auth.utils import (
    create_access_token,
    generate_otp,
    hash_password,
    verify_password,
)
from src.config import settings


def test_hash_password_menghasilkan_hash_berbeda_dari_plaintext():
    hashed = hash_password("rahasia123")
    assert hashed != "rahasia123"
    assert len(hashed) > 20


def test_verify_password_cocok():
    hashed = hash_password("rahasia123")
    assert verify_password("rahasia123", hashed) is True


def test_verify_password_salah():
    hashed = hash_password("rahasia123")
    assert verify_password("password-salah", hashed) is False


def test_generate_otp_selalu_6_digit_angka():
    for _ in range(100):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()


def test_access_token_bisa_di_decode_dan_isinya_benar():
    token = create_access_token(subject="42")
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_access_token_punya_waktu_kedaluwarsa_di_masa_depan():
    token = create_access_token(subject="1")
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert exp > datetime.now(timezone.utc)
