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

        status = 'Nowe informacje wkrótce!'
        timestamp_start = None
        timestamp_end = None

        if convention.start_date < now <= convention.end_date:
            status = 'Wydarzenie właśnie trwa'
            timestamp_end = int(convention.end_date.timestamp() * 1000)
        elif now < convention.start_date:
            status = 'Wydarzenie jeszcze się nie rozpoczęło'
            timestamp_start = int(convention.start_date.timestamp() * 1000)


        context = {
            'convention': convention,
            'status': status,
            'timestamp_start': timestamp_start,
            'timestamp_end': timestamp_end,
        }

        return render(request, 'index.html', context)
