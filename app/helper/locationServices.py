def extract_location_components(response):
    typesToCheck = [
        "locality", "sublocality", "administrative_area_level_7", "administrative_area_level_6",
        "administrative_area_level_5", "administrative_area_level_4", "administrative_area_level_3",
        "administrative_area_level_2"
    ]
    addr_comp = response['results'][0]['address_components']

    addr = {"mainText": "", "State": "", "Country": ""}

    for type in typesToCheck:
        for x in addr_comp:
            if type in x['types']:
                addr["mainText"] = x['long_name']
                break
        if addr["mainText"]:
            break
    
    # for x in addr_comp:
    #     if "administrative_area_level_3" in x['types']:
    #         addr["District"] = x['long_name']

    # Extract State (administrative_area_level_1)
    for x in addr_comp:
        if "administrative_area_level_1" in x['types']:
            addr["State"] = x['long_name']
            break

    # Extract Country
    for x in addr_comp:
        if "country" in x['types']:
            addr["Country"] = x['long_name']
            break

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
