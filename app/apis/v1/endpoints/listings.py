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

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET.get_secret_value()
)


@router.post("/", response_model=schemas.VehicleListing, status_code=status.HTTP_201_CREATED)
async def create_listing(
    listing: schemas.VehicleListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new vehicle listing.
    """
    listing_in = schemas.VehicleListingCreate(
        vehicle_type=listing.vehicle_type,
        reg_no=listing.reg_no,
        kilometers_driven=listing.kilometers_driven,
        price=listing.price,
        city=listing.city,
        seller_phone=listing.seller_phone,
        description=listing.description,
    )
    listing = crud.create_vehicle_listing(
        db=db,
        listing=listing_in,
        user_id=current_user.id,
    )

    listing.rc_details = listing.verification.raw_data
    if listing.owner:
        listing.owner_email = listing.owner.email
    else:
        owner = crud.get_user(db, user_id=listing.user_id)
        if owner:
            listing.owner_email = owner.email
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

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
    listing = crud.delete_listing(
        db, listing_id=listing_id, user_id=current_user.id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Listing not found or not authorized")


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
        raise HTTPException(
            status_code=404, detail="Listing not Found or Unauthorised")
    return update_listing


@router.post("/{listing_id}/images", response_model=List[schemas.ListingImage])
async def upload_listing_images(
    listing_id: int,
    files: List[UploadFile] = File(...),
    is_primary_flags: List[bool] = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if len(files) != len(is_primary_flags) or sum(is_primary_flags) != 1:
        raise HTTPException(
            status_code=400, detail="Mismatch in files and is_primary flags or more than 1 primary_flag as True")

    listing = crud.get_listing_by_id(db, listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Listing not found or Not Authorized")

    existing = crud.get_images_for_listing(db, listing_id)
    if len(existing) + len(files) > 5:
        raise HTTPException(
            status_code=400, detail="You can only upload up tp 5 images per listing")

    if any(img.is_primary for img in existing) and any(is_primary_flags):
        raise HTTPException(
            status_code=400, detail="A primary image already exists")

    image_data = []
    for i, file in enumerate(files):
        result = cloudinary.uploader.upload(file.file)
        url = result.get("secure_url")
        image_data.append({
            "url": url,
            "is_primary": is_primary_flags[i]
        })
    
    added_images = crud.add_listing_images(db, listing_id, image_data)
    return added_images


@router.delete("/images/{image_id}", status_code=204)
def delete_listing_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    image = crud.get_listing_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    listing = crud.get_listing_by_id(db, image.listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    crud.delete_listing_image(db, image_id)
    return


@router.put("/images/{image_id}", response_model=str)
async def update_listing_image(
    image_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    image = crud.get_listing_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    listing = crud.get_listing_by_id(db, image.listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = cloudinary.uploader.upload(file.file)
    updated = crud.update_listing_image_url(
        db, image_id, result.get("secure_url"))
    return updated.url
