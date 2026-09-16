import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import ContactAttempt, TicketDownloadLog


class Command(BaseCommand):
    help = "Remove ticket IP logs older than 30 days and contact attempts older than a day."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true", help="Run immediately and every 24 hours."
        )

    def handle(self, *args, **options):
        while True:
            now = timezone.now()
            tickets, _ = TicketDownloadLog.objects.filter(
                created_at__lt=now - timedelta(days=30)
            ).delete()
            contacts, _ = ContactAttempt.objects.filter(
                created_at__lt=now - timedelta(days=1)
            ).delete()
            self.stdout.write(f"Removed {tickets} ticket logs and {contacts} contact attempts.")
            if not options["loop"]:
                return
            time.sleep(86400)
