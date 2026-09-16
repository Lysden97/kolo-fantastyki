from django.core.exceptions import ValidationError
from django.db import models


class Counter(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    link = models.URLField(max_length=500, default="https://www.facebook.com/KoloFantastykiIGier/")

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "Koniec wydarzenia musi nastąpić po jego rozpoczęciu."}
            )

    def __str__(self):
        return self.name


class Ticket(models.Model):
    # CharField preserves previously issued eight-character ticket URLs.
    ticket_id = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Bilet {self.ticket_id}"


class TicketDownloadLog(models.Model):
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["ip_address", "created_at"], name="ticket_ip_created_idx")]


class ContactAttempt(models.Model):
    """Only IP and time are retained; message content stays out of the database."""

    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["ip_address", "created_at"], name="contact_ip_created_idx")]
