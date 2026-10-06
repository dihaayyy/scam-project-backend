from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from src.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=settings.mail_use_credentials,
    VALIDATE_CERTS=settings.mail_validate_certs,
)

fm = FastMail(conf)

async def send_otp_email(email: str, otp_code: str) -> None:
    message = MessageSchema(
        subject="Your OTP Code",
        recipients=[email],
        body=f"<p>Your OTP code is: <b>{otp_code}</b></p>",
        subtype="html",
    )
    await fm.send_message(message)

async def send_password_reset_email(email: str, otp_code: str) -> None:
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"<p>Your password reset OTP code is: <b>{otp_code}</b></p>",
        subtype="html",
    )
    await fm.send_message(message)