from django.db import models

# Create your models here.

class Counter(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    link = models.CharField(max_length=500, default='https://www.facebook.com/KoloFantastykiIGier/')

    def __str__(self):
        return self.name

class Ticket(models.Model):
    ticket_id = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'Bilet {self.ticket_id}'

class TicketDownloadLog(models.Model):
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)
