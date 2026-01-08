from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import EmotionPoint


@login_required
@require_POST
def delete_emotion(request, pk):
    emotion = get_object_or_404(EmotionPoint, pk=pk)

    if emotion.user != request.user:
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tej oceny.")

    # Zapamiętujemy ID lokalizacji, żeby wiedzieć gdzie wrócić
    location_id = emotion.location.id

    emotion.delete()

    messages.success(request, "Twoja ocena została usunięta.")

    return redirect('map:location_detail', pk=location_id)