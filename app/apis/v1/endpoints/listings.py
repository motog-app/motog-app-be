# backend/app/apis/v1/endpoints/listings.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Any, Optional
import cloudinary
import cloudinary.uploader

from app import crud, schemas, models # Absolute imports
from app.database import get_db
from app.dependencies import get_current_active_user # For protected routes
from app.core.config import settings

router = APIRouter()

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

@router.post("/", response_model=schemas.VehicleListing, status_code=status.HTTP_201_CREATED)
async def create_listing(
    # Use Form() for regular fields when mixing with File()
    vehicle_type: models.VehicleTypeEnum = Form(...),
    make: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    kilometers_driven: int = Form(...),
    price: int = Form(...),
    city: str = Form(...),
    seller_phone: str = Form(...),
    description: Optional[str] = Form(None),
    primary_image: UploadFile = File(...), # The uploaded image file
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new vehicle listing. Requires authentication.
    """
    try:
        # Upload image to Cloudinary
        upload_result = cloudinary.uploader.upload(primary_image.file, folder="motoflip_listings")
        image_url = upload_result.get("secure_url")

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to Cloudinary."
            )

        # Create Pydantic schema instance from form data and image URL
        listing_in = schemas.VehicleListingCreate(
            vehicle_type=vehicle_type,
            make=make,
            model=model,
            year=year,
            kilometers_driven=kilometers_driven,
            price=price,
            city=city,
            seller_phone=seller_phone,
            description=description,
            primary_image_url=image_url
        )

        listing = crud.create_vehicle_listing(db=db, listing=listing_in, user_id=current_user.id)
        # Populate owner_email for response
        listing.owner_email = current_user.email
        return listing
    except Exception as e:
        # Log the error for debugging
        print(f"Error creating listing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the listing: {e}"
        )


@router.get("/", response_model=List[schemas.VehicleListing])
def read_listings(
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None,
    city: Optional[str] = None,
    vehicle_type: Optional[models.VehicleTypeEnum] = None,
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve multiple vehicle listings with optional filters and search.
    """
    listings = crud.get_listings(
        db,
        skip=skip,
        limit=limit,
        q=q,
        city=city,
        vehicle_type=vehicle_type
    )
    # Populate owner_email for response schema
    for listing in listings:
        if listing.owner: # Check if owner relationship is loaded
            listing.owner_email = listing.owner.email
        else: # If not loaded, fetch it (less efficient, but handles cases where owner isn't eagerly loaded)
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
    
    # Populate owner_email for response schema
    if listing.owner:
        listing.owner_email = listing.owner.email
    else:
        owner = crud.get_user(db, user_id=listing.user_id)
        if owner:
            listing.owner_email = owner.email

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
    listing = crud.get_listing_by_id(db, listing_id=listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    
    if listing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this listing"
        )
    
    crud.delete_listing(db, listing_id=listing_id, user_id=current_user.id)
    return # FastAPI handles 204 No Content for None return