# Based on Week 6 lab (api/urls.py)
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CycleLaneViewSet, FavouriteStationViewSet, ParkViewSet, StationViewSet

router = DefaultRouter()
router.register(r'stations', StationViewSet)
router.register(r'lanes', CycleLaneViewSet)
router.register(r'parks', ParkViewSet)
router.register(r'favourites', FavouriteStationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
