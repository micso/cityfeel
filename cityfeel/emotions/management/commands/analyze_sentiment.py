from django.core.management.base import BaseCommand

from emotions.models import Comment
from emotions import sentiment as sentiment_service


class Command(BaseCommand):
    help = "Analizuje sentyment komentarzy bez wyników (backfill)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Przelicz ponownie wszystkie komentarze, nie tylko te bez wyników",
        )

    def handle(self, *args, **options):
        qs = Comment.objects.exclude(content="")
        if not options["all"]:
            qs = qs.filter(sentiment_score__isnull=True)

        total = qs.count()
        if total == 0:
            self.stdout.write("Brak komentarzy do analizy.")
            return

        self.stdout.write(f"Analizuję {total} komentarzy...")
        updated = 0

        for comment in qs.iterator():
            result = sentiment_service.analyze(comment.content)
            if result["score"] is not None:
                Comment.objects.filter(pk=comment.pk).update(
                    sentiment_score=result["score"],
                    sentiment_label=result["label"],
                )
                updated += 1
                if updated % 10 == 0:
                    self.stdout.write(f"  {updated}/{total}...")

        self.stdout.write(self.style.SUCCESS(f"Gotowe. Zaktualizowano {updated}/{total} komentarzy."))
