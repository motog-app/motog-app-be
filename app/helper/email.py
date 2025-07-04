# app/helper/email.py
from app.core.config import settings
from app.core.security import create_email_verification_token
from .email_sender import send_email

async def send_verification_email(email: str):
    token = create_email_verification_token(email)
    verification_url = f"{settings.SERVER_HOST}/api/v1/verify-email?token={token}"
    
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
