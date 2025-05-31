# backend/app/main.py
from fastapi import FastAPI
from .database import engine, Base
from . import models # <--- ADD THIS LINE TO EXPLICITLY IMPORT MODELS
from .apis.v1.api import api_router as api_v1_router # Ensure this is below models import if it uses models

# Create database tables
# This ensures that all models that inherit from Base are known to SQLAlchemy
# before trying to create tables.
print("Attempting to create database tables...") # Add a print statement for feedback
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables should be created if they didn't exist.")
except Exception as e:
    print(f"Error creating database tables: {e}") # Print any exception

app = FastAPI(
    title="MotoG Clone API - www.gomotog.com",
    description="API for buying and selling used cars and bikes.",
    version="0.1.0"
)

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to MotoG Clone API!"}

# Include the API router
app.include_router(api_v1_router, prefix="/api/v1")