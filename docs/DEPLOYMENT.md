# Deployment and updates

The supplied Compose configuration runs locally at 127.0.0.1:8001.
The application uses Gunicorn, but the proxy has no TLS certificate configured.

## Before deployment

1. Back up the database and verify that it can be restored.
2. Generate deployment-specific secrets for PostgreSQL and Django's `SECRET_KEY`.
3. Set `DEBUG=False`, `ALLOWED_HOSTS` to your domain and `CSRF_TRUSTED_ORIGINS` to its HTTPS origin.
4. Configure TLS in Nginx, mount certificates read-only and redirect port 80 to 443.
5. Keep overwriting `X-Forwarded-For` and `X-Forwarded-Proto`. Only the trusted proxy should be able to reach Gunicorn.
6. Configure the SMTP backend, a sender address on your mail domain and `CONTACT_RECIPIENT`.
7. Run migrations against a copy of the database, then run tests and deployment checks.

```bash
python manage.py check --deploy --fail-level WARNING
```

HSTS applies only to the configured domain; `includeSubDomains` and `preload` are
not enabled automatically. The command may report warnings for these options.
Review all subdomains and the preload requirements before enabling them.

If TLS terminates at another proxy in front of Nginx, configure that trust boundary
explicitly. The current Nginx configuration overwrites the forwarded protocol with
its own connection scheme. Do not blindly forward headers supplied by clients.

## Upgrading from an earlier version

- Keep the `postgres_data` volume; deleting it removes the database.
- Preserve the existing database name and user in `DATABASE_NAME` and `DATABASE_USER`.
- When rotating a password, update it in PostgreSQL as well as in `.env`.
- Migration `0006` extends the ticket identifier field without changing existing
  ticket values, and adds contact attempt logs and indexes.
- Existing eight-character QR links and the original admin URL remain available.
- Collected static files now use a separate `staticfiles` volume.
- Check the dates of existing events. Date validation applies to new form submissions
  and does not automatically change historical records.

## Maintenance

Compose runs a separate `cleanup` service at startup and every 24 hours.
Alternatively, a host scheduler can run this command once a day:

```bash
python manage.py clean_old_ticket_logs
```

Ticket IP logs are deleted after 30 days and contact attempt logs after 1 day,
subject to the cleanup schedule. This command does not delete tickets.
The contact form allows 3 attempts per IP address per hour, including attempts
made while SMTP is unavailable. Message content is not stored in the database.

Maintain database backups, update pinned dependencies and monitor application logs
and the `cleanup` service. Test new container images and migrations before updating
a running deployment.
