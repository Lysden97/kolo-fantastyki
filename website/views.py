from datetime import timedelta

from django.utils.decorators import method_decorator

from website.models import Counter, Ticket, TicketDownloadLog

import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

import io
import uuid
from django.http import FileResponse, HttpResponseForbidden
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class GenerateTicketView(View):
    MAX_DOWNLOADS_PER_IP = 2

    def get(self, request):
        ip_address = get_client_ip(request)
        month_ago = timezone.now() - timedelta(days=30)
        downloads_count = TicketDownloadLog.objects.filter(ip_address=ip_address, created_at__gte=month_ago).count()
        if downloads_count >= self.MAX_DOWNLOADS_PER_IP:
            return HttpResponseForbidden('Przekroczono limit pobrań biletu (limit 2 biletów na użytkownika)')

        TicketDownloadLog.objects.create(ip_address=ip_address)

        ticket_id = str(uuid.uuid4())[:8]

        ticket = Ticket.objects.create(ticket_id=ticket_id)

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A6)
        width, height = A6

        if settings.DEBUG:
            template_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Lustro_bilet_pion.png')
        else:
            template_path = os.path.join(settings.STATIC_ROOT, 'images', 'Lustro_bilet_pion.png')

        if os.path.exists(template_path):
            p.drawImage(template_path, 0, 0, width, height)

        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(f'{request.build_absolute_uri('/website/verify-ticket/')}{ticket_id}')
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_reader = ImageReader(img_buffer)

        p.drawImage(qr_reader, 50, 110, 198, 167)

        p.showPage()
        p.save()
        buffer.seek(0)

        return FileResponse(buffer, as_attachment=False, filename=f'Bilet-{ticket_id}.pdf')


def staff_required_redirect_index(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return redirect('index')

    return _wrapped_view


@method_decorator(staff_required_redirect_index, name='dispatch')
class VerifyTicketView(View):
    template_name = 'verify-ticket.html'

    def _render_ticket(self, request, ticket_id, error=None, success_message=None, mark_used=False):
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)

            if mark_used:
                if not ticket.is_used:
                    ticket.is_used = True
                    ticket.verified_at = timezone.now()
                    ticket.save()
                    success_message = success_message or 'Bilet został pomyślnie oznaczony jako użyty'
                else:
                    error = error or 'Bilet został już wcześniej użyty'

            is_still_valid = True
            expiry_time = None
            if ticket.is_used and ticket.verified_at:
                expiry_time = ticket.verified_at + timedelta(hours=48)
                if timezone.now() > expiry_time:
                    is_still_valid = False

            context = {
                'ticket': ticket,
                'is_valid': is_still_valid,
                'ticket_id': ticket_id,
                'error': error,
                'success_message': success_message,
                'expiry_time': expiry_time,
            }
            return render(request, self.template_name, context)

        except Ticket.DoesNotExist:
            context = {
                'ticket': None,
                'error': 'Bilet o podanym ID nie istnieje',
                'ticket_id': ticket_id,
                'is_valid': False,
            }
            return render(request, self.template_name, context)

        except Exception:
            context = {
                'ticket': None,
                'error': 'Wystąpił błąd podczas przetwarzania biletu',
                'ticket_id': ticket_id,
                'is_valid': False,
            }
            return render(request, self.template_name, context)

    def get(self, request, ticket_id):
        return self._render_ticket(request, ticket_id)

    def post(self, request, ticket_id):
        return self._render_ticket(request, ticket_id, mark_used=True)


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


class RulesView(View):
    def get(self, request):
        return render(request, 'rules.html')
