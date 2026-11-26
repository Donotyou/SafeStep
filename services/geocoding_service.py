import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def geocode(query, limit=1):
    params = {
        'q': query,
        'format': 'json',
        'limit': limit
    }
    headers = {'User-Agent': 'SafeStep/1.0'}
    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data:
        results.append({
            'lat': float(item['lat']),
            'lon': float(item['lon']),
            'display_name': item.get('display_name')
        })
    return results
