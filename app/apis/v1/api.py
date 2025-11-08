# backend/app/apis/v1/api.py
from fastapi import APIRouter
from .endpoints import auth, listings, vehicle_verification, location_services, discovery, boosts, stats
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
api_router.include_router(listings.router, prefix=settings.API_V1_STR + "/listings", tags=["listings"])
api_router.include_router(boosts.router, prefix=settings.API_V1_STR + "/boosts", tags=["boosts"])
api_router.include_router(stats.router, prefix=settings.API_V1_STR + "/stats", tags=["stats"])
api_router.include_router(vehicle_verification.router, prefix=settings.API_V1_STR, tags=["Vehicle Verification"])
api_router.include_router(location_services.router, prefix=settings.API_V1_STR, tags=["Location Services"])
api_router.include_router(discovery.router, prefix=settings.API_V1_STR, tags=["discovery"])

@api_router.get("/test") # Keep for testing if needed
async def test_v1_route():
    return {"message": "API V1 is working!"}