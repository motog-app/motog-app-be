# app/crud.py
import re
from time import sleep
from sqlalchemy.orm import Session
from . import models, schemas
from .core.security import get_password_hash
from typing import Optional, List
from sqlalchemy import func, or_
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
    listing: schemas.VehicleListingCreate,
    user_id: int,
):
    # Start of geocoding logic
    input_city = listing.city
    resolved_locations = {input_city.lower()}
    latitude, longitude = None, None

    try:
        geocode_result = gmaps.geocode(input_city)
        if geocode_result:
            # Get Coordinates
            location = geocode_result[0]['geometry']['location']
            latitude = location['lat']
            longitude = location['lng']

            # Extract all relevant location names
            for component in geocode_result[0]['address_components']:
                # e.g., Saket, South Delhi, Delhi, New Delhi, NCT of Delhi, etc.
                component_types = component.get('types', [])
                if any(t in component_types for t in ['sublocality', 'locality', 'administrative_area_level_2', 'administrative_area_level_1']):
                    resolved_locations.add(component['long_name'].lower())
                    resolved_locations.add(component['short_name'].lower())

            # Special handling for Delhi
            # can be added for other major cities as well
            if "delhi" in resolved_locations:
                resolved_locations.add("new delhi")
    except Exception as e:
        print(f"Google Maps API error during listing creation: {e}")
        # If API fails, we still proceed with the user's original input

    # Create the pipe-delimited string for storage
    # e.g., "delhi|new delhi|saket|south delhi"
    location_string = "|".join(sorted(list(resolved_locations)))
    # --- End of Geocoding Logic ---

    db_listing = models.VehicleListing(
        # This unpacks all fields from the schema, including primary_image_url
        **listing.model_dump(exclude={"city"}),
        user_id=user_id,
        city=location_string,
        usr_inp_city=listing.city,
        latitude=latitude,
        longitude=longitude
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
    query = db.query(models.VehicleListing).filter(
        models.VehicleListing.is_active == True)

    if city:
        search_term = f"%{city.lower()}%"
        query = query.filter(models.VehicleListing.city.ilike(search_term))

    if vehicle_type:
        query = query.filter(
            models.VehicleListing.vehicle_type == vehicle_type)

    if min_price is not None:
        query = query.filter(models.VehicleListing.price >= min_price)

    if max_price is not None:
        query = query.filter(models.VehicleListing.price <= max_price)

    if min_year is not None:
        query = query.filter(models.VehicleListing.year >= min_year)

    if max_year is not None:
        query = query.filter(models.VehicleListing.year <= max_year)

    if min_km_driven is not None:
        query = query.filter(
            models.VehicleListing.kilometers_driven >= min_km_driven)

    if max_km_driven is not None:
        query = query.filter(
            models.VehicleListing.kilometers_driven <= max_km_driven)

    if owner_id is not None:
        query = query.filter(
            models.VehicleListing.user_id == owner_id
        )

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


def update_vehicle_listing(
    db: Session,
    listing_id: int,
    listing_in: schemas.VehicleListingUpdate,
    user_id: int
) -> Optional[models.VehicleListing]:
    db_listing = db.query(models.VehicleListing).filter(
        models.VehicleListing.id == listing_id,
        models.VehicleListing.user_id == user_id
    ).first()

    if not db_listing:
        return None

    update_data = listing_in.model_dump(exclude_unset=True)

    # Optional: Handle geocoding if city is updated
    if "city" in update_data:
        # updating the usr_inp_city along with the city
        update_data["usr_inp_city"] = update_data["city"]
        input_city = update_data["city"]
        resolved_locations = {input_city.lower()}
        latitude, longitude = None, None

        try:
            geocode_result = gmaps.geocode(input_city)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                latitude = location['lat']
                longitude = location['lng']

                for component in geocode_result[0]['address_components']:
                    component_types = component.get('types', [])
                    if any(t in component_types for t in ['sublocality', 'locality', 'administrative_area_level_2', 'administrative_area_level_1']):
                        resolved_locations.add(component['long_name'].lower())
                        resolved_locations.add(component['short_name'].lower())

                if "delhi" in resolved_locations:
                    resolved_locations.add("new delhi")

            update_data["city"] = "|".join(sorted(list(resolved_locations)))
            update_data["latitude"] = latitude
            update_data["longitude"] = longitude
        except Exception as e:
            print(f"Google Maps API error during update: {e}")
            # Fallback to user input city (already in `update_data`)

    for key, value in update_data.items():
        setattr(db_listing, key, value)

    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing


def get_verification_by_reg_no(db: Session, reg_no: str):
    return db.query(models.VehicleVerification).filter(models.VehicleVerification.reg_no == reg_no).first()


def create_verification(db: Session, reg_no: str, status: str, raw_data: dict):
    verification = models.VehicleVerification(
        reg_no=reg_no,
        status=status,
        raw_data=raw_data
    )

    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def add_listing_images(
        db: Session,
        listing_id: int,
        images_data: List[dict]
) -> List[models.ListingImage]:
    images = []
    for data in images_data:
        img = models.ListingImage(
            listing_id=listing_id,
            url=data["url"],
            is_primary=data.get("is_primary", False)
        )
        db.add(img)
        images.append(img)
    db.commit()
    return images


def get_images_for_listing(db: Session, listing_id: int) -> List[models.ListingImage]:
    return db.query(models.ListingImage).filter_by(listing_id=listing_id).all()


def get_listing_image(db: Session, image_id: int) -> Optional[models.ListingImage]:
    return db.query(models.ListingImage).filter_by(id=image_id).first()


def delete_listing_image(db: Session, image_id: int) -> bool:
    image = db.query(models.ListingImage).filter_by(id=image_id).first()
    if image:
        db.delete(image)
        db.commit()
        return True
    return False


def update_listing_image_url(db: Session, image_id: int, new_url: str) -> Optional[models.ListingImage]:
    image = db.query(models.ListingImage).filter_by(id=image_id).first()
    if image:
        image.url = new_url
        db.commit()
        db.refresh(image)
        return image
    return None


def get_homepage_listings(db: Session, city_input: str, limit: int = 10):
    city_input = city_input.lower().strip()

    query = db.query(models.VehicleListing).filter(
        models.VehicleListing.is_active == True,
        models.VehicleListing.city.ilike(f"%{city_input}%"),
        db.query(models.ListingImage.id)
        .filter(models.ListingImage.listing_id == models.VehicleListing.id)
        .exists()
    ).order_by(models.VehicleListing.created_at.desc()).limit(limit)

    return query.all()


def search_vehicle_listings(db: Session, q: str, skip: int = 0, limit: int = 10) -> List[models.VehicleListing]:
    """
    Search active vehicle listings based on a keyword query. The query supports
    searching by vehicle manufacturer name and model from the verification raw data.

    Args:
        db (Session): SQLAlchemy DB session.
        q (str): Search query, e.g., "Hyundai Creta 2021".
        skip (int): Number of records to skip (pagination).
        limit (int): Maximum number of records to return (pagination).

    Returns:
        List[VehicleListing]: List of matching vehicle listings ordered by manufacturing date.
    """

    # Remove non-alphanumeric characters (except space), make lowercase
    q = re.sub(r"[^a-zA-Z0-9\s]", "", q).lower().strip()
    keywords = q.split()

    # Base query: only active listings with join to verification table
    query = (
        db.query(models.VehicleListing)
        .join(models.VehicleVerification, models.VehicleListing.reg_no == models.VehicleVerification.reg_no)
        .filter(models.VehicleListing.is_active == True)
    )

    # Add search conditions using ilike for manufacturer name and model
    if keywords:
        conditions = []
        for word in keywords:
            ilike_pattern = f"%{word}%"
            conditions.append(func.lower(
                models.VehicleVerification.raw_data['vehicle_manufacturer_name'].astext).ilike(ilike_pattern))
            conditions.append(func.lower(
                models.VehicleVerification.raw_data['model'].astext).ilike(ilike_pattern))

        query = query.filter(or_(*conditions))

    # Extract and reuse manufacturing date
    manufacture_date = func.to_date(
        models.VehicleVerification.raw_data['vehicle_manufacturing_month_year'].astext,
        'MM/YYYY'
    )

    # Ensure distinct listings and order by manufacturing date descending
    query = (
        query
        .distinct(manufacture_date, models.VehicleListing.id)
        .order_by(
            manufacture_date.desc(),
            models.VehicleListing.id.desc()
        )
        .offset(skip)
        .limit(limit)
    )

    return query.all()
