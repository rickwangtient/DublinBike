# Based on Week 6 lab (api/serializers.py). GeoJSON serializers.
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from bikes.models import CycleLane, FavouriteStation, Park, Station


class StationSerializer(GeoFeatureModelSerializer):
    distance_m = serializers.SerializerMethodField()

    class Meta:
        model = Station
        geo_field = 'location'
        fields = [
            'id', 'station_id', 'name', 'address',
            'bike_stands', 'available_bikes', 'distance_m',
        ]

    def get_distance_m(self, obj):
        distance = getattr(obj, 'distance', None)
        if distance is None:
            return None
        return round(distance.m)


class CycleLaneSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = CycleLane
        geo_field = 'path'
        fields = ['id', 'name', 'lane_type']


class ParkSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Park
        geo_field = 'area'
        fields = ['id', 'name']


class FavouriteStationSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)

    class Meta:
        model = FavouriteStation
        fields = ['id', 'station', 'station_name', 'nickname', 'notes', 'created_at']
