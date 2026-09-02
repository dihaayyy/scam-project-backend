# Scam Project — Backend API

Backend API untuk mendeteksi **scam, phishing, dan fraud** dari teks (chat/SMS) dan gambar (screenshot), menggunakan model Machine Learning (NLP untuk teks, OCR + NLP untuk gambar). Dibangun dengan **FastAPI** + **PostgreSQL**.

Dokumen ini ditujukan untuk siapa pun yang mau menjalankan backend ini secara lokal — termasuk tim frontend (Next.js) yang butuh tahu cara setup dan bentuk API-nya.

## Tech Stack

| Kebutuhan | Teknologi |
|---|---|
| Framework | FastAPI (async) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| Auth | JWT (access token) + refresh token di httpOnly cookie |
| Password hashing | pwdlib (Argon2) |
| Email (OTP, reset password) | fastapi-mail (SMTP) |
| ML — teks | scikit-learn (Naive Bayes + TF-IDF), model `.pkl` |
| ML — gambar | OCR + NLP (masih dalam pengembangan) |

## Prerequisites

Pastikan sudah terinstall:

1. **Python 3.12+**
2. **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — package manager yang dipakai project ini (bukan pip biasa)
3. **PostgreSQL** — bisa lewat [Laragon](https://laragon.org/) (Windows) atau instalasi Postgres lainnya
4. **SMTP server untuk testing email** (opsional tapi disarankan untuk development) — pakai [Mailpit](https://github.com/axllent/mailpit/releases), jalan lokal tanpa perlu akun apa pun

## Getting Started

### 1. Clone repo

```bash
git clone <url-repo-ini>
cd scam-project
```

### 2. Install dependencies

```bash
uv sync
```

Ini otomatis membuat virtual environment (`.venv`) dan install semua dependency sesuai `pyproject.toml`.

### 3. Siapkan PostgreSQL

Buat database baru (nama bebas, contoh `scam_project`):

```sql
CREATE DATABASE scam_project;
```

### 4. Siapkan Mailpit (untuk testing email OTP secara lokal)

Download binary dari [rilis Mailpit](https://github.com/axllent/mailpit/releases), lalu jalankan dari terminal:

```bash
./mailpit.exe
```

Biarkan tetap berjalan di terminal terpisah. Ini membuka:
- `localhost:1025` — SMTP server palsu (dipakai backend untuk "mengirim" email)
- `localhost:8025` — Web UI untuk melihat email yang "terkirim" (buka di browser)

### 5. Konfigurasi environment variables

Buat file `.env` di root project (sejajar `pyproject.toml`), isi sesuai tabel di bagian **Environment Variables** di bawah.

### 6. Jalankan migration database

```bash
uv run alembic upgrade head
```

Ini akan membuat semua tabel yang dibutuhkan (`users`, `detections`, dst) sesuai skema terbaru.

### 7. Pastikan model ML tersedia

File model teks (`model_spam_sms.pkl`) harus ada di `src/ml_models/model_spam_sms.pkl`. Kalau belum ada (misal setelah clone baru), pastikan file ini sudah ter-commit di repo atau minta ke tim ML.

### 8. Jalankan server

```bash
uv run fastapi dev src/main.py
```

Server berjalan di `http://localhost:8000`. Dokumentasi API interaktif (Swagger UI) otomatis tersedia di `http://localhost:8000/docs`.

## Environment Variables

Semua variabel ini wajib ada di `.env`, kecuali yang ditandai "opsional" (sudah ada default value).

| Variabel | Wajib? | Contoh | Keterangan |
|---|---|---|---|
| `DATABASE_URL` | Ya | `postgresql+asyncpg://postgres:password@localhost:5432/scam_project` | Connection string PostgreSQL |
| `SECRET_KEY` | Ya | (string acak panjang) | Kunci rahasia untuk sign JWT. Generate dengan `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ALGORITHM` | Opsional | `HS256` | Algoritma signing JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Opsional | `15` | Masa berlaku access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Opsional | `7` | Masa berlaku refresh token |
| `OTP_EXPIRE_MINUTES` | Opsional | `10` | Masa berlaku kode OTP |
| `MAIL_USERNAME` | Ya | `mailpit` | Username SMTP (bebas kalau pakai Mailpit) |
| `MAIL_PASSWORD` | Ya | `mailpit` | Password SMTP (bebas kalau pakai Mailpit) |
| `MAIL_FROM` | Ya | `noreply@scamproject.com` | Alamat pengirim email (harus format email valid, hindari domain reserved seperti `.local`/`.test`) |
| `MAIL_PORT` | Ya | `1025` (Mailpit) | Port SMTP |
| `MAIL_SERVER` | Ya | `localhost` (Mailpit) | Host SMTP |
| `MAIL_FROM_NAME` | Opsional | `Scam Project` | Nama pengirim yang tampil di email |
| `CORS_ORIGINS` | Opsional | `http://localhost:3000` | Origin frontend yang diizinkan akses API (pisahkan dengan koma kalau lebih dari satu) |

## Autentikasi (Penting untuk Frontend)

API ini pakai **kombinasi 2 cara** pengiriman token — perlu dipahami betul supaya integrasi dari Next.js tidak salah:

1. **Access token (JWT)** — dikembalikan di **response body** saat `POST /auth/login`, harus disimpan di sisi frontend (memory/state) dan dikirim manual di setiap request ke endpoint yang butuh login, lewat header:
   ```
   Authorization: Bearer <access_token>
   ```
2. **Refresh token** — dikirim otomatis oleh backend lewat **httpOnly cookie** (`refresh_token`), tidak bisa dan tidak perlu dibaca oleh JavaScript di frontend. Browser akan otomatis mengirim cookie ini ke API selama request dilakukan dengan `credentials: "include"` (fetch) atau `withCredentials: true` (axios).

**Alur login yang disarankan di frontend:**
1. `POST /auth/login` dengan `{ email, password }`
2. Simpan `access_token` dari response ke state/memory (jangan `localStorage` untuk keamanan)
3. Pakai `access_token` itu di header `Authorization` untuk semua request selanjutnya yang butuh login
4. Cookie `refresh_token` otomatis ikut terkirim browser tanpa perlu ditangani manual

> Catatan: cookie refresh token saat ini di-set dengan `SameSite=Strict`. Ini akan perlu disesuaikan (`SameSite=None`) kalau frontend dan backend nanti di-deploy ke domain yang benar-benar berbeda.

## Daftar Endpoint

### Auth (`/auth`)

| Method | Path | Butuh Login? | Keterangan |
|---|---|---|---|
| POST | `/auth/register` | Tidak | Daftar akun baru (kirim OTP ke email) |
| POST | `/auth/verify-otp` | Tidak | Verifikasi akun pakai kode OTP |
| POST | `/auth/resend-otp` | Tidak | Kirim ulang kode OTP |
| POST | `/auth/login` | Tidak | Login, dapatkan access token |
| POST | `/auth/forgot-password` | Tidak | Minta kode reset password |
| POST | `/auth/reset-password` | Tidak | Set password baru pakai kode reset |
| GET | `/auth/me` | **Ya** | Data user yang sedang login |

### Detection (`/detection`)

| Method | Path | Butuh Login? | Keterangan |
|---|---|---|---|
| POST | `/detection/text` | **Ya** | Deteksi scam dari teks |
| POST | `/detection/image` | **Ya** | Deteksi scam dari gambar (OCR — *masih dalam pengembangan*) |
| GET | `/detection/history` | **Ya** | Riwayat deteksi milik user (paginated: `?page=&size=`) |
| GET | `/detection/history/{id}` | **Ya** | Detail satu riwayat deteksi |
| DELETE | `/detection/history/{id}` | **Ya** | Hapus satu riwayat deteksi |

Untuk detail lengkap request/response tiap endpoint (schema, contoh, kode error), lihat Swagger UI di `/docs` — dokumentasi itu selalu sinkron otomatis dengan kode backend.

## Struktur Project

```
src/
├── auth/           # Registrasi, login, OTP, JWT
├── detections/      # Deteksi scam (teks & gambar), riwayat
├── migrations/      # Alembic migration files
├── ml_models/        # File model ML (.pkl, dll)
├── config.py         # Konfigurasi global (baca dari .env)
├── database.py       # Setup koneksi database
├── main.py            # Entry point aplikasi
└── pagination.py      # Helper pagination generik
```

## Status Fitur

- ✅ Autentikasi lengkap (register, verifikasi OTP, login, resend OTP, lupa password)
- ✅ Deteksi scam dari teks (model ML asli sudah terpasang)
- 🚧 Deteksi scam dari gambar (OCR belum terintegrasi, masih pakai placeholder)
- 🚧 Automated testing (belum ada)
