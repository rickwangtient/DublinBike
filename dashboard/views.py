# Based on Week 6 lab (dashboard/views.py)
from django.shortcuts import render

from bikes.models import CycleLane, Park, Station


def index(request):
    """Main map page"""
    context = {
        'total_stations': Station.objects.count(),
        'total_lanes': CycleLane.objects.count(),
        'total_parks': Park.objects.count(),
    }
    return render(request, 'dashboard/index.html', context)


def analytics(request):
    """Week 6 analytics page. Not built for Dublin Bike yet."""
    return render(request, 'dashboard/analytics.html', {})
