# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.apis.v1.api import api_router
from app.core.config import settings

# Create database tables
print("Attempting to create database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables should be created if they didn't exist.")
except Exception as e:
    print(f"Error creating database tables: {e}")

fastapi_kwargs = {
    "title": settings.PROJECT_NAME,
    "version": "0.1.0"
}

if settings.ENV == 'prod':
    fastapi_kwargs["docs_url"] = None
    fastapi_kwargs["redoc_url"] = None
    fastapi_kwargs["openapi_url"] = None

app = FastAPI(**fastapi_kwargs)

# CORS Middleware configuration
if settings.ENV == 'nonprod':
    origins = [
        "http://localhost",
        "http://localhost:3000",  # Your Next.js frontend origin
        "http://127.0.0.1:3000",  # Another common local development address
        "http://192.168.1.3:3000",
        "https://motog-app-fe.vercel.app",
        "https://www.gomotog.com",
        "*",
    ]
elif settings.ENV == 'prod':
    origins = [
        "https://www.gomotog.com",
        "https://motog-app-fe-liart.vercel.app",
        "https://motog-app-fe.vercel.app",
        "http://localhost",
        "http://localhost:3000",  # Your Next.js frontend origin
        "http://127.0.0.1:3000",  # Another common local development address
        "http://192.168.1.3:3000",

    ]
else:
    origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to MotoG API!"}


@app.get(f"{settings.API_V1_STR}/test")
def test_api_v1():
    return {"message": "API V1 is working!"}
