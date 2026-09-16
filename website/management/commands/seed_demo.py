from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from website.models import Counter


class Command(BaseCommand):
    help = "Create or update a fictional upcoming event. Never creates accounts or credentials."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be created with DEBUG=True.")
        start = timezone.now() + timedelta(days=7)
        Counter.objects.update_or_create(
            name="Demo — spotkanie miłośników fantastyki",
            defaults={
                "start_date": start,
                "end_date": start + timedelta(days=2),
                "link": "https://example.com/",
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo event ready."))
