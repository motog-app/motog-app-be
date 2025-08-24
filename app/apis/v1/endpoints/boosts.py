# app/apis/v1/endpoints/boosts.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models
from app.dependencies import get_db, get_current_user

router = APIRouter()

@router.get("/packages", response_model=List[schemas.BoostPackage])
def list_boost_packages(db: Session = Depends(get_db)):
    """
    Get a list of all available boost packages.
    """
    packages = crud.list_boost_packages(db=db)
    return packages

@router.post("/", response_model=schemas.UserBoost)
def create_user_boost(
    boost_in: schemas.UserBoostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Purchase a boost package.

    - For **single_listing** type packages, the `listing_id` must be provided.
    - For **bundle** type packages, the `listing_id` should be omitted.
    """
    try:
        user_boost = crud.create_user_boost(db=db, user_id=current_user.id, boost_in=boost_in)
        return user_boost
    except HTTPException as e:
        raise e
    except Exception as e:
        # Generic error for unexpected issues
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
