from django.contrib import admin

from website.models import Counter, Ticket, TicketDownloadLog

# Register your models here.
admin.site.register(Counter)
admin.site.register(Ticket)
admin.site.register(TicketDownloadLog)