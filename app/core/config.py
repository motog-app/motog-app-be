# backend/app/core/config.py
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load .env file from the backend directory, one level up from core
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".env"))


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_default_secret_key_if_not_set")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    # New: Google Maps API Key
    Maps_API_KEY: str = os.getenv("Maps_API_KEY", "")
    
    # New: Redis URL
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0") # Default for local dev

    class Config:
        env_file = ".env" # Not strictly needed if load_dotenv is used correctly above
        case_sensitive = True


settings = Settings()