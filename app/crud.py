# app/crud.py

import re
import json
import math
from typing import Optional, List
from datetime import datetime, timedelta

import googlemaps
import redis
from sqlalchemy import func, or_, and_, cast, Integer, bindparam, case, exists
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from . import models, schemas
from .core.config import settings
from .core.security import get_password_hash

gmaps = googlemaps.Client(key=settings.MAPS_API_KEY)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
GEOCODE_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


# --- Helper Functions ---


# --- User CRUD ---

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Vehicle Listing CRUD ---

def create_vehicle_listing(db: Session, listing: schemas.VehicleListingCreate, user_id: int):
    db_listing = models.VehicleListing(
        **listing.model_dump(),
        user_id=user_id,
        usr_inp_city=listing.city
    )
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing


def get_vehicle_listings(
    db: Session,
    lat: float,
    lng: float,
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None,
    vehicle_type: Optional[models.VehicleTypeEnum] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_km_driven: Optional[int] = None,
    max_km_driven: Optional[int] = None,
    owner_id: Optional[int] = None,
    radii: List[int] = [30, 60, 100],
    min_results: int = 10
):
    # Preprocess search query once outside the loop
    if q:
        q_clean = re.sub(r"[^a-zA-Z0-9\s]", "", q).lower().strip()
        keywords = q_clean.split()
    else:
        keywords = []

    for radius in radii:
        # Bounding box optimization
        R = 6371  # Earth radius in km
        delta_lat = radius / R
        delta_lng = radius / (R * math.cos(math.radians(lat)))

        min_lat = lat - math.degrees(delta_lat)
        max_lat = lat + math.degrees(delta_lat)
        min_lng = lng - math.degrees(delta_lng)
        max_lng = lng + math.degrees(delta_lng)

        # Haversine distance expression
        haversine_formula = 6371 * func.acos(
            func.greatest(-1.0, func.least(1.0, 
                func.cos(func.radians(bindparam('lat'))) *
                func.cos(func.radians(models.VehicleListing.latitude)) *
                func.cos(func.radians(models.VehicleListing.longitude) - func.radians(bindparam('lng'))) +
                func.sin(func.radians(bindparam('lat'))) *
                func.sin(func.radians(models.VehicleListing.latitude))
            ))
        )

        # Boost status subquery/CTE could be complex. We'll create a case statement.
        # This determines if a listing is boosted.
        now = datetime.utcnow()
        is_boosted_case = case(
            (
                exists().where(
                    and_(
                        models.UserBoost.listing_id == models.VehicleListing.id,
                        models.UserBoost.start_date <= now,
                        models.UserBoost.end_date >= now,
                    )
                ) |
                exists().where(
                    and_(
                        models.UserBoost.user_id == models.VehicleListing.user_id,
                        models.UserBoost.listing_id.is_(None), # Bundle boost
                        models.UserBoost.start_date <= now,
                        models.UserBoost.end_date >= now,
                    )
                ), 
                True
            ),
            else_=False
        ).label("is_boosted")

        # Base query
        query = (
            db.query(models.VehicleListing,
                     haversine_formula.label("distance"),
                     is_boosted_case)
            .join(
                models.VehicleVerification,
                models.VehicleListing.reg_no == models.VehicleVerification.reg_no
            )
            .join(
                models.ListingImage,
                models.VehicleListing.id == models.ListingImage.listing_id
            )
            .filter(models.VehicleListing.is_active.is_(True))
            .filter(models.VehicleListing.latitude.between(min_lat, max_lat))
            .filter(models.VehicleListing.longitude.between(min_lng, max_lng))
            .filter(haversine_formula < radius)
            .filter(models.ListingImage.listing_id.isnot(None))
        )

        # Text search filtering
        if keywords:
            search_conditions = [
                func.lower(
                    func.trim(
                        models.VehicleVerification.raw_data['vehicle_manufacturer_name'].astext)
                ).ilike(f"%{kw}%") |
                func.lower(
                    func.trim(
                        models.VehicleVerification.raw_data['model'].astext)
                ).ilike(f"%{kw}%")
                for kw in keywords
            ]
            query = query.filter(and_(*search_conditions))

        # Apply numeric filters only if provided
        if vehicle_type:
            query = query.filter(
                models.VehicleListing.vehicle_type == vehicle_type)
        if min_price is not None:
            query = query.filter(models.VehicleListing.price >= min_price)
        if max_price is not None:
            query = query.filter(models.VehicleListing.price <= max_price)
        if min_km_driven is not None:
            query = query.filter(
                models.VehicleListing.kilometers_driven >= min_km_driven)
        if max_km_driven is not None:
            query = query.filter(
                models.VehicleListing.kilometers_driven <= max_km_driven)
        if owner_id is not None:
            query = query.filter(models.VehicleListing.user_id == owner_id)

        # Year filter — calculate only if needed
        if min_year or max_year:
            mfg_year = cast(
                func.substring(
                    models.VehicleVerification.raw_data['reg_date'].astext,
                    1,
                    4
                ),
                Integer
            )
            if min_year:
                query = query.filter(mfg_year >= min_year)
            if max_year:
                query = query.filter(mfg_year <= max_year)

        # Ordering — extract date only once
        mfg_date = func.to_date(
            models.VehicleVerification.raw_data['reg_date'].astext,
            'YYYY-MM-DD'
        )

        # Final query execution
        results = (
            query
            .distinct(
                is_boosted_case,
                haversine_formula.label("distance"),
                mfg_date,
                models.VehicleListing.id
            )
            .order_by(
                is_boosted_case.desc(), # Boosted listings first
                haversine_formula.label("distance"),
                mfg_date.desc(),
                models.VehicleListing.id.desc() # Added for stable DISTINCT ON ordering
            )
            .params(lat=lat, lng=lng)
            .offset(skip)
            .limit(limit)
            .all()
        )

        if len(results) >= min_results:
            return results

    return results


def get_listing_by_id(db: Session, listing_id: int):
    return db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.is_active == True
    ).first()


def get_listing_by_rc(db: Session, rc: str):
    return db.query(models.VehicleListing).filter(models.VehicleListing.reg_no == rc).first()


def get_active_listing_by_rc(db: Session, rc: str):
    return db.query(models.VehicleListing).filter(models.VehicleListing.reg_no == rc, models.VehicleListing.is_active == True).first()


def get_user_vehicle_listings(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 10
):
    now = datetime.utcnow()
    is_boosted_case = case(
        (
            exists().where(
                and_(
                    models.UserBoost.listing_id == models.VehicleListing.id,
                    models.UserBoost.start_date <= now,
                    models.UserBoost.end_date >= now,
                )
            ) |
            exists().where(
                and_(
                    models.UserBoost.user_id == models.VehicleListing.user_id,
                    models.UserBoost.listing_id.is_(None), # Bundle boost
                    models.UserBoost.start_date <= now,
                    models.UserBoost.end_date >= now,
                )
            ),
            True
        ),
        else_=False
    ).label("is_boosted")

    return (
        db.query(models.VehicleListing, is_boosted_case)
        .filter(models.VehicleListing.user_id == user_id)
        .filter(models.VehicleListing.is_active == True)
        .order_by(is_boosted_case.desc(), models.VehicleListing.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_listing(db: Session, listing_id: int, user_id: int):
    listing = db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.user_id == user_id
    ).first()

    if listing:
        listing.is_active = False
        db.commit()
        db.refresh(listing)
        return listing
    return None


def update_vehicle_listing(db: Session, listing_id: int, listing_in: schemas.VehicleListingUpdate, user_id: int):
    listing = db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.user_id == user_id
    ).first()

    if not listing:
        return None

    data = listing_in.model_dump(exclude_unset=True)

    if "city" in data:
        # If city is updated, ensure lat/lng are also provided
        if "latitude" not in data or "longitude" not in data:
            raise HTTPException(
                status_code=400, detail="Latitude and longitude must be provided when updating city.")
        # Update usr_inp_city to match the new city
        data["usr_inp_city"] = data["city"]

    for k, v in data.items():
        setattr(listing, k, v)

    db.commit()
    db.refresh(listing)
    return listing


def get_verification_by_reg_no(db: Session, reg_no: str):
    return db.query(models.VehicleVerification).filter_by(reg_no=reg_no).first()


def create_verification(db: Session, reg_no: str, status: str, raw_data: dict):
    verification = models.VehicleVerification(
        reg_no=reg_no, status=status, raw_data=raw_data)
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def add_listing_images(db: Session, listing_id: int, images_data: List[dict]):
    images = [
        models.ListingImage(
            listing_id=listing_id,
            url=data["url"],
            is_primary=data.get("is_primary", False)
        )
        for data in images_data
    ]
    db.add_all(images)
    db.commit()
    return images


def get_images_for_listing(db: Session, listing_id: int):
    return db.query(models.ListingImage).filter_by(listing_id=listing_id).all()


def get_primary_image_for_listing(db: Session, listing_id: int):
    return db.query(models.ListingImage).filter(models.ListingImage.listing_id == listing_id, models.ListingImage.is_primary == True).first()


def get_listing_image(db: Session, image_id: int):
    return db.query(models.ListingImage).filter_by(id=image_id).first()


def delete_listing_image(db: Session, image_id: int):
    image = get_listing_image(db, image_id)
    if image:
        db.delete(image)
        db.commit()
        return True
    return False


def update_listing_image_url(db: Session, image_id: int, new_url: str):
    image = get_listing_image(db, image_id)
    if image:
        image.url = new_url
        db.commit()
        db.refresh(image)
        return image
    return None


def get_homepage_listings(db: Session, lat: float, lng: float, limit: int = 12):
    # Use the optimized get_vehicle_listings for homepage listings
    # Default to a reasonable radius for homepage, e.g., 100 km
    return get_vehicle_listings(db=db, lat=lat, lng=lng, limit=limit, radii=[100], min_results=5)


def set_primary_image(db: Session, listing_id: int, image_id: str):
    # Set all others to non-primary
    db.query(models.ListingImage).filter(
        models.ListingImage.listing_id == listing_id
    ).update({models.ListingImage.is_primary: False})

    # Set the new primary
    db.query(models.ListingImage).filter(
        models.ListingImage.id == image_id,
        models.ListingImage.listing_id == listing_id
    ).update({models.ListingImage.is_primary: True})

    db.commit()

# --- Boost CRUD ---

def list_boost_packages(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.BoostPackage).filter(models.BoostPackage.is_active == True).offset(skip).limit(limit).all()

def create_user_boost(db: Session, user_id: int, boost_in: schemas.UserBoostCreate):
    # 1. Get the package details
    package = db.query(models.BoostPackage).filter(models.BoostPackage.id == boost_in.package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Boost package not found")
    if not package.is_active:
        raise HTTPException(status_code=400, detail="Boost package is not active")

    # 2. Validate listing for single_listing boosts
    if package.type == 'single_listing':
        if not boost_in.listing_id:
            raise HTTPException(status_code=400, detail="listing_id is required for this package type")
        listing = db.query(models.VehicleListing).filter(
            models.VehicleListing.id == boost_in.listing_id,
            models.VehicleListing.user_id == user_id
        ).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found or you do not own this listing")

    # 3. Create the boost record
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=package.duration_days)

    db_user_boost = models.UserBoost(
        user_id=user_id,
        package_id=boost_in.package_id,
        listing_id=boost_in.listing_id if package.type == 'single_listing' else None,
        start_date=start_date,
        end_date=end_date
    )
    db.add(db_user_boost)
    db.commit()
    db.refresh(db_user_boost)
    return db_user_boost

def is_listing_boosted(db: Session, listing_id: int, user_id: int) -> bool:
    now = datetime.utcnow()
    # Check for a direct, active boost on the listing
    direct_boost = db.query(models.UserBoost).filter(
        models.UserBoost.listing_id == listing_id,
        models.UserBoost.start_date <= now,
        models.UserBoost.end_date >= now
    ).first()

    if direct_boost:
        return True

    # Check for an active bundle boost on the user
    bundle_boost = db.query(models.UserBoost).filter(
        models.UserBoost.user_id == user_id,
        models.UserBoost.listing_id.is_(None), # This identifies a bundle boost
        models.UserBoost.start_date <= now,
        models.UserBoost.end_date >= now
    ).first()

    return bundle_boost is not None