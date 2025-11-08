# app/apis/v1/endpoints/stats.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.database import SessionLocal
from app.dependencies import get_db

router = APIRouter()

@router.get("/listings/{listing_id}/stats", response_model=schemas.ListingStats)
def get_listing_stats(listing_id: int, db: Session = Depends(get_db)):
    """
    Retrieve view statistics for a specific listing.
    """
    total_views = crud.get_total_listing_views(db, listing_id=listing_id)
    views_last_7_days = crud.get_listing_views_last_n_days(db, listing_id=listing_id, days=7)

    return schemas.ListingStats(
        total_views=total_views,
        views_last_7_days=views_last_7_days,
    )
