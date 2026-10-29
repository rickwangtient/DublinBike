# Based on Week 6 lab (api/views.py)
from rest_framework import viewsets

from bikes.models import CycleLane, FavouriteStation, Park, Station
from .serializers import (
    CycleLaneSerializer,
    FavouriteStationSerializer,
    ParkSerializer,
    StationSerializer,
)


class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    pagination_class = None  # From Week 6 lab: return one GeoJSON FeatureCollection


class CycleLaneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CycleLane.objects.all()
    serializer_class = CycleLaneSerializer
    pagination_class = None


class ParkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Park.objects.all()
    serializer_class = ParkSerializer
    pagination_class = None


class FavouriteStationViewSet(viewsets.ModelViewSet):
    queryset = FavouriteStation.objects.select_related('station')
    serializer_class = FavouriteStationSerializer
