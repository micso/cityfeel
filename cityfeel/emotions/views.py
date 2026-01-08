from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from .models import EmotionPoint, Comment
from .forms import CommentForm


@login_required
@require_POST
def delete_emotion(request, pk):
    """
    Usuwanie oceny (EmotionPoint).
    Dozwolone dla: Administratora (is_staff) LUB właściciela oceny.
    """
    emotion = get_object_or_404(EmotionPoint, pk=pk)

    # POPRAWKA: Sprawdzamy czy to admin LUB właściciel
    if not request.user.is_staff and emotion.user != request.user:
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tej oceny.")

    location_id = emotion.location.id
    emotion.delete()

    messages.success(request, "Ocena została usunięta.")
    return redirect('map:location_detail', pk=location_id)


@login_required
@require_POST
def add_comment(request, emotion_id):
    """
    Widok AJAX do dodawania komentarza.
    """
    emotion = get_object_or_404(EmotionPoint, pk=emotion_id)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.emotion_point = emotion
        comment.save()

        return JsonResponse({
            'success': True,
            'comment': {
                'username': comment.user.username,
                'created_at': comment.created_at.strftime('%d.%m.%Y'),
                'content': comment.content,
                'id': comment.id
            }
        })

    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_comment(request, comment_id):
    """
    Usuwanie komentarza.
    Dozwolone dla: Administratora (is_staff) LUB autora komentarza.
    """
    comment = get_object_or_404(Comment, pk=comment_id)

    # Sprawdzenie uprawnień: Admin LUB Autor
    if not request.user.is_staff and comment.user != request.user:
        return HttpResponseForbidden("Nie masz uprawnień do usunięcia tego komentarza.")

    location_id = comment.emotion_point.location.id

    comment.delete()
    messages.success(request, "Komentarz został usunięty.")

    return redirect('map:location_detail', pk=location_id)