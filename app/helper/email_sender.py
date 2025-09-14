# app/helper/email_sender.py
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

async def _get_zoho_access_token() -> str:
    """
    Generates a new Zoho access token using the refresh token.
    """
    if not all([settings.ZOHO_MAIL_CLIENT_ID, settings.ZOHO_MAIL_CLIENT_SECRET, settings.ZOHO_MAIL_REFRESH_TOKEN, settings.ZOHO_MAIL_REGION]):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Zoho Mail is not configured.")

    token_url = f"https://accounts.zoho.{settings.ZOHO_MAIL_REGION}/oauth/v2/token"
    data = {
        "refresh_token": settings.ZOHO_MAIL_REFRESH_TOKEN.get_secret_value(),
        "client_id": settings.ZOHO_MAIL_CLIENT_ID,
        "client_secret": settings.ZOHO_MAIL_CLIENT_SECRET.get_secret_value(),
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            if "access_token" not in token_data:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve Zoho access token.")
            return token_data["access_token"]
        except httpx.HTTPStatusError as e:
            # Log the error details for debugging
            print(f"Error refreshing Zoho token: {e.response.text}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not refresh Zoho authentication token.")
        except Exception as e:
            print(f"An unexpected error occurred while refreshing token: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


async def send_email(email_to: str, subject: str, body: str):
    """
    Sends an email using the Zoho Mail API.
    """
    if not settings.ZOHO_MAIL_ACCOUNT_ID:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Zoho Account ID is not configured.")

    try:
        access_token = await _get_zoho_access_token()
        
        api_url = f"https://mail.zoho.{settings.ZOHO_MAIL_REGION}/api/accounts/{settings.ZOHO_MAIL_ACCOUNT_ID}/messages"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json",
        }
        
        json_payload = {
            "fromAddress": settings.SMTP_FROM_EMAIL,
            "toAddress": email_to,
            "subject": subject,
            "content": body,
            "askReceipt": "no" # Or "yes" if you want read receipts
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, headers=headers, json=json_payload)
            response.raise_for_status()

    except HTTPException as e:
        # Re-raise HTTPExceptions from _get_zoho_access_token
        raise e
    except httpx.HTTPStatusError as e:
        # Log the error for debugging
        print(f"Error sending email via Zoho: {e.response.text}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email.")
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while sending email.")