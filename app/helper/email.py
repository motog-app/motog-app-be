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
        <body style="margin:0; padding:0; background:#f4f6f8; font-family:Arial, sans-serif; color:#333;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:30px 0;">
            <tr>
                <td align="center">
                <!-- Outer Card -->
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:10px; padding:40px 30px;">
                    <!-- Logo -->
                    <tr>
                    <td align="center" style="padding-bottom:20px;">
                        <img src="https://storage.googleapis.com/motog-bucket/public/motog.png"
                            alt="MotoG India"
                            width="120"
                            style="display:block;">
                    </td>
                    </tr>

                    <!-- Heading -->
                    <tr>
                    <td align="center" style="font-size:22px; font-weight:bold; color:#222; padding-bottom:15px;">
                        Welcome to MotoG India!
                    </td>
                    </tr>

                    <!-- Message -->
                    <tr>
                    <td style="font-size:16px; line-height:1.6; text-align:center; padding:0 20px 25px;">
                        Thank you for registering with MotoG India.<br>
                        We are excited to have you on board!<br><br>
                        Please confirm your email address by clicking the button below:
                    </td>
                    </tr>

                    <!-- Button -->
                    <tr>
                    <td align="center" style="padding-bottom:30px;">
                        <a href="{verification_url}"
                        style="
                            display:inline-block;
                            background-color:#007BFF;
                            color:#ffffff;
                            text-decoration:none;
                            padding:14px 30px;
                            border-radius:6px;
                            font-weight:bold;
                            font-size:16px;
                            letter-spacing:0.5px;
                        ">
                        Verify My Email
                        </a>
                    </td>
                    </tr>

                    <!-- Footer text -->
                    <tr>
                    <td style="font-size:14px; line-height:1.6; text-align:center; color:#666; padding:0 20px;">
                        This quick step helps us secure your account and ensure it’s really you.<br><br>
                        If you didn’t sign up for MotoG India, you can safely ignore this message.
                    </td>
                    </tr>

                    <tr>
                    <td align="center" style="padding-top:25px; font-size:14px; color:#333;">
                        — Team MotoG India
                    </td>
                    </tr>
                </table>
                <!-- End Outer Card -->
                </td>
            </tr>
            </table>
        </body>
    </html>

    """

    await send_email(email_to=email, subject="Motog - Verify Your Email", body=html_content)


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
