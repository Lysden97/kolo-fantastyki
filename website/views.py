from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from website.models import Counter


# Create your views here.

class IndexView(View):
    def get(self, request):
        convention = Counter.objects.last()
        now = timezone.now()

        if not convention:
            status = 'Nowe informacje wkrótce!'

            context = {
                'status': status,
            }
            return render(request, 'index.html', context)

        timestamp_start = None
        timestamp_end = None

        if convention.start_date < now <= convention.end_date:
            status = 'Konwent właśnie trwa'
            timestamp_end = int(convention.end_date.timestamp() * 1000)
        elif now < convention.start_date:
            status = 'Konwent jeszcze się nie rozpoczął'
            timestamp_start = int(convention.start_date.timestamp() * 1000)


        context = {
            'convention': convention,
            'status': status,
            'timestamp_start': timestamp_start,
            'timestamp_end': timestamp_end,
        }

        return render(request, 'index.html', context)
