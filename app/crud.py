# backend/app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from .core.security import get_password_hash
from typing import Optional, List
from sqlalchemy import or_
import googlemaps
from app.core.config import settings # Import settings
import redis # Import redis
import json # For serializing/deserializing data to/from Redis

# Initialize Google Maps client (outside the function for efficiency)
gmaps = googlemaps.Client(key=settings.Maps_API_KEY)

# Initialize Redis client (outside the function)
# decode_responses=True ensures that data retrieved from Redis are Python strings, not bytes
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Cache expiry time for geocoding results (e.g., 7 days in seconds)
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

# --- VehicleListing CRUD ---
def create_vehicle_listing(db: Session, listing: schemas.VehicleListingCreate, user_id: int):
    db_listing = models.VehicleListing(**listing.model_dump(), user_id=user_id) # Pydantic V2
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    return db_listing

def get_listings(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    q: Optional[str] = None,
    city: Optional[str] = None,
    vehicle_type: Optional[models.VehicleTypeEnum] = None
) -> List[models.VehicleListing]:
    query = db.query(models.VehicleListing).filter(models.VehicleListing.is_active == True)

    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            (models.VehicleListing.make.ilike(search_term)) |
            (models.VehicleListing.model.ilike(search_term)) |
            (models.VehicleListing.city.ilike(search_term))
        )

    if city:
        resolved_cities = set()
        resolved_cities.add(city.lower()) # Always include the original search term

        cache_key = f"geocode:{city.lower()}"
        cached_result_json = None

        try:
            # Attempt to retrieve from Redis cache
            cached_result_json = redis_client.get(cache_key)
        except redis.exceptions.ConnectionError as e:
            print(f"Redis connection error: {e}. Proceeding without cache for '{city}'.")
            # If Redis is down, we still want the application to work, so proceed without cache
            cached_result_json = None

        geocode_result = None
        if cached_result_json:
            try:
                # Deserialize the JSON string back into a Python object
                geocode_result = json.loads(cached_result_json)
                print(f"Using cached geocoding result for '{city}'")
            except json.JSONDecodeError as e:
                print(f"Error decoding cached JSON for '{city}': {e}. Fetching new result.")
                # If cache is corrupted, treat it as a cache miss
                geocode_result = None
            except TypeError as e: # Handle cases where cached_result_json might not be a string
                print(f"Type error with cached data for '{city}': {e}. Fetching new result.")
                geocode_result = None

        if not geocode_result: # If not in cache or cache lookup failed
            try:
                print(f"Fetching new geocoding result for '{city}' from Google Maps API...")
                # Perform geocoding
                geocode_result = gmaps.geocode(city, components={"country": "IN"})
                
                if geocode_result:
                    try:
                        # Cache the API response (serialize to JSON string)
                        redis_client.setex(cache_key, GEOCODE_CACHE_TTL_SECONDS, json.dumps(geocode_result))
                        print(f"Cached geocoding result for '{city}' with TTL {GEOCODE_CACHE_TTL_SECONDS}s.")
                    except redis.exceptions.ConnectionError as e:
                        print(f"Redis connection error during set: {e}. Data for '{city}' not cached.")
                    except Exception as e:
                        print(f"Error caching geocoding result for '{city}': {e}")
                else:
                    print(f"Google Maps API returned no results for '{city}'.")

            except Exception as e:
                # Log the error, but don't stop the search. Fallback to original input.
                print(f"Error calling Google Maps Geocoding API for city '{city}': {e}. Fallback to original input.")
                geocode_result = None # Ensure it's None if API call failed

        if geocode_result:
            for result in geocode_result:
                for component in result.get('address_components', []):
                    types = component.get('types', [])
                    long_name = component.get('long_name', '').lower()
                    
                    if 'locality' in types or 'administrative_area_level_2' in types or 'administrative_area_level_1' in types or 'sublocality' in types:
                        if long_name:
                            resolved_cities.add(long_name)
                    # Attempt to extract broader city if a sublocality was queried
                    if 'sublocality' in types and 'locality' in types and result.get('formatted_address'):
                        parts = result['formatted_address'].split(',')
                        # Look for the part that's likely the main city before country/state
                        if len(parts) >= 2:
                            # Heuristic: often the second to last part is the main city (e.g., Saket, New Delhi, Delhi, India)
                            potential_city = parts[-2].strip().lower()
                            # Only add if it looks like a city name (not just a single letter or number)
                            if len(potential_city) > 1 and not potential_city.isdigit():
                                resolved_cities.add(potential_city)
            
            # Explicitly add "new delhi" if "delhi" is found to ensure coverage
            if "delhi" in resolved_cities:
                resolved_cities.add("new delhi")
        
        # Ensure at least the original city is in the search if no API result or error
        if not resolved_cities:
            resolved_cities.add(city.lower())


        city_conditions = [models.VehicleListing.city.ilike(f"%{c}%") for c in resolved_cities]
        query = query.filter(or_(*city_conditions))


    if vehicle_type:
        query = query.filter(models.VehicleListing.vehicle_type == vehicle_type)

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