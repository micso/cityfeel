from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import EmotionPoint, Comment, Photo


def check_owner_or_staff(user, obj_user):
    """Pomocnicza funkcja sprawdzająca uprawnienia (właściciel lub admin)."""
    return user == obj_user or user.is_staff


@login_required
@require_POST
def delete_emotion(request, pk):
    emotion = get_object_or_404(EmotionPoint, pk=pk)

    if not check_owner_or_staff(request.user, emotion.user):
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tej oceny.")

    location_id = emotion.location.id
    emotion.delete()
    messages.success(request, "Ocena została usunięta.")
    return redirect('map:location_detail', pk=location_id)


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)

    if not check_owner_or_staff(request.user, comment.user):
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tego komentarza.")

    location_id = comment.location.id
    comment.delete()
    messages.success(request, "Komentarz został usunięty.")
    return redirect('map:location_detail', pk=location_id)


@login_required
@require_POST
def delete_photo(request, pk):
    photo = get_object_or_404(Photo, pk=pk)

    if not check_owner_or_staff(request.user, photo.user):
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tego zdjęcia.")

    location_id = photo.location.id
    photo.delete()
    messages.success(request, "Zdjęcie zostało usunięte.")
    return redirect('map:location_detail', pk=location_id)


@login_required
@require_POST
def edit_photo_caption(request, pk):
    """
    [NOWE] Pozwala edytować opis zdjęcia.
    """
    photo = get_object_or_404(Photo, pk=pk)

    if not check_owner_or_staff(request.user, photo.user):
        return HttpResponseForbidden("Nie masz uprawnień do edycji tego zdjęcia.")

    new_caption = request.POST.get('caption', '').strip()

    # Aktualizujemy opis (nawet jeśli pusty - użytkownik może chcieć usunąć opis)
    photo.caption = new_caption
    photo.save()

    messages.success(request, "Opis zdjęcia został zaktualizowany.")
    return redirect('map:location_detail', pk=photo.location.id)