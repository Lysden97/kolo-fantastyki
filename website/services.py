"""Ticket creation and rate limits shared by all PostgreSQL workers."""

import hashlib
import io
import uuid
from contextlib import contextmanager
from datetime import timedelta
from ipaddress import ip_address

import qrcode
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import SuspiciousOperation
from django.db import connection, transaction
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.pagesizes import A6
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import ContactAttempt, Ticket, TicketDownloadLog


class RateLimitExceeded(Exception):
    pass


def get_client_ip(request):
    # TRUST_PROXY_HEADERS requires a proxy which overwrites this header and
    # an app port that is inaccessible to untrusted clients (see Compose).
    raw = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_PROXY_HEADERS:
        raw = request.META.get("HTTP_X_FORWARDED_FOR", raw)
    try:
        return str(ip_address(raw.strip()))
    except ValueError as exc:
        raise SuspiciousOperation("Invalid client IP address") from exc


@contextmanager
def rate_limit_lock(scope, client_ip):
    with transaction.atomic():
        if connection.vendor == "postgresql":
            key = int.from_bytes(
                hashlib.sha256(f"{scope}:{client_ip}".encode()).digest()[:8],
                byteorder="big",
                signed=True,
            )
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
        # SQLite is for single-user development; concurrency is tested on PostgreSQL.
        yield


def render_ticket_pdf(ticket_id, verification_url):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A6)
    template = finders.find("images/Lustro_bilet_pion.png")
    if template:
        pdf.drawImage(template, 0, 0, *A6)
    qr = qrcode.make(verification_url).convert("RGB")
    # Preserve the square aspect ratio for reliable scanning.
    pdf.drawImage(ImageReader(qr), 65, 110, 167, 167)
    pdf.setTitle(f"Bilet {ticket_id}")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def generate_ticket(request):
    client_ip = get_client_ip(request)
    with rate_limit_lock("ticket", client_ip):
        cutoff = timezone.now() - timedelta(days=30)
        if (
            TicketDownloadLog.objects.filter(ip_address=client_ip, created_at__gte=cutoff).count()
            >= 2
        ):
            raise RateLimitExceeded
        ticket = Ticket.objects.create(ticket_id=uuid.uuid4().hex)
        url = request.build_absolute_uri(reverse("verify-ticket", args=[ticket.ticket_id]))
        # Render before committing, so a PDF error doesn't consume a ticket or quota.
        pdf = render_ticket_pdf(ticket.ticket_id, url)
        TicketDownloadLog.objects.create(ip_address=client_ip)
    return ticket, pdf


def reserve_contact_attempt(request):
    client_ip = get_client_ip(request)
    with rate_limit_lock("contact", client_ip):
        cutoff = timezone.now() - timedelta(hours=1)
        if ContactAttempt.objects.filter(ip_address=client_ip, created_at__gte=cutoff).count() >= 3:
            raise RateLimitExceeded
        # Failed SMTP attempts count too, to bound retries against a failing service.
        ContactAttempt.objects.create(ip_address=client_ip)


def verify_ticket(ticket_id):
    with transaction.atomic():
        ticket = Ticket.objects.select_for_update().get(ticket_id=ticket_id)
        changed = not ticket.is_used
        if changed:
            ticket.is_used = True
            ticket.verified_at = timezone.now()
            ticket.save(update_fields=["is_used", "verified_at"])
        return ticket, changed
