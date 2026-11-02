"""Download Dublin Bike data and save it as GeoJSON in data/.

Run inside the web container:
    docker compose exec web python scripts/fetch_data.py

Sources:
- Stations: Dublin Bikes GBFS feed (JCDecaux / Smart Dublin), CC BY 4.0
- Cycle lanes and parks: OpenStreetMap via the Overpass API, (c) OpenStreetMap contributors, ODbL
"""
import json
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping
from shapely.ops import linemerge, polygonize, unary_union

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

GBFS = 'https://api.cyclocity.fr/contracts/dublin/gbfs/v2'
OVERPASS_SERVERS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
]
HEADERS = {
    'User-Agent': 'DublinBikeStudentProject/1.0 (TU Dublin coursework)',
    'Accept': 'application/json',
}

# Dublin city centre, slightly larger than the area covered by the stations
BBOX = '(53.325,-6.315,53.365,-6.225)'


def save(name, features):
    path = DATA_DIR / name
    path.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}))
    print(f'  saved {len(features)} features to data/{name}')


def overpass(query):
    """Run an Overpass query, retrying on busy servers."""
    for attempt in range(4):
        for url in OVERPASS_SERVERS:
            try:
                response = requests.post(url, data={'data': query}, headers=HEADERS, timeout=120)
                if response.status_code == 200:
                    return response.json()['elements']
                print(f'  {url} returned {response.status_code}, trying next server')
            except requests.RequestException as error:
                print(f'  {url} failed ({error}), trying next server')
        wait = 10 * 2 ** attempt
        print(f'  all servers busy, waiting {wait}s')
        time.sleep(wait)
    raise RuntimeError('Overpass API is unavailable, try again later')


def fetch_stations():
    print('Stations (Dublin Bikes GBFS)')
    info = requests.get(f'{GBFS}/station_information.json', headers=HEADERS, timeout=30).json()
    status = requests.get(f'{GBFS}/station_status.json', headers=HEADERS, timeout=30).json()
    bikes = {s['station_id']: s.get('num_bikes_available', 0) for s in status['data']['stations']}

    features = []
    for s in info['data']['stations']:
        # A few stations have no name in the feed. Use the address instead.
        name = (s.get('name') or s.get('address') or f"Station {s['station_id']}").title()
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [s['lon'], s['lat']]},
            'properties': {
                'station_id': int(s['station_id']),
                'name': name,
                'address': s.get('address', ''),
                'bike_stands': s.get('capacity', 0),
                'available_bikes': bikes.get(s['station_id'], 0),
            },
        })
    save('stations.geojson', features)


def lane_type(tags):
    if tags.get('highway') == 'cycleway':
        return 'cycleway'
    for key in ('cycleway', 'cycleway:both', 'cycleway:left', 'cycleway:right'):
        if tags.get(key) in ('lane', 'track'):
            return tags[key]
    return 'other'


def fetch_lanes():
    print('Cycle lanes (OpenStreetMap)')
    query = f"""[out:json][timeout:90];
(
  way["highway"="cycleway"]{BBOX};
  way["cycleway"~"^(lane|track)$"]{BBOX};
  way["cycleway:both"~"^(lane|track)$"]{BBOX};
  way["cycleway:left"~"^(lane|track)$"]{BBOX};
  way["cycleway:right"~"^(lane|track)$"]{BBOX};
);
out geom;"""
    features = []
    for way in overpass(query):
        points = [(p['lon'], p['lat']) for p in way.get('geometry', [])]
        if len(points) < 2:
            continue
        tags = way.get('tags', {})
        features.append({
            'type': 'Feature',
            'geometry': mapping(LineString(points)),
            'properties': {
                'osm_id': way['id'],
                'name': tags.get('name', 'Unnamed cycleway'),
                'lane_type': lane_type(tags),
            },
        })
    save('cycle_lanes.geojson', features)


def relation_polygon(relation):
    """Join the outer ways of an OSM multipolygon into a shape."""
    lines = [
        LineString([(p['lon'], p['lat']) for p in m['geometry']])
        for m in relation.get('members', [])
        if m.get('role') == 'outer' and len(m.get('geometry', [])) >= 2
    ]
    polygons = list(polygonize(linemerge(lines))) if lines else []
    return unary_union(polygons) if polygons else None


def fetch_parks():
    print('Parks (OpenStreetMap)')
    query = f"""[out:json][timeout:90];
(
  way["leisure"="park"]["name"]{BBOX};
  relation["leisure"="park"]["name"]{BBOX};
);
out geom;"""
    features = []
    for element in overpass(query):
        if element['type'] == 'way':
            points = [(p['lon'], p['lat']) for p in element.get('geometry', [])]
            if len(points) < 4 or points[0] != points[-1]:
                continue
            shape = Polygon(points)
        else:
            shape = relation_polygon(element)
        if shape is None or shape.is_empty:
            continue
        if not shape.is_valid:
            shape = shape.buffer(0)
        if isinstance(shape, Polygon):
            shape = MultiPolygon([shape])
        if not isinstance(shape, MultiPolygon):
            continue
        features.append({
            'type': 'Feature',
            'geometry': mapping(shape),
            'properties': {'osm_id': element['id'], 'name': element['tags']['name']},
        })
    save('parks.geojson', features)


if __name__ == '__main__':
    DATA_DIR.mkdir(exist_ok=True)
    fetch_stations()
    fetch_lanes()
    fetch_parks()
