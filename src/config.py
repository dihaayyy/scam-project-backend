from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    database_test_url: str | None = None
    database_echo: bool = False
    # Vercel otomatis mengisi VERCEL=1 saat aplikasi berjalan di sana.
    vercel: bool = False
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    otp_expire_minutes: int = 10

    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    mail_from_name: str = "Scam Project"
    # Default untuk Mailpit lokal; SMTP asli/Mailtrap butuh STARTTLS + credentials.
    mail_starttls: bool = False
    mail_ssl_tls: bool = False
    mail_use_credentials: bool = False
    mail_validate_certs: bool = False

    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    guest_detection_limit: int = 3
    guest_limit_window_hours: int = 24 

settings = Settings()  #type: ignore[call-arg]
