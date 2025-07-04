from fastapi import APIRouter, HTTPException, Depends
from app.dependencies import get_current_user
from app.core.config import settings
import requests
import json
from app import schemas
from app.helper.locationServices import extract_location_components, filter_relevant_suggestions
from app.core.redis import get_redis_client

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/get-location", response_model=schemas.LocationFrmLatLngResponse)
async def getLocation(request: schemas.LocationFrmLatLngRequest):
    lat = request.lat
    lng = request.lng

    REVERSE_GEOCODE_CACHE_TTL_SECONDS = 24 * 60 * 60

    cache_key = f"reverse_geocode:{lat},{lng}"
    redis_client = await get_redis_client()
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        return schemas.LocationFrmLatLngResponse(**json.loads(cached_data))

    MAPS_API_KEY = settings.MAPS_API_KEY

    url = "https://maps.googleapis.com/maps/api/geocode/json"

    payload = {
        "latlng": f"{lat},{lng}",
        "result_type": "sublocality|locality|administrative_area_level_7|administrative_area_level_6|administrative_area_level_5|administrative_area_level_4|administrative_area_level_3|administrative_area_level_2|administrative_area_level_1|country",
        "key": MAPS_API_KEY
    }

    response = requests.get(url=url, params=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code,
                            detail=f"Google Maps API error: {response.text}")

    data = response.json()

    if data.get("status") != "OK":
        raise HTTPException(
            status_code=400, detail=f"Geocoding Failed: {data.get('status')} - {data.get('error_message', 'No Additional info')}")

    extracted_data = extract_location_components(data)
    await redis_client.setex(cache_key, REVERSE_GEOCODE_CACHE_TTL_SECONDS, json.dumps(extracted_data))
    return extracted_data


@router.post("/loc-autocomplete", response_model=schemas.LocAutoCompleteResponse)
def locAutoComplete(request: schemas.LocAutoCompleteRequest):
    try:
        payload = {
            "input": request.addrStr
        }

        if request.sessionToken:
            payload["sessionToken"] = request.sessionToken

        if request.latLng:
            try:
                lat, lng = map(float, request.latLng.split(","))
                payload["locationBias"] = {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lng
                        },
                        "radius": 360.0
                    }
                }
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid latlng format. Use 'lat,lng'.")
        else:
            # Restrict suggestions to India when latLng not provided
            payload["locationRestriction"] = {
                "rectangle": {
                    # Approx SW corner of India
                    "low": {"latitude": 6.5546079, "longitude": 68.1113787},
                    # Approx NE corner of India
                    "high": {"latitude": 35.6745457, "longitude": 97.395561}
                }
            }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.MAPS_API_KEY
        }

        response = requests.post(
            "https://places.googleapis.com/v1/places:autocomplete",
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Google API Error: {response.text}"
            )
        data = response.json()
        return {"suggestions": filter_relevant_suggestions(data.get('suggestions', []))}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
