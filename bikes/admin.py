from django.contrib.gis import admin

from .models import CycleLane, FavouriteStation, Park, Station


@admin.register(Station)
class StationAdmin(admin.GISModelAdmin):
    list_display = ['name', 'station_id', 'available_bikes', 'bike_stands']
    search_fields = ['name', 'address']


@admin.register(CycleLane)
class CycleLaneAdmin(admin.GISModelAdmin):
    list_display = ['name', 'lane_type']


@admin.register(Park)
class ParkAdmin(admin.GISModelAdmin):
    list_display = ['name']


@admin.register(FavouriteStation)
class FavouriteStationAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'station', 'created_at']
