# Based on Week 6 lab models (cities/models.py and regions/models.py)
from django.contrib.gis.db import models


class Station(models.Model):
    """A Dublin Bikes station (point)."""

    station_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    bike_stands = models.PositiveIntegerField()
    available_bikes = models.PositiveIntegerField(default=0)
    location = models.PointField(srid=4326)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CycleLane(models.Model):
    """A cycle lane or cycleway (line)."""

    name = models.CharField(max_length=100)
    lane_type = models.CharField(max_length=50, blank=True)
    path = models.LineStringField(srid=4326)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Park(models.Model):
    """A park or green space (polygon)."""

    name = models.CharField(max_length=100)
    area = models.MultiPolygonField(srid=4326)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FavouriteStation(models.Model):
    """A station a user has saved. Used for create, update and delete."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='favourites')
    nickname = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nickname} ({self.station.name})"
