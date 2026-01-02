from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Avg, Count
from .models import Location

def location_detail(request, id):
    # Get location or 404
    location = get_object_or_404(Location, id=id)

    # Calculate stats
    stats = location.emotion_points.aggregate(
        average_rating=Avg('emotional_value'),
        total_opinions=Count('id')
    )

    # Prepare data
    data = {
        'id': location.id,
        'name': location.name,
        'coordinates': {
            'lat': location.coordinates.y,
            'lon': location.coordinates.x
        },
        'average_rating': stats['average_rating'] if stats['average_rating'] else 0,
        'total_opinions': stats['total_opinions']
    }

    return JsonResponse(data)