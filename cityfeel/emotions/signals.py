from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Comment
from . import sentiment as sentiment_service


@receiver(post_save, sender=Comment)
def analyze_comment_sentiment(sender, instance, created, **kwargs):
    if not created or not instance.content:
        return

    result = sentiment_service.analyze(instance.content)
    if result["score"] is not None:
        Comment.objects.filter(pk=instance.pk).update(
            sentiment_score=result["score"],
            sentiment_label=result["label"],
        )
