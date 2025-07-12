# backend/app/apis/v1/endpoints/discovery.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Any, Optional

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user
from app.core.config import settings

router = APIRouter()

@router.get("/homepage-listings", response_model=List[schemas.VehicleListing])
def homepage_listings(lat: float, lng: float, db: Session = Depends(get_db)):
    listings = crud.get_homepage_listings(db, lat=lat, lng=lng)
    for listing, distance in listings:
        if listing.owner:
            listing.owner_email = listing.owner.email
        else:
            owner = crud.get_user(db, user_id=listing.user_id)
            if owner:
                listing.owner_email = owner.email
        listing.rc_details = listing.verification.raw_data
        listing.distance = distance
    return [listing for listing, distance in listings]

def boosted(): pass

def trending(): pass

def liked_by_friends(): pass

def recommended(): pass

def reviewed_sellers(): pass