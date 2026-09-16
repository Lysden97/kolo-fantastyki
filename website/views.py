import logging
from datetime import timedelta
from functools import wraps
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views import View

from .forms import ContactForm
from .models import Counter, Ticket
from .services import RateLimitExceeded, generate_ticket, reserve_contact_attempt, verify_ticket

logger = logging.getLogger(__name__)


class GenerateTicketView(View):
    def post(self, request):
        try:
            ticket, pdf = generate_ticket(request)
        except RateLimitExceeded:
            return HttpResponse("Limit 2 biletów na adres IP w ciągu 30 dni.", status=429)
        return FileResponse(
            pdf, content_type="application/pdf", filename=f"Bilet-{ticket.ticket_id}.pdf"
        )


def staff_required_redirect_index(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return redirect("index")

    return wrapped


@method_decorator(staff_required_redirect_index, name="dispatch")
class VerifyTicketView(View):
    def _render_ticket(self, request, ticket_id, mark_used=False):
        error = success = None
        try:
            if mark_used:
                ticket, changed = verify_ticket(ticket_id)
                if changed:
                    success = "Bilet został pomyślnie oznaczony jako użyty"
                else:
                    error = "Bilet został już wcześniej użyty"
            else:
                ticket = Ticket.objects.get(ticket_id=ticket_id)
        except Ticket.DoesNotExist:
            return render(
                request,
                "verify-ticket.html",
                {
                    "ticket": None,
                    "ticket_id": ticket_id,
                    "is_valid": False,
                    "error": "Bilet o podanym ID nie istnieje",
                },
                status=404,
            )
        expiry = ticket.verified_at + timedelta(hours=48) if ticket.verified_at else None
        valid = not ticket.is_used or (expiry is not None and timezone.now() < expiry)
        return render(
            request,
            "verify-ticket.html",
            {
                "ticket": ticket,
                "ticket_id": ticket_id,
                "is_valid": valid,
                "expiry_time": expiry,
                "error": error,
                "success_message": success,
            },
        )

    def get(self, request, ticket_id):
        return self._render_ticket(request, ticket_id)

    def post(self, request, ticket_id):
        return self._render_ticket(request, ticket_id, mark_used=True)


class IndexView(View):
    def get(self, request):
        convention = Counter.objects.last()
        now = timezone.now()
        status = "Nowe informacje wkrótce!"
        timestamp_start = timestamp_end = None
        if convention:
            if convention.start_date <= now < convention.end_date:
                status = "Wydarzenie właśnie trwa"
                timestamp_end = int(convention.end_date.timestamp() * 1000)
            elif now < convention.start_date:
                status = "Wydarzenie jeszcze się nie rozpoczęło"
                timestamp_start = int(convention.start_date.timestamp() * 1000)
        return render(
            request,
            "index.html",
            {
                "convention": convention,
                "status": status,
                "timestamp_start": timestamp_start,
                "timestamp_end": timestamp_end,
            },
        )


class RulesView(View):
    def get(self, request):
        return render(request, "rules.html")


class ContactView(View):
    def get(self, request):
        return redirect("/#contact-2320")

    def post(self, request):
        form = ContactForm(request.POST, prefix="message")
        if not form.is_valid():
            return render(request, "contact-errors.html", {"form": form}, status=400)
        try:
            reserve_contact_attempt(request)
        except RateLimitExceeded:
            return HttpResponse("Limit 3 wiadomości na godzinę z jednego adresu IP.", status=429)
        context = {f"message_{key}": value for key, value in form.cleaned_data.items()}
        html = render_to_string("email.html", context)
        email = EmailMultiAlternatives(
            subject=f"Nowa wiadomość od {form.cleaned_data['name']}",
            body=strip_tags(html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_RECIPIENT],
            reply_to=[form.cleaned_data["email"]],
        )
        email.attach_alternative(html, "text/html")
        try:
            email.send()
        except (SMTPException, OSError):
            logger.warning("Contact email delivery failed", exc_info=True)
            messages.error(request, "Nie udało się wysłać wiadomości. Spróbuj ponownie później.")
        else:
            messages.success(request, "Twoja wiadomość została wysłana. Dziękujemy!")
        return redirect("/#contact-2320")
