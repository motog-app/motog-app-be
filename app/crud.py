# app/crud.py

import re
from typing import Optional, List

import googlemaps
import redis
from sqlalchemy import func, or_, cast, Integer
from sqlalchemy.orm import Session

from . import models, schemas
from .core.config import settings
from .core.security import get_password_hash

gmaps = googlemaps.Client(key=settings.MAPS_API_KEY)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
GEOCODE_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


# --- Helper Functions ---

def _resolve_city_location(input_city: str):
    resolved = {input_city.lower()}
    lat, lng = None, None

    try:
        geocode_result = gmaps.geocode(input_city)
        if geocode_result:
            loc = geocode_result[0]["geometry"]["location"]
            lat, lng = loc["lat"], loc["lng"]

            for comp in geocode_result[0]["address_components"]:
                types = comp.get("types", [])
                if any(t in types for t in ["sublocality", "locality", "administrative_area_level_2", "administrative_area_level_1"]):
                    resolved.update(
                        {comp["long_name"].lower(), comp["short_name"].lower()})

            if "delhi" in resolved:
                resolved.add("new delhi")

    except Exception as e:
        print(f"Google Maps API error: {e}")

    return "|".join(sorted(resolved)), lat, lng


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
    location_string, lat, lng = _resolve_city_location(listing.city)

    db_listing = models.VehicleListing(
        **listing.model_dump(exclude={"city"}),
        user_id=user_id,
        city=location_string,
        usr_inp_city=listing.city,
        latitude=lat,
        longitude=lng
    )
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing


def get_vehicle_listings(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    city: Optional[str] = None,
    vehicle_type: Optional[models.VehicleTypeEnum] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    min_km_driven: Optional[int] = None,
    max_km_driven: Optional[int] = None,
    owner_id: Optional[int] = None,
):
    query = (
        db.query(models.VehicleListing)
        .join(models.VehicleVerification, models.VehicleListing.reg_no == models.VehicleVerification.reg_no)
        .filter(models.VehicleListing.is_active == True)
    )

    if city:
        query = query.filter(
            models.VehicleListing.city.ilike(f"%{city.lower()}%"))
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

    mfg_year = cast(func.substring(
        models.VehicleVerification.raw_data['vehicle_manufacturing_month_year'].astext, 4, 4
    ), Integer)

    if min_year:
        query = query.filter(mfg_year >= min_year)
    if max_year:
        query = query.filter(mfg_year <= max_year)

    return query.order_by(models.VehicleListing.created_at.desc()).offset(skip).limit(limit).all()


def get_listing_by_id(db: Session, listing_id: int):
    return db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.is_active == True
    ).first()


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
        data["usr_inp_city"] = data["city"]
        data["city"], data["latitude"], data["longitude"] = _resolve_city_location(
            data["city"])

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


def get_homepage_listings(db: Session, city_input: str, limit: int = 10):
    city_input = city_input.lower().strip()
    subquery = db.query(models.ListingImage.id).filter(
        models.ListingImage.listing_id == models.VehicleListing.id).exists()

    return db.query(models.VehicleListing).filter(
        models.VehicleListing.is_active == True,
        models.VehicleListing.city.ilike(f"%{city_input}%"),
        subquery
    ).order_by(models.VehicleListing.created_at.desc()).limit(limit).all()


def search_vehicle_listings(db: Session, q: str, skip: int = 0, limit: int = 10):
    q = re.sub(r"[^a-zA-Z0-9\s]", "", q).lower().strip()
    keywords = q.split()

    query = (
        db.query(models.VehicleListing)
        .join(models.VehicleVerification, models.VehicleListing.reg_no == models.VehicleVerification.reg_no)
        .filter(models.VehicleListing.is_active == True)
    )

    if keywords:
        conditions = [
            func.lower(models.VehicleVerification.raw_data['vehicle_manufacturer_name'].astext).ilike(f"%{kw}%") |
            func.lower(models.VehicleVerification.raw_data['model'].astext).ilike(
                f"%{kw}%")
            for kw in keywords
        ]
        query = query.filter(or_(*conditions))

    mfg_date = func.to_date(
        models.VehicleVerification.raw_data['vehicle_manufacturing_month_year'].astext,
        'MM/YYYY'
    )

    return (
        query.distinct(mfg_date, models.VehicleListing.id)
        .order_by(mfg_date.desc(), models.VehicleListing.id.desc())
        .offset(skip).limit(limit)
        .all()
    )
