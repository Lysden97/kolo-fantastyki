import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from pathlib import Path
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import (
    Client,
    RequestFactory,
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone

from .models import ContactAttempt, Counter, Ticket, TicketDownloadLog
from .services import RateLimitExceeded, generate_ticket, reserve_contact_attempt, verify_ticket


class StaticAssetTests(SimpleTestCase):
    def test_template_assets_exist_with_exact_case(self):
        root = Path(settings.BASE_DIR)
        assets = {
            p.relative_to(root / "static").as_posix()
            for p in (root / "static").rglob("*")
            if p.is_file()
        }
        for template in (root / "templates").glob("*.html"):
            for name in re.findall(
                r"static ['\"]([^'\"]+)['\"]", template.read_text(encoding="utf-8")
            ):
                with self.subTest(template=template.name, asset=name):
                    self.assertIn(name, assets)


class HomepageTests(TestCase):
    def test_empty(self):
        response = self.client.get("/")
        self.assertContains(response, "Nowe informacje wkrótce!")
        self.assertNotContains(response, "Pobierz darmowy bilet!")

    def test_event_phases_and_boundaries(self):
        now = timezone.now()
        event = Counter.objects.create(
            name="Demo", start_date=now, end_date=now + timedelta(days=2)
        )
        for instant, expected in [
            (now - timedelta(seconds=1), "Wydarzenie jeszcze się nie rozpoczęło"),
            (now, "Wydarzenie właśnie trwa"),
            (now + timedelta(days=1), "Wydarzenie właśnie trwa"),
            (event.end_date, "Nowe informacje wkrótce!"),
        ]:
            with (
                self.subTest(instant=instant),
                patch("website.views.timezone.now", return_value=instant),
            ):
                self.assertEqual(self.client.get("/").context["status"], expected)

    def test_invalid_dates(self):
        now = timezone.now()
        event = Counter(name="Demo", start_date=now, end_date=now - timedelta(days=1))
        with self.assertRaises(ValidationError):
            event.full_clean()


class TicketTests(TestCase):
    def test_get_cannot_create_ticket(self):
        self.assertEqual(self.client.get(reverse("generate_ticket")).status_code, 405)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_csrf_required(self):
        response = Client(enforce_csrf_checks=True).post(reverse("generate_ticket"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Ticket.objects.exists())

    def test_pdf_and_qr_url(self):
        with patch("website.services.qrcode.make", wraps=__import__("qrcode").make) as qr:
            response = self.client.post(reverse("generate_ticket"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))
        list(response.streaming_content)
        ticket = Ticket.objects.get()
        self.assertEqual(len(ticket.ticket_id), 32)
        qr.assert_called_once_with(
            "http://testserver" + reverse("verify-ticket", args=[ticket.ticket_id])
        )
        self.assertEqual(TicketDownloadLog.objects.count(), 1)

    def test_limit_and_untrusted_forwarding_header(self):
        for index in range(2):
            response = self.client.post(
                reverse("generate_ticket"), HTTP_X_FORWARDED_FOR=f"192.0.2.{index}"
            )
            self.assertEqual(response.status_code, 200)
            list(response.streaming_content)
        self.assertEqual(
            self.client.post(
                reverse("generate_ticket"), HTTP_X_FORWARDED_FOR="192.0.2.99"
            ).status_code,
            429,
        )
        self.assertEqual(Ticket.objects.count(), 2)

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_trusted_proxy_and_invalid_chain(self):
        response = self.client.post(reverse("generate_ticket"), HTTP_X_FORWARDED_FOR="2001:db8::1")
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)
        self.assertEqual(TicketDownloadLog.objects.get().ip_address, "2001:db8::1")
        self.assertEqual(
            self.client.post(
                reverse("generate_ticket"), HTTP_X_FORWARDED_FOR="192.0.2.1, 192.0.2.2"
            ).status_code,
            400,
        )

    def test_expired_logs_do_not_consume_quota(self):
        log = TicketDownloadLog.objects.create(ip_address="127.0.0.1")
        TicketDownloadLog.objects.filter(pk=log.pk).update(
            created_at=timezone.now() - timedelta(days=31)
        )
        response = self.client.post(reverse("generate_ticket"))
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)

    def test_pdf_failure_rolls_back(self):
        with patch("website.services.render_ticket_pdf", side_effect=OSError("PDF failure")):
            with self.assertRaises(OSError):
                self.client.post(reverse("generate_ticket"))
        self.assertFalse(Ticket.objects.exists())
        self.assertFalse(TicketDownloadLog.objects.exists())


class VerificationTests(TestCase):
    def setUp(self):
        self.ticket = Ticket.objects.create(ticket_id="old12345")
        self.url = reverse("verify-ticket", args=[self.ticket.ticket_id])
        self.staff = get_user_model().objects.create_user(username="staff", is_staff=True)

    def test_access_control(self):
        for method in [self.client.get, self.client.post]:
            self.assertRedirects(method(self.url), "/")
        user = get_user_model().objects.create_user(username="visitor")
        self.client.force_login(user)
        self.assertRedirects(self.client.post(self.url), "/")
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.is_used)

    def test_get_is_read_only_and_legacy_url_works(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.is_used)

    def test_verification_cannot_extend_validity(self):
        self.client.force_login(self.staff)
        self.client.post(self.url)
        self.ticket.refresh_from_db()
        first = self.ticket.verified_at
        response = self.client.post(self.url)
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.is_used)
        self.assertEqual(self.ticket.verified_at, first)
        self.assertIsNotNone(response.context["error"])

    def test_expiration_boundary(self):
        self.client.force_login(self.staff)
        verified = timezone.now()
        self.ticket.is_used = True
        self.ticket.verified_at = verified
        self.ticket.save()
        for hours, valid in [(47, True), (48, False), (49, False)]:
            with patch(
                "website.views.timezone.now", return_value=verified + timedelta(hours=hours)
            ):
                self.assertEqual(self.client.get(self.url).context["is_valid"], valid)

    def test_missing(self):
        self.client.force_login(self.staff)
        self.assertEqual(
            self.client.get(reverse("verify-ticket", args=["missing"])).status_code, 404
        )

    def test_csrf_required_for_verification(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.post(self.url).status_code, 403)


class ContactTests(TestCase):
    data = {
        "message-name": "Demo",
        "message-email": "visitor@example.com",
        "message-phone": "",
        "message-subject": "Test message",
    }

    @override_settings(
        DEFAULT_FROM_EMAIL="sender@example.com", CONTACT_RECIPIENT="club@example.com"
    )
    def test_sender_reply_to_and_content(self):
        self.assertRedirects(self.client.post(reverse("contact"), self.data), "/#contact-2320")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.from_email, "sender@example.com")
        self.assertEqual(email.to, ["club@example.com"])
        self.assertEqual(email.reply_to, ["visitor@example.com"])
        self.assertIn("Test message", email.body)

    def test_validation(self):
        for field, value in [
            ("message-email", "invalid"),
            ("message-name", "a\nb"),
            ("message-subject", ""),
            ("message-subject", "a" * 5001),
            ("message-phone", "bad-phone"),
        ]:
            with self.subTest(field=field, value=value[:20]):
                self.assertEqual(
                    self.client.post(reverse("contact"), {**self.data, field: value}).status_code,
                    400,
                )
        self.assertFalse(ContactAttempt.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.post(reverse("contact"), self.data).status_code, 302)
        self.assertEqual(self.client.post(reverse("contact"), self.data).status_code, 429)
        self.assertEqual(len(mail.outbox), 3)

    def test_old_attempts_do_not_consume_quota(self):
        attempt = ContactAttempt.objects.create(ip_address="127.0.0.1")
        ContactAttempt.objects.filter(pk=attempt.pk).update(
            created_at=timezone.now() - timedelta(hours=2)
        )
        self.assertEqual(self.client.post(reverse("contact"), self.data).status_code, 302)

    def test_smtp_failure_is_handled(self):
        with patch("website.views.EmailMultiAlternatives.send", side_effect=OSError("offline")):
            with self.assertLogs("website.views", level="WARNING"):
                response = self.client.post(reverse("contact"), self.data, follow=True)
        self.assertContains(response, "Nie udało się wysłać wiadomości.")
        self.assertEqual(ContactAttempt.objects.count(), 1)


class MaintenanceTests(TestCase):
    def test_cleanup_preserves_recent_logs_and_tickets(self):
        now = timezone.now()
        for model, days in [(TicketDownloadLog, 31), (ContactAttempt, 2)]:
            old = model.objects.create(ip_address="192.0.2.1")
            model.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=days))
            model.objects.create(ip_address="192.0.2.2")
        ticket = Ticket.objects.create(ticket_id="legacy01")
        call_command("clean_old_ticket_logs", stdout=StringIO())
        self.assertEqual(TicketDownloadLog.objects.get().ip_address, "192.0.2.2")
        self.assertEqual(ContactAttempt.objects.get().ip_address, "192.0.2.2")
        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    @override_settings(DEBUG=True)
    def test_demo_is_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Counter.objects.count(), 1)
        self.assertFalse(get_user_model().objects.exists())


@skipUnless(connection.vendor == "postgresql", "Concurrency requires PostgreSQL")
class ConcurrencyTests(TransactionTestCase):
    def run_parallel(self, operation, count=4):
        barrier = Barrier(count)

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=count) as pool:
            return list(pool.map(lambda _: worker(), range(count)))

    def test_concurrent_ticket_quota(self):
        def operation():
            request = RequestFactory().post("/website/ticket/")
            try:
                _, pdf = generate_ticket(request)
                pdf.close()
                return True
            except RateLimitExceeded:
                return False

        results = self.run_parallel(operation)
        self.assertEqual(sum(results), 2)
        self.assertEqual(Ticket.objects.count(), 2)
        self.assertEqual(TicketDownloadLog.objects.count(), 2)

    def test_concurrent_contact_quota(self):
        def operation():
            try:
                reserve_contact_attempt(RequestFactory().post("/website/contact/"))
                return True
            except RateLimitExceeded:
                return False

        self.assertEqual(sum(self.run_parallel(operation)), 3)
        self.assertEqual(ContactAttempt.objects.count(), 3)

    def test_concurrent_verification(self):
        ticket = Ticket.objects.create(ticket_id="legacy01")
        results = self.run_parallel(lambda: verify_ticket(ticket.ticket_id)[1])
        self.assertEqual(sum(results), 1)
