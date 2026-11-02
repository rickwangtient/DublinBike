# Checks the Dublin Bike API. Run inside the web container:
#   docker compose exec web python tests/test_api_endpoints.py
import sys

import requests

BASE = 'http://localhost:8000'
session = requests.Session()
failed = False


def check(name, ok, detail=''):
    global failed
    print(('ok  ' if ok else 'FAIL') + '  ' + name + (('  ' + detail) if detail else ''))
    if not ok:
        failed = True


def get_json(path):
    response = session.get(BASE + path, timeout=20)
    return response.status_code, response.json()


def features(path):
    status, data = get_json(path)
    count = len(data.get('features', [])) if isinstance(data, dict) else 0
    return status, data, count


def main():
    try:
        home = session.get(BASE + '/', timeout=5)
        check('map page', home.status_code == 200, f'HTTP {home.status_code}')
    except requests.RequestException as error:
        check('map page', False, str(error))
        return 1

    status, data, count = features('/api/stations/')
    check('stations GeoJSON', status == 200 and data.get('type') == 'FeatureCollection' and count == 115, f'{count} features')
    if count:
        props = data['features'][0]['properties']
        check('station fields', {'name', 'available_bikes', 'bike_stands'} <= set(props))

    status, data, count = features('/api/lanes/')
    check('lanes GeoJSON', status == 200 and data.get('type') == 'FeatureCollection' and count > 1000, f'{count} features')

    status, data, count = features('/api/parks/')
    check('parks GeoJSON', status == 200 and data.get('type') == 'FeatureCollection' and count == 60, f'{count} features')
    parks = {feature['properties']['name']: feature['id'] for feature in data.get('features', [])}

    status, body = get_json('/api/stations/nearby/')
    check('nearby needs coordinates', status == 400 and 'lat' in body.get('error', ''))

    status, data, count = features('/api/stations/nearby/?lat=53.3547&lng=-6.2795&distance=0.8')
    distances = [feature['properties'].get('distance_m') for feature in data.get('features', [])]
    check('nearby Grangegorman', status == 200 and count > 0 and distances[0] == min(distances), f'{count} stations, closest {distances[0] if distances else "n/a"} m')

    green = parks.get("St Stephen's Green")
    phoenix = parks.get('Phoenix Park')
    check('park names found', green is not None and phoenix is not None)

    if green:
        status, data, count = features(f'/api/stations/in_park/?park_id={green}')
        check('stations inside a park', status == 200 and data.get('type') == 'FeatureCollection', f'{count} stations')
        status, data, count = features(f'/api/stations/near_park/?park_id={green}&distance=200')
        check('stations near a park', status == 200 and count > 0, f'{count} stations')

    if phoenix:
        status, data, count = features(f'/api/lanes/through_park/?park_id={phoenix}')
        check('lanes crossing a park', status == 200 and count > 0, f'{count} lanes')

    status, missing = get_json('/api/stations/near_park/')
    check('park search needs an id', status == 400)

    stations_status, stations = get_json('/api/stations/')
    station_id = stations['features'][0]['id']
    created = session.post(
        BASE + '/api/favourites/',
        json={'station': station_id, 'nickname': 'Test stop', 'notes': 'api check'},
        timeout=20,
    )
    check('create favourite', created.status_code == 201, f'HTTP {created.status_code}')
    if created.status_code == 201:
        favourite_id = created.json()['id']
        updated = session.put(
            f'{BASE}/api/favourites/{favourite_id}/',
            json={'station': station_id, 'nickname': 'Updated stop', 'notes': ''},
            timeout=20,
        )
        check('update favourite', updated.status_code == 200 and updated.json()['nickname'] == 'Updated stop')
        deleted = session.delete(f'{BASE}/api/favourites/{favourite_id}/', timeout=20)
        check('delete favourite', deleted.status_code == 204, f'HTTP {deleted.status_code}')

    print('FAILED' if failed else 'All checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
