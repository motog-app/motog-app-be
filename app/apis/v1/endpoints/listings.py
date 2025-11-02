from typing import List, Optional, Any

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    File, UploadFile, Form, BackgroundTasks
)
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

from app import crud, schemas, models
from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.core.config import settings
from app.helper.image_optimizer import optimize_image

router = APIRouter()

# Cloudinary config
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET.get_secret_value()
)


# --- Helper Utilities ---

def enrich_listing(listing: models.VehicleListing, db: Session):
    listing.rc_details = listing.verification.raw_data if listing.verification else None
    if not listing.owner:
        listing.owner = crud.get_user(db, user_id=listing.user_id)
    listing.owner_email = listing.owner.email if listing.owner else None


# --- Endpoints ---


@router.get("/my-listings", response_model=List[schemas.VehicleListing])
def get_my_listings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10,
):
    results = []
    listings_with_boost_status = crud.get_user_vehicle_listings(
        db=db, skip=skip, limit=limit, user_id=current_user.id)
    for listing, is_boosted in listings_with_boost_status:
        listing.rc_details = listing.verification.raw_data if listing.verification else None
        listing.owner_email = current_user.email
        listing.is_boosted = is_boosted
        results.append(listing)
    return results


@router.post("/", response_model=schemas.VehicleListing, status_code=status.HTTP_201_CREATED)
async def create_listing(
    listing: schemas.VehicleListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    if crud.get_active_listing_by_rc(db=db, rc=listing.reg_no):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active listing with the RC already exists.",
        )
    listing = crud.create_vehicle_listing(
        db=db, listing=listing, user_id=current_user.id)
    enrich_listing(listing, db)
    return listing


@router.get("/", response_model=List[schemas.VehicleListing])
def read_listings(
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    search_q: Optional[str] = None,
    vehicle_type: Optional[schemas.VehicleTypeEnum] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_km_driven: Optional[int] = None,
    max_km_driven: Optional[int] = None
) -> Any:
    listings = crud.get_vehicle_listings(
        db=db,
        lat=lat,
        lng=lng,
        skip=skip,
        limit=limit,
        q=search_q,
        vehicle_type=vehicle_type,
        min_price=min_price,
        max_price=max_price,
        min_year=min_year,
        max_year=max_year,
        min_km_driven=min_km_driven,
        max_km_driven=max_km_driven
    )
    results = []
    for listing, distance, is_boosted in listings:
        enrich_listing(listing, db)
        listing.distance = distance
        listing.is_boosted = is_boosted
        results.append(listing)
    return results


@router.get("/{listing_id}", response_model=schemas.VehicleListing)
def read_listing(listing_id: int,
                 background_tasks: BackgroundTasks,
                 db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user_optional)) -> Any:
    listing = crud.get_listing_by_id(db, listing_id=listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Add a background task to record the view
    background_tasks.add_task(
        crud.create_listing_view, db, listing_id=listing_id, user_id=current_user.id if current_user else None
    )

    enrich_listing(listing, db)
    if not current_user:
        listing.owner_email = "please@log.in"
        listing.seller_phone = "9876543210"
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing_by_id(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> None:
    listing = crud.delete_listing(
        db, listing_id=listing_id, user_id=current_user.id)
    if not listing:
        raise HTTPException(
            status_code=404, detail="Listing not found or not authorized")


@router.put("/{listing_id}", response_model=schemas.VehicleListing)
def update_listing(
    listing_id: int,
    listing_in: schemas.VehicleListingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    listing = crud.update_vehicle_listing(
        db, listing_id, listing_in, current_user.id)
    if not listing:
        raise HTTPException(
            status_code=404, detail="Listing not found or unauthorized")
    enrich_listing(listing, db)
    return listing


@router.patch("/{listing_id}/images/{image_id}/make-primary")
def set_primary_image(
    listing_id: int,
    image_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    listing = crud.get_listing_by_id(db, listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    crud.set_primary_image(db, listing_id, image_id)
    return {"detail": "Primary image updated"}


@router.post("/{listing_id}/images", response_model=List[schemas.ListingImage])
async def upload_listing_images(
    listing_id: int,
    files: List[UploadFile] = File(...),
    is_primary_flags: List[bool] = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if len(files) != len(is_primary_flags):
        raise HTTPException(400, "Number of files and flags mismatch")

    listing = crud.get_listing_by_id(db, listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(403, "Listing not found or not authorized")

    existing = crud.get_images_for_listing(db, listing_id)

    if not existing:
        if sum(is_primary_flags) != 1:
            raise HTTPException(
                400, "Exactly one image must be marked as primary")

    if len(existing) + len(files) > 5:
        raise HTTPException(400, "You can upload up to 5 images per listing")

    if any(img.is_primary for img in existing) and any(is_primary_flags):
        raise HTTPException(400, "A primary image already exists")

    image_data = []
    for i, file in enumerate(files):
        optimize_file = await optimize_image(file=file)
        if isinstance(optimize_file, dict) and "error" in optimize_file:
            raise HTTPException(status_code=400, detail=optimize_file["error"])
        result = cloudinary.uploader.upload(optimize_file, folder="listing")
        image_data.append({
            "url": result.get("secure_url"),
            "is_primary": is_primary_flags[i]
        })

    return crud.add_listing_images(db, listing_id, image_data)


@router.delete("/images/{image_id}", status_code=204)
def delete_listing_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    image = crud.get_listing_image(db, image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    listing = crud.get_listing_by_id(db, image.listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    crud.delete_listing_image(db, image_id)


@router.put("/images/{image_id}", response_model=str)
async def update_listing_image(
    image_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    image = crud.get_listing_image(db, image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    listing = crud.get_listing_by_id(db, image.listing_id)
    if not listing or listing.user_id != current_user.id:
        raise HTTPException(403, "Not authorized")

    optimize_file = await optimize_image(file=file)
    if isinstance(optimize_file, dict) and "error" in optimize_file:
        raise HTTPException(status_code=400, detail=optimize_file["error"])
    result = cloudinary.uploader.upload(optimize_file, folder="listing")
    updated = crud.update_listing_image_url(
        db, image_id, result.get("secure_url"))
    return updated.url
