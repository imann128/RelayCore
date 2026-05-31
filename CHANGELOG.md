# Changelog

All notable changes to RelayCore are documented here.
Versioning follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

---

## [1.1.0] — 2026-05-31

### Security
- **SSRF guard** — destination URLs are now validated against RFC 1918 private ranges, loopback, and link-local addresses (including the AWS metadata endpoint `169.254.169.254`) at two independent points: on save via `Destination.clean()` and again inside the Celery delivery task before the outbound HTTP POST.
- **Brute-force login protection** — `django-axes` locks out a username after 5 consecutive failed login attempts for one hour, with automatic reset on successful authentication. Tracking by username rather than IP remains effective against distributed attacks.
- **HTTPS enforcement** — `SECURE_SSL_REDIRECT`, one-year HSTS, and secure cookie flags activate automatically when `DEBUG=False`.

### Added
- **User action audit log** — every create, update, and delete on Sources, Destinations, and Routes is recorded via `django-auditlog` with actor, timestamp, and a field-level diff. `auth_header` is excluded from diffs. Viewable in the new Audit Log dashboard page.
- **Docker support** — `Dockerfile`, `docker-compose.yml`, and `frontend/Dockerfile` added. The full stack (Django, Celery worker, Celery Beat, Redis, Postgres, nginx) starts with `docker compose up --build`.
- **Docker Hub images** — `imann122/relaycore:latest` and `imann122/relaycore-frontend:latest` published.
- **Passthrough transformer** — registered in choices and registry so it is selectable in the dashboard.
- **Duplicate and sig_failed metrics** — `collect_metrics` now aggregates these counts and the Overview dashboard surfaces them as metric cards.

### Fixed
- Dead code in `routing/service.py` — the first unused `candidates` queryset was removed; `Q` import moved to module level.
- Bare `except (InvalidToken, Exception)` in `EncryptedCharField.from_db_value` narrowed to `except InvalidToken`.
- `getattr(destination, 'timeout_seconds', ...)` replaced with direct field access since `timeout_seconds` is a concrete model field.
- Redis singleton pattern added to `idempotency/service.py` to match the pattern already used in `ratelimit.py`.
- `delivery.status = 'routed'` now set before `route_and_deliver.delay()` so eager task execution in tests does not overwrite the final status.

### Changed
- Project renamed from **Webhook Relay** to **RelayCore**. Django module renamed from `webhook_relay` to `relaycore`.
- All `# ---` separator comments removed across the codebase.
- `monitoring/views.py` cleared — the HTMX dashboard is superseded by the React frontend.

---

## [1.0.0] — 2026-05-29

Initial release.

### Features
- Webhook ingestion at `/webhooks/receive/<slug>/` with HMAC-SHA256 signature verification
- Atomic Redis `SET NX` idempotency — duplicate events dropped, not re-processed
- Source-level and route-level rate limiting via Redis sliding window
- JSONPath condition matching and event-type filtering on routes
- Fan-out routing — all matching routes execute per delivery
- Exponential backoff retries (2^n seconds, max 5 attempts) with dead-letter queue
- Four built-in transformers: GitHub → Slack, GitHub → Discord, Google Calendar → DB, HTML Form → Email
- `auth_header` encrypted at rest with Fernet symmetric encryption
- Celery Beat metric aggregation every 60 seconds
- Django REST Framework API for Sources, Destinations, Routes, Deliveries, and Metrics
- React + TypeScript dashboard with live 10-second auto-refresh
- 57-test pytest suite covering HMAC, idempotency, routing, transformers, and end-to-end pipeline
