import requests
from app.core.config import settings

def get_place_details(place_id: str):
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.MAPS_API_KEY,
        "X-Goog-FieldMask": "id,displayName,formattedAddress,addressComponents,location"
    }
    params = {
        "languageCode": "en" # Optional: Specify language
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status() # Will raise an exception for 4XX/5XX errors
    return response.json()

def extract_location_components(response, source_api):
    addr = {"mainText": "", "secondaryText": None, "state": "", "country": "", "lat": None, "lng": None, "placeId": None}

    if source_api == "places_details":
        addr_comp = response.get('addressComponents', [])
        addr['mainText'] = response.get('displayName', {}).get('text', '')
        addr['lat'] = response.get('location', {}).get('latitude')
        addr['lng'] = response.get('location', {}).get('longitude')
        addr['placeId'] = response.get('id')

        # For places, secondary text can be the full address
        addr['secondaryText'] = response.get('formattedAddress')

    elif source_api == "geocode":
        if not response.get('results'):
            return addr
        result = response['results'][0]
        addr_comp = result.get('address_components', [])
        addr['lat'] = result.get('geometry', {}).get('location', {}).get('lat')
        addr['lng'] = result.get('geometry', {}).get('location', {}).get('lng')
        addr['placeId'] = result.get('place_id')

        # Geocode specific logic to find main text
        types_to_check = [
            "locality", "sublocality", "administrative_area_level_7", "administrative_area_level_6",
            "administrative_area_level_5", "administrative_area_level_4", "administrative_area_level_3",
            "administrative_area_level_2"
        ]
        for component_type in types_to_check:
            for component in addr_comp:
                if component_type in component.get('types', []):
                    addr['mainText'] = component.get('long_name', '')
                    break
            if addr['mainText']:
                break

    # Common logic for state and country
    for component in addr_comp:
        if "administrative_area_level_1" in component.get('types', []):
            addr['state'] = component.get('long_name', '')
        if "country" in component.get('types', []):
            addr['country'] = component.get('long_name', '')

    return addr


def filter_relevant_suggestions(suggestions):
    relevant_types = {"sublocality", "locality"}

    filtered = []
    for s in suggestions:
        types = s["placePrediction"].get("types", [])
        if any(t in relevant_types for t in types):
            filtered.append({
                "placeId": s["placePrediction"]["placeId"],
                "mainText": s["placePrediction"]["structuredFormat"]["mainText"]["text"],
                "secondaryText": s["placePrediction"]["structuredFormat"]["secondaryText"]["text"]
            })
    return filtered
