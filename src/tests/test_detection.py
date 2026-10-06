import pytest

from src.detections.ml_client import ClassificationResult


@pytest.fixture(autouse=True)
def mock_classifier(monkeypatch):
    """Ganti model ML asli dengan hasil tetap supaya test deterministik."""

    async def fake_classify(text: str) -> ClassificationResult:
        return ClassificationResult(
            verdict="scam", confidence_score=0.97, category="penipuan"
        )

    async def fake_extract(image_bytes: bytes) -> str:
        return "teks hasil ocr palsu"

    async def fake_classify_url(url: str) -> ClassificationResult:
        return ClassificationResult(
            verdict="scam", confidence_score=0.91, category="phishing"
        )

    monkeypatch.setattr("src.detections.service.classify_text", fake_classify)
    monkeypatch.setattr("src.detections.service.extract_text_from_image", fake_extract)
    monkeypatch.setattr("src.detections.service.classify_url", fake_classify_url)


# ---------------------- POST /detection/text ----------------------

async def test_detect_text_butuh_login(client):
    resp = await client.post("/detection/text", json={"text": "halo"})
    assert resp.status_code in (401, 403)


async def test_detect_text_sukses(client, auth_headers):
    resp = await client.post(
        "/detection/text",
        json={"text": "Selamat! Anda memenangkan hadiah 100 juta, klik link ini"},
        headers=auth_headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["verdict"] == "scam"
    assert body["confidence_score"] == 0.97
    assert body["input_type"] == "text"
    assert body["input_text"].startswith("Selamat!")
    assert "id" in body


# ---------------------- POST /detection/url ----------------------

async def test_detect_url_butuh_login(client):
    resp = await client.post("/detection/url", json={"url": "http://contoh.xyz"})
    assert resp.status_code in (401, 403)


async def test_detect_url_sukses(client, auth_headers):
    resp = await client.post(
        "/detection/url",
        json={"url": "  http://paypal-secure-login.verify-account.xyz/signin  "},
        headers=auth_headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["input_type"] == "url"
    assert body["input_text"] == "http://paypal-secure-login.verify-account.xyz/signin"
    assert body["verdict"] == "scam"
    assert body["category"] == "phishing"


async def test_detect_url_kosong_ditolak_422(client, auth_headers):
    resp = await client.post("/detection/url", json={"url": ""}, headers=auth_headers)
    assert resp.status_code == 422


async def test_detect_url_muncul_di_history(client, auth_headers):
    await client.post("/detection/url", json={"url": "http://contoh.xyz"}, headers=auth_headers)

    resp = await client.get("/detection/history", headers=auth_headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["input_type"] == "url"


# ---------------------- GET /detection/history ----------------------

async def test_history_kosong_di_awal(client, auth_headers):
    resp = await client.get("/detection/history", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["total_pages"] == 0


async def test_history_pagination(client, auth_headers):
    for i in range(3):
        await client.post(
            "/detection/text", json={"text": f"pesan {i}"}, headers=auth_headers
        )

    resp = await client.get("/detection/history?page=1&size=2", headers=auth_headers)
    body = resp.json()

    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["total_pages"] == 2


async def test_history_hanya_milik_user_sendiri(client, auth_headers, db_session):
    """Detection milik user lain tidak boleh muncul di history kita."""
    from src.auth.models import User
    from src.detections.models import Detection

    # user kedua, harus benar-benar ada karena detections.user_id FK ke users.id
    other_user = User(
        name="Orang Lain",
        email="lain@example.com",
        hashed_password="x",
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.flush()  # isi other_user.id tanpa commit penuh

    db_session.add(
        Detection(
            user_id=other_user.id,
            input_type="text",
            input_text="punya orang lain",
            verdict="safe",
            confidence_score=0.5,
        )
    )
    await db_session.commit()

    # detection milik kita sendiri
    await client.post("/detection/text", json={"text": "punyaku"}, headers=auth_headers)

    resp = await client.get("/detection/history", headers=auth_headers)
    assert resp.json()["total"] == 1  # hanya punya kita yang kehitung


async def test_history_size_di_atas_100_ditolak_422(client, auth_headers):
    resp = await client.get("/detection/history?size=999", headers=auth_headers)
    assert resp.status_code == 422


# ---------------------- GET / DELETE /detection/history/{id} ----------------------

async def test_get_detail_id_tidak_ada_404(client, auth_headers):
    resp = await client.get("/detection/history/123456", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_detection_lalu_hilang(client, auth_headers):
    created = await client.post(
        "/detection/text", json={"text": "mau dihapus"}, headers=auth_headers
    )
    detection_id = created.json()["id"]

    resp = await client.delete(
        f"/detection/history/{detection_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    resp = await client.get(
        f"/detection/history/{detection_id}", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_delete_detection_id_tidak_ada_404(client, auth_headers):
    resp = await client.delete("/detection/history/123456", headers=auth_headers)
    assert resp.status_code == 404

# ==================== POST /detection/image ====================

IMAGE_FILE = {"file": ("screenshot.png", b"fake-image-bytes", "image/png")}


async def test_detect_image_butuh_login(client):
    resp = await client.post("/detection/image", files=IMAGE_FILE)
    assert resp.status_code in (401, 403)


async def test_detect_image_sukses(client, auth_headers):
    resp = await client.post("/detection/image", files=IMAGE_FILE, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["input_type"] == "image"
    assert body["verdict"] == "scam"
    assert body["confidence_score"] == 0.97
    assert body["input_text"] is None  # endpoint image tidak mengisi input_text


async def test_detect_image_tanpa_file_422(client, auth_headers):
    resp = await client.post("/detection/image", headers=auth_headers)
    assert resp.status_code == 422


async def test_detect_image_muncul_di_history(client, auth_headers):
    await client.post("/detection/image", files=IMAGE_FILE, headers=auth_headers)

    resp = await client.get("/detection/history", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["input_type"] == "image"


async def test_detect_image_extracted_text_belum_disimpan(client, auth_headers):
    """CATATAN QA (characterization test): idealnya teks hasil OCR ikut tersimpan
    di kolom `extracted_text`, tapi service saat ini men-drop-nya
    (src/detections/service.py:29-38). Test ini mendokumentasikan perilaku SEKARANG.
    Kalau bug diperbaiki, ubah jadi `assert body["extracted_text"] is not None`.
    """
    resp = await client.post("/detection/image", files=IMAGE_FILE, headers=auth_headers)
    assert resp.json()["extracted_text"] is None