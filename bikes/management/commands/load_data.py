# Based on Week 6 lab (populate_cities.py and populate_regions.py)
import json
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bikes.models import CycleLane, Park, Station

DATA_DIR = Path(settings.BASE_DIR) / 'data'


def read_features(name):
    path = DATA_DIR / name
    if not path.exists():
        raise CommandError(f'data/{name} not found. Run: python scripts/fetch_data.py')
    return json.loads(path.read_text())['features']


def to_geometry(feature):
    return GEOSGeometry(json.dumps(feature['geometry']), srid=4326)


class Command(BaseCommand):
    help = 'Load stations, cycle lanes and parks from the GeoJSON files in data/'

    @transaction.atomic
    def handle(self, *args, **options):
        self.load_stations()
        self.load_lanes()
        self.load_parks()

    def load_stations(self):
        # update_or_create keeps station rows, so saved favourites are not deleted
        created = updated = 0
        for feature in read_features('stations.geojson'):
            props = feature['properties']
            _, was_created = Station.objects.update_or_create(
                station_id=props['station_id'],
                defaults={
                    'name': props['name'],
                    'address': props.get('address', ''),
                    'bike_stands': props['bike_stands'],
                    'available_bikes': props['available_bikes'],
                    'location': to_geometry(feature),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Stations: {created} created, {updated} updated'))

    def load_lanes(self):
        CycleLane.objects.all().delete()
        lanes = [
            CycleLane(
                name=f['properties']['name'][:100],
                lane_type=f['properties'].get('lane_type', ''),
                path=to_geometry(f),
            )
            for f in read_features('cycle_lanes.geojson')
            if f['geometry']['type'] == 'LineString'
        ]
        CycleLane.objects.bulk_create(lanes)
        self.stdout.write(self.style.SUCCESS(f'Cycle lanes: {len(lanes)} loaded'))

    def load_parks(self):
        Park.objects.all().delete()
        parks = []
        for f in read_features('parks.geojson'):
            area = to_geometry(f)
            if area.geom_type == 'Polygon':
                area = MultiPolygon(area, srid=4326)
            if area.geom_type != 'MultiPolygon' or not area.valid:
                continue
            parks.append(Park(name=f['properties']['name'][:100], area=area))
        Park.objects.bulk_create(parks)
        self.stdout.write(self.style.SUCCESS(f'Parks: {len(parks)} loaded'))
