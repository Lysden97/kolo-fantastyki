# Security

## Reporting a vulnerability

Use **Security → Report a vulnerability** on this repository if private reporting is enabled.
Include the affected version, reproduction steps and expected impact. Do not include real
credentials, ticket identifiers or participant data.

If private reporting is unavailable, open an issue requesting a private contact channel
without publishing vulnerability details or exploit instructions.

## Configuration

- Django and PostgreSQL secrets come from environment variables. Local `.env` files are
  excluded from Git and Docker builds; `.env.example` contains no working credentials.
- Use separate secrets for each deployment and rotate any exposed values.
- Production settings use HTTPS redirects and secure cookies when `DEBUG=False`.
  The supplied Compose configuration is intended for local use; production requires TLS.

## Request limits and access

- Ticket generation is limited to 2 downloads per IP address over a rolling 30-day period.
- The contact form accepts up to 3 valid submission attempts per IP address per hour.
  SMTP failures still count towards this limit.
- PostgreSQL transaction locks enforce limits across application workers. SQLite is for
  local development only. Users sharing a public IP address share the same quota.
- Ticket verification requires an authenticated staff account. State-changing requests
  use POST and CSRF protection.

## IP retention

The cleanup service runs at startup and every 24 hours. It deletes ticket download logs
older than 30 days and contact attempt logs older than 1 day. Deletion may occur up to one
cleanup interval after those thresholds, provided the service is running.

Contact message content is not stored in the application database. This cleanup does not
delete tickets, infrastructure logs, backups or messages retained by the mail provider;
configure retention for those separately.

## Trusted proxy

`TRUST_PROXY_HEADERS` defaults to `False`. Enable it only when the application is reachable
exclusively through a trusted proxy. The supplied Nginx configuration overwrites
`X-Forwarded-For` and `X-Forwarded-Proto`, and Compose does not publish Gunicorn's port.

Additional proxies require an explicit trust configuration. Client-supplied forwarding
headers must not be passed through unchecked.

## Automated checks

CI scans the complete Git history of all fetched branches and tags with Gitleaks, including
the commit under review. Findings are redacted. Dependency audits run alongside the tests.
