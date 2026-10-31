# Based on Week 6 lab (api/views.py). nearby is the Week 6 proximity search.
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bikes.models import CycleLane, FavouriteStation, Park, Station
from .serializers import (
    CycleLaneSerializer,
    FavouriteStationSerializer,
    ParkSerializer,
    StationSerializer,
)


def parse_park(request):
    park_id = request.query_params.get('park_id')
    if not park_id:
        return None, Response(
            {'error': 'park_id is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return get_object_or_404(Park, pk=park_id), None


class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    pagination_class = None  # From Week 6 lab: return one GeoJSON FeatureCollection

    def get_queryset(self):
        queryset = Station.objects.all()
        min_bikes = self.request.query_params.get('min_bikes')
        if min_bikes:
            queryset = queryset.filter(available_bikes__gte=min_bikes)
        return queryset

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Stations within distance km of a point. Default 1 km."""
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if not lat or not lng:
            return Response(
                {'error': 'lat and lng parameters are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            point = Point(float(lng), float(lat), srid=4326)
            distance_km = float(request.query_params.get('distance', 1))
            stations = self.get_queryset().filter(
                location__distance_lte=(point, D(km=distance_km))
            ).annotate(
                distance=Distance('location', point)
            ).order_by('distance')
            return Response(self.get_serializer(stations, many=True).data)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid coordinates or distance'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'])
    def in_park(self, request):
        """Stations whose point is inside a park polygon (containment)."""
        park, error = parse_park(request)
        if error:
            return error
        stations = self.get_queryset().filter(location__within=park.area)
        return Response(self.get_serializer(stations, many=True).data)

    @action(detail=False, methods=['get'])
    def near_park(self, request):
        """Stations within distance metres of a park edge. Default 200 m.

        Dublin Bikes stations sit on streets, not inside parks, so this
        is the useful park query. in_park still shows containment.
        """
        park, error = parse_park(request)
        if error:
            return error
        try:
            distance_m = float(request.query_params.get('distance', 200))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid distance'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stations = self.get_queryset().filter(
            location__distance_lte=(park.area, D(m=distance_m))
        ).annotate(
            distance=Distance('location', park.area)
        ).order_by('distance')
        return Response(self.get_serializer(stations, many=True).data)


class CycleLaneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CycleLane.objects.all()
    serializer_class = CycleLaneSerializer
    pagination_class = None

    @action(detail=False, methods=['get'])
    def through_park(self, request):
        """Lane segments that cross a park polygon (intersection)."""
        park, error = parse_park(request)
        if error:
            return error
        lanes = CycleLane.objects.filter(path__intersects=park.area)
        return Response(self.get_serializer(lanes, many=True).data)


class ParkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Park.objects.all()
    serializer_class = ParkSerializer
    pagination_class = None


class FavouriteStationViewSet(viewsets.ModelViewSet):
    queryset = FavouriteStation.objects.select_related('station')
    serializer_class = FavouriteStationSerializer
