# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, SecretStr, Field
from typing import Optional

class Settings(BaseSettings):
    # This is the Pydantic v2 way to configure settings loading:
    # It tells Pydantic to load from .env, allows case-insensitivity,
    # and critically, allows for extra fields not explicitly defined here
    # without raising a validation error.
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, extra='ignore')

    # Project Settings
    # Pydantic will now automatically look for PROJECT_NAME in .env or environment variables
    # and use "MotoG API" as a default if not found.
    PROJECT_NAME: str = Field("MotoG API", env="PROJECT_NAME")
    API_V1_STR: str = Field(env="API_V1_STR")
    ENV: str = Field("nonprod", env="ENV")
    FRONTEND_SERVER_HOST: str = Field("http://localhost:8000", env="FRONTEND_SERVER_HOST")

    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL") # '...' makes this field required

    # JWT Authentication Settings
    SECRET_KEY: SecretStr = Field(..., env="SECRET_KEY") # Required secret
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = Field(15, env="EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES")
    EMAIL_RESEND_COOLDOWN_SECONDS: int = Field(60, env="EMAIL_RESEND_COOLDOWN_SECONDS")
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(60, env="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES")

    # Cloudinary Settings (Optional, as they might not always be set)
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(None, env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = Field(None, env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[SecretStr] = Field(None, env="CLOUDINARY_API_SECRET")

    # Google Maps API Key
    MAPS_API_KEY: Optional[str] = Field(None, env="MAPS_API_KEY") # Renamed to MAPS_API_KEY for consistency

    # Redis URL (with a default for local development)
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    CASHFREE_API_URL: Optional[str] = Field(None, env="CASHFREE_API_URL")
    CASHFREE_CLIENT_ID: Optional[str] = Field(None, env="CASHFREE_CLIENT_ID")
    CASHFREE_CLIENT_SECRET: Optional[str] = Field(None, env="CASHFREE_CLIENT_SECRET")

    # Email settings
    # SMTP_HOST: str = Field(..., env="SMTP_HOST")
    # SMTP_PORT: int = Field(..., env="SMTP_PORT")
    # SMTP_USER: str = Field(..., env="SMTP_USER")
    # SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: EmailStr = Field(..., env="SMTP_FROM_EMAIL")

    # Zoho Mail
    ZOHO_MAIL_CLIENT_ID: Optional[str] = Field(None, env="ZOHO_MAIL_CLIENT_ID")
    ZOHO_MAIL_CLIENT_SECRET: Optional[SecretStr] = Field(None, env="ZOHO_MAIL_CLIENT_SECRET")
    ZOHO_MAIL_REFRESH_TOKEN: Optional[SecretStr] = Field(None, env="ZOHO_MAIL_REFRESH_TOKEN")
    ZOHO_MAIL_REGION: Optional[str] = Field("com", env="ZOHO_MAIL_REGION")
    ZOHO_MAIL_ACCOUNT_ID: Optional[str] = Field(None, env="ZOHO_MAIL_ACCOUNT_ID")

settings = Settings()