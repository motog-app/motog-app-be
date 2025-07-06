# app/helper/email.py
from app.core.config import settings
from app.core.security import create_email_verification_token, create_password_reset_token
from .email_sender import send_email

async def send_verification_email(email: str):
    token = create_email_verification_token(email)
    # verification_url = f"{settings.FRONTEND_SERVER_HOST}/api/v1/verify-email?token={token}"
    verification_url = f"{settings.FRONTEND_SERVER_HOST}/verify-email/{token}"
    
    html_content = f"""
    <html>
    <body>
        <h2>Hello,</h2>
        <p>Thank you for registering with MotoG. Please click the link below to verify your email address:</p>
        <a href="{verification_url}">Verify Email</a>
        <p>If you did not register, please ignore this email.</p>
    </body>
    </html>
    """
    
    await send_email(email_to=email, subject="Verify Your Email", body=html_content)

async def send_password_reset_email(email: str):
    token = create_password_reset_token(email)
    # reset_url = f"{settings.FRONTEND_SERVER_HOST}/api/v1/reset-password?token={token}"
    reset_url = f"{settings.FRONTEND_SERVER_HOST}/reset-password/{token}"

    html_content = f"""
    <html>
    <body>
        <h2>Hello,</h2>
        <p>You have requested to reset your password. Please click the link below to reset it:</p>
        <a href="{reset_url}">Reset Password</a>
        <p>This link is valid for {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not request a password reset, please ignore this email.</p>
    </body>
    </html>
    """

    await send_email(email_to=email, subject="Password Reset Request", body=html_content)
