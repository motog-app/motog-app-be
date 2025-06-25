# backend/app/apis/v1/endpoints/listings.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Any, Optional
import cloudinary
import cloudinary.uploader

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_active_user
from app.core.config import settings

router = APIRouter()

# Configure Cloudinary - CORRECTED USAGE for API_KEY and API_SECRET
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,  # Use directly as it's a string
    api_secret=settings.CLOUDINARY_API_SECRET.get_secret_value() # Use .get_secret_value() as it's a SecretStr
)

@router.post("/", response_model=schemas.VehicleListing, status_code=status.HTTP_201_CREATED)
async def create_listing(
    vehicle_type: schemas.VehicleTypeEnum = Form(...),
    reg_no: str = Form(...),
    # make: str = Form(...),
    # model: str = Form(...),
    # year: int = Form(...),
    kilometers_driven: int = Form(...),
    price: int = Form(...),
    city: str = Form(...),
    # latitude: float = Form(...),
    # longitude: float = Form(...),
    seller_phone: str = Form(...),
    description: Optional[str] = Form(None),
    primary_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new vehicle listing.
    """
    image_url = None
    if primary_image:
        try:
            upload_result = cloudinary.uploader.upload(primary_image.file)
            image_url = upload_result.get("secure_url")
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Image upload failed: {e}")

    listing_in = schemas.VehicleListingCreate(
        vehicle_type=vehicle_type,
        reg_no=reg_no,
        # make=make,
        # model=model,
        # year=year,
        kilometers_driven=kilometers_driven,
        price=price,
        usr_inp_city=city,
        city=city,
        # latitude=latitude,
        # longitude=longitude,
        seller_phone=seller_phone,
        description=description,
        primary_image_url=image_url,
    )

    listing = crud.create_vehicle_listing(
        db=db,
        listing=listing_in,
        user_id=current_user.id,
    )
    return listing


@router.get("/", response_model=List[schemas.VehicleListing])
def read_listings(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    city: Optional[str] = None,
    vehicle_type: Optional[schemas.VehicleTypeEnum] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_km_driven: Optional[int] = None,
    max_km_driven: Optional[int] = None
) -> Any:
    """
    Retrieve multiple vehicle listings with optional filters.
    """
    listings = crud.get_vehicle_listings(
        db=db,
        skip=skip,
        limit=limit,
        city=city,
        vehicle_type=vehicle_type,
        min_price=min_price,
        max_price=max_price,
        min_year=min_year,
        max_year=max_year,
        min_km_driven=min_km_driven,
        max_km_driven=max_km_driven
    )
    for listing in listings:
        listing.rc_details = listing.verification.raw_data
        if listing.owner:
            listing.owner_email = listing.owner.email
        else:
            owner = crud.get_user(db, user_id=listing.user_id)
            if owner:
                listing.owner_email = owner.email
    return listings


@router.get("/{listing_id}", response_model=schemas.VehicleListing)
def read_listing(listing_id: int, db: Session = Depends(get_db)) -> Any:
    """
    Retrieve a single vehicle listing by ID.
    """
    listing = crud.get_listing_by_id(db, listing_id=listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if listing.owner:
        listing.owner_email = listing.owner.email
    else:
        owner = crud.get_user(db, user_id=listing.user_id)
        if owner:
            listing.owner_email = owner.email
    listing.rc_details = listing.verification.raw_data
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing_by_id(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> None:
    """
    Deactivate (soft delete) a vehicle listing by its owner.
    """
    listing = crud.delete_listing(db, listing_id=listing_id, user_id=current_user.id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found or not authorized")
    

@router.put("/{listing_id}", response_model=schemas.VehicleListing)
def update_listing(
    listing_id: int,
    listing_in: schemas.VehicleListingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    update_listing = crud.update_vehicle_listing(
        db=db,
        listing_id=listing_id,
        listing_in=listing_in,
        user_id=current_user.id
    )
    if not update_listing:
        raise HTTPException(status_code=404, detail="Listing not Found or Unauthorised")
    return update_listing