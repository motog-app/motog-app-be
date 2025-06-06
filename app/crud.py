# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from .core.security import get_password_hash
from typing import Optional, List
from sqlalchemy import or_
import googlemaps
from app.core.config import settings
import redis
import json

gmaps = googlemaps.Client(key=settings.MAPS_API_KEY)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
GEOCODE_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# --- User CRUD (No changes) ---
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


# --- Vehicle Listing CRUD Operations (Updated `create_vehicle_listing`) ---
def create_vehicle_listing(
    db: Session,
    listing: schemas.VehicleListingCreate, # This object now contains primary_image_url
    user_id: int,
    # REMOVED: primary_image_url: Optional[str] = None <-- Remove this line
):
    db_listing = models.VehicleListing(
        **listing.model_dump(), # This unpacks all fields from the schema, including primary_image_url
        user_id=user_id,
        # REMOVED: primary_image_url=primary_image_url <-- Remove this line
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
    max_km_driven: Optional[int] = None
):
    query = db.query(models.VehicleListing).filter(models.VehicleListing.is_active == True)

    if city:
        cache_key = f"geocode:{city.lower()}"
        cached_data = redis_client.get(cache_key)
        resolved_cities = set()

        if cached_data:
            resolved_cities = set(json.loads(cached_data))
        else:
            try:
                geocode_result = gmaps.geocode(city)
                if geocode_result:
                    for component in geocode_result[0]['address_components']:
                        if 'locality' in component['types'] or 'administrative_area_level_2' in component['types'] or 'administrative_area_level_1' in component['types']:
                            resolved_cities.add(component['long_name'].lower())
                            resolved_cities.add(component['short_name'].lower())

                    resolved_cities.add(city.lower())

                    if "delhi" in resolved_cities:
                        resolved_cities.add("new delhi")

                    redis_client.setex(cache_key, GEOCODE_CACHE_TTL_SECONDS, json.dumps(list(resolved_cities)))
                else:
                    resolved_cities.add(city.lower())
            except Exception as e:
                print(f"Google Maps API error: {e}")
                resolved_cities.add(city.lower())

        if not resolved_cities:
            resolved_cities.add(city.lower())

        city_conditions = [models.VehicleListing.city.ilike(f"%{c}%") for c in resolved_cities]
        query = query.filter(or_(*city_conditions))


    if vehicle_type:
        query = query.filter(models.VehicleListing.vehicle_type == vehicle_type)

    if min_price is not None:
        query = query.filter(models.VehicleListing.price >= min_price)
    if max_price is not None:
        query = query.filter(models.VehicleListing.price <= max_price)
    if min_year is not None:
        query = query.filter(models.VehicleListing.year >= min_year)
    if max_year is not None:
        query = query.filter(models.VehicleListing.year <= max_year)
    if min_km_driven is not None:
        query = query.filter(models.VehicleListing.kilometers_driven >= min_km_driven)
    if max_km_driven is not None:
        query = query.filter(models.VehicleListing.kilometers_driven <= max_km_driven)


    return query.order_by(models.VehicleListing.created_at.desc()).offset(skip).limit(limit).all()


def get_listing_by_id(db: Session, listing_id: int):
    return db.query(models.VehicleListing).filter(models.VehicleListing.id == listing_id, models.VehicleListing.is_active == True).first()

def delete_listing(db: Session, listing_id: int, user_id: int) -> Optional[models.VehicleListing]:
    """
    Soft deletes a listing by setting is_active to False.
    Only the owner can delete their listing.
    """
    db_listing = db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.user_id == user_id
    ).first()

    if db_listing:
        db_listing.is_active = False
        db.add(db_listing)
        db.commit()
        db.refresh(db_listing)
        return db_listing
    return None