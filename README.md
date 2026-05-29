# RelayCore

> A self-hosted event gateway that ingests, verifies, deduplicates, routes, and delivers HTTP webhook events with the same structural discipline a SOC applies to alert pipelines.

---

## Why is it needed

Modern software stacks generate events from dozens of producers: GitHub pushes, form submissions, calendar changes, payment callbacks. Each destination (Slack, Discord, a database, an email service) expects a different payload shape, and each producer has its own signature scheme, retry logic, and delivery guarantees. The naive solution is point-to-point glue code: a script per integration, no visibility, no retries, no deduplication.

RelayCore replaces that with a single, observable ingestion layer. Every event flows through one gateway, gets verified and deduplicated atomically, is stored immutably, and is routed and transformed before delivery along with exponential backoff retries and a dead-letter queue when destinations fail.

---

## Who It's For

- **Engineering teams** running multiple webhook integrations who want one place to monitor, debug, and replay events instead of hunting through individual service logs.
- **Students and researchers** building event-driven systems who need a reference implementation of a reliable async pipeline with proper idempotency guarantees.
- **Anyone who has lost a webhook event and had no idea why.**

---

## How It Resembles a SOC Pipeline

A Security Operations Center ingests alerts from many sensors, normalises them into a common schema, applies detection rules, routes matches to analysts, and keeps an immutable audit trail. RelayCore does the same thing for application events:

| SOC Concept | RelayCore Equivalent |
|---|---|
| Sensor / log source | Source (one URL endpoint per producer) |
| Signature / authenticity check | HMAC-SHA256 verification per source |
| Deduplication / event correlation | Atomic Redis SET NX idempotency check |
| Alert normalisation | Transformer (payload shape per destination) |
| Detection rule / routing rule | Route (source + event type + JSONPath condition) |
| Alert fan-out to analysts | Fan-out delivery to multiple destinations |
| Retry / escalation policy | Exponential backoff → dead-letter queue |
| SIEM audit log | Immutable `WebhookDelivery` table |
| SOC dashboard | React monitoring dashboard |

The analogy is not cosmetic. The architectural problems are identical: at-least-once delivery, race-free deduplication, observable routing, and graceful degradation when a downstream system is slow or down.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Producers                           │
│         GitHub · Google Calendar · HTML Forms           │
└───────────────────────┬─────────────────────────────────┘
                        │  POST /webhooks/receive/<slug>/
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  Ingestion Layer (Django)                │
│                                                         │
│  1. Resolve Source by slug                              │
│  2. HMAC-SHA256 signature verification                  │
│  3. Source-level rate limit  (Redis sliding window)     │
│  4. Idempotency check        (Redis atomic SET NX)      │
│  5. Persist WebhookDelivery row  (status = received)    │
│  6. Enqueue Celery task → return 200 immediately        │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Redis (broker) │
              └────────┬────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Delivery Worker (Celery)                   │
│                                                         │
│  • find_matching_routes()  — event type + JSONPath      │
│  • Per-route rate limit check                           │
│  • transformer.transform(payload)                       │
│  • httpx.post(destination.url)                          │
│  • On failure: retry with 2^n second backoff (max 5)   │
│  • On max retries: status = dead_lettered               │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
  Slack     Discord      Database / Email / any HTTP

┌─────────────────────────────────────────────────────────┐
│           Celery Beat  (every 60 s)                     │
│  collect_metrics() → MetricPoint rows                   │
│  success rate · queue depth · dead letters ·            │
│  throughput · duplicates · sig failures                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│           React Dashboard  (localhost:5173)             │
│  Overview · Sources · Destinations · Routes ·           │
│  Deliveries  — live metrics, 10 s auto-refresh          │
└─────────────────────────────────────────────────────────┘
```
## Screenshots
![Django Admin Login](images/Django-admin.png)
![Dashboard](images/Dashboard-Overview.png)
![Routes](images/New-Route.png)
![Deliveries](images/Delieveries.png)

---

## Key Design Decisions

**HMAC-SHA256 per source, not per system.** Each source can require 
signature verification — the scheme GitHub uses — so only authenticated 
producers can inject events into the pipeline. A request that fails 
verification is logged as `sig_failed` and dropped before any processing occurs.

**Atomic deduplication over GET-then-SET.** Two concurrent requests carrying the same idempotency key would both pass a `GET` check before either writes. `SET NX` is a single atomic Redis operation — only one caller wins, guaranteed.

**200 on duplicates, never 4xx.** Returning an error code to a provider like GitHub signals a delivery failure and triggers their retry logic, flooding the system with the exact events you are trying to suppress.

**At-least-once, not exactly-once.** If a worker crashes after the Redis `SET NX` but before writing the `WebhookDelivery` row, the event is lost. Exactly-once across two independent systems (Redis + Postgres) requires distributed transactions; the tradeoff is not worth it for application webhooks.

**Fan-out, not first-match-wins.** All matching routes execute for every delivery. A push event can simultaneously notify Slack and write to Discord. Routes are evaluated in priority order but none short-circuits the rest.

**Auth headers encrypted at rest.** `Destination.auth_header` (Bearer tokens, API keys) is stored using Fernet symmetric encryption. The plaintext value only lives in memory during the Celery delivery task.

---

## Threat Model

**What RelayCore protects against**

- *Event spoofing* — HMAC-SHA256 verification ensures only producers who hold the shared secret can inject events into a source. A forged request fails before any DB write or task is enqueued.
- *Replay attacks* — the idempotency layer detects and drops repeated delivery of the same event. Even if an attacker captures and replays a valid signed request, the second delivery is silently absorbed (and logged as `duplicate`) without re-processing.
- *Abuse / DDoS via high event volume* — source-level and route-level rate limits (Redis sliding window) cap how many events a single producer can push per minute. Requests over the limit receive a 429 with a `Retry-After` header.
- *Credential leakage in storage* — destination auth headers (API keys, Bearer tokens) are encrypted at rest with Fernet. A full database dump does not expose usable credentials.

**What it explicitly does not protect against**

- *Compromised HMAC secrets* — if a producer's secret is leaked, an attacker can craft valid signatures indefinitely. Rotate secrets via the Sources page; there is no automatic secret rotation.
- *SSRF via destination URLs* — Relay will POST to any URL configured as a destination, including internal network addresses (`http://192.168.x.x/`, `http://localhost/`). In production, enforce a network-level allowlist for egress traffic.
- *Payload content* — Relay verifies the envelope (signature, rate limit, idempotency) but does not inspect or sanitise the payload body. Transformers receive raw producer data.
- *Man-in-the-middle on outbound delivery* — `httpx` uses system CA certificates but does not enforce certificate pinning to destinations.

**What would be added in a production hardening pass**

- Destination URL allowlist / SSRF guard (block private IP ranges before enqueuing).
- Automatic secret rotation with overlap window for zero-downtime key changes.
- mTLS for inbound producer connections where the producer supports client certificates.
- Per-delivery audit log of which transformer ran and what the transformed payload looked like, separate from the raw payload record.

---

## Performance

Run the included load test to measure your deployment. With all four processes running on a development laptop (single Celery worker, local Redis and Postgres):

```bash
python load_test.py --requests 300 --concurrency 20
```

Fill in your numbers after running it:

| Metric | Result |
|---|---|
| Throughput |  req/s |
| Latency p50 | 236.8 ms |
| Latency p95 | 1002.6 ms |
| Latency p99 | 296.7 ms |
| Success rate | 33 % | (rate-limited by design at 100 req/min)

> Note: the ingestion view returns 200 immediately after enqueuing — latency here measures time to accept and persist the event, not time to deliver to the destination. 429s are the rate limiter enforcing the configured limit

---

## Stack

| Component | Technology |
|---|---|
| Backend | Django 4.2, Django REST Framework 3.15 |
| Database | PostgreSQL |
| Task queue | Celery 5.3 + Celery Beat |
| Broker / cache / rate limit | Redis 5 |
| Outbound HTTP | httpx |
| Encryption | cryptography (Fernet) |
| JSONPath routing | jsonpath-ng |
| Frontend | React 18, TypeScript, Vite 5 |
| Styling | Tailwind CSS 3, Material Icons Round, Roboto Slab |
| Data fetching | TanStack Query v5, Axios |

---

## Docker

The entire stack — Django, Celery worker, Celery Beat, Redis, Postgres, and the React frontend served by nginx — runs with a single command:

```bash
# First time or after code changes — rebuilds images
docker compose up --build

# Subsequent runs — uses existing images, starts faster
docker compose up
```

Open **http://localhost** in your browser. The nginx container proxies `/api/` and `/webhooks/` to Django and serves the React SPA for everything else.

**First run only** — create a superuser after the containers are up:

```bash
docker compose exec web python manage.py createsuperuser
```

**Environment variables**

Copy `.env.example` to `.env` and fill in your values:

```powershell
cp .env.example .env
```

Set at minimum:

```env
SECRET_KEY=your-django-secret-key
FIELD_ENCRYPTION_KEY=your-fernet-key
DB_PASSWORD=postgres
```

The compose file injects `DB_HOST`, `DB_PORT`, and `REDIS_URL` automatically — do not set those in `.env` when running via Docker.

**Pushing to Docker Hub**

```bash
# Build and tag
docker build -t imann122/relaycore:latest .
docker build -t imann122/relaycore-frontend:latest ./frontend

# Push
docker push imann122/relaycore:latest
docker push imann122/relaycore-frontend:latest
```

Then update `docker-compose.yml` to use `image: imann122/relaycore:latest` instead of `build: .` for the `web`, `worker`, and `beat` services to pull pre-built images instead of building locally.

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

---

## Setup

```bash
git clone <repo-url>
cd relaycore_project

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create `.env` in the project root:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/relaycore
REDIS_URL=redis://localhost:6379/0
FIELD_ENCRYPTION_KEY=your-fernet-key
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

```bash
python manage.py migrate
python manage.py createsuperuser

cd frontend && npm install && cd ..
```

---

## Running

Four processes, each in its own terminal with the venv activated:

```bash
# 1 — Django
python manage.py runserver

# 2 — Celery worker  (-P solo required on Windows)
celery -A relaycore worker -P solo -l info

# 3 — Celery Beat
celery -A relaycore beat -l info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 4 — React dev server
cd frontend && npm run dev
```

Dashboard: **http://localhost:5173** — log in with your superuser credentials.

---

## Sending a Webhook

![Slack Webhook](images/Slack-sent.png)

```bash
curl -X POST http://localhost:8000/webhooks/receive/<source-slug>/ \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"repository": {"full_name": "you/repo"}, "pusher": {"name": "you"}, "ref": "refs/heads/main", "commits": []}'
```

Returns `{"status": "accepted", "delivery_id": N}`. Send the same payload twice to observe deduplication — the second call returns `{"status": "duplicate"}`.

---

## GitHub → Slack

The primary demo integration: a GitHub push event arrives at Relay, gets verified, routed, and transformed into a Slack message delivered via Slack's Incoming Webhooks API.

**How Slack Incoming Webhooks work**

Slack exposes a unique HTTPS URL per channel (generated at `api.slack.com/apps`). Any HTTP POST to that URL with a JSON body containing a `text` field appears as a message in that channel — no OAuth flow, no bot token, no Slack SDK. The `GitHubToSlackTransformer` produces exactly that shape:

```json
{
  "text": "🚀 *iman* pushed to `refs/heads/main` on *iman/relaycore*\n• `a1b2c3d` docs: add screenshots to README"
}
```

Relay POSTs this to the Slack webhook URL stored on the `Destination` model (encrypted at rest). Slack renders it with the pusher name bolded, the branch and repo in code formatting, and each commit as a bullet with its short SHA.

**Setting it up**

1. Go to `api.slack.com/apps` → Create New App → From scratch.
2. Under Features → Incoming Webhooks, toggle on and add a webhook to your target channel.
3. Copy the webhook URL (`https://hooks.slack.com/services/...`).
4. In the Relay dashboard: create a Destination with that URL, create a Source with slug `github-production` and signature scheme `github_hmac`, create a Route connecting them with transformer `github_to_slack`.
5. Point your GitHub repository webhook at `https://your-relay-host/webhooks/receive/github-production/` with the same secret you set on the Source.

Every push to that repository will now appear in your Slack channel within seconds, with HMAC verification, deduplication, and retry guarantees handled by Relay.

**Other built-in transformers**

`GitHubToDiscordTransformer` produces a Discord embed with the same commit information, posted to a Discord channel via its webhook URL — identical setup, different destination.

`CalendarToDatabaseTransformer` handles Google Calendar push notifications, which carry their metadata in HTTP headers (`X-Goog-Channel-ID`, `X-Goog-Resource-State`) rather than the body. Relay's ingestion layer extracts these headers and merges them into the payload under `__goog_meta` before the transformer runs, so the transformer has everything it needs in one dict.

`FormToEmailTransformer` converts an HTML contact form POST into a generic transactional email API shape compatible with SendGrid, Mailgun, and Postmark — swap the destination URL to change the email provider without touching the transformer.

---

## Adding a Transformer

1. Create `apps/transformers/your_transformer.py` extending `BaseTransformer`, implement `transform(self, payload: dict) -> dict`.
2. Add an entry to `TRANSFORMER_CHOICES` in `apps/transformers/choices.py`.
3. Add an entry to `TRANSFORMER_REGISTRY` in `apps/transformers/registry.py`.

---

## Testing

```bash
.venv\Scripts\activate
pytest
```

The test suite is split across four focused files plus one end-to-end file.

`tests/test_hmac.py` — unit tests for HMAC-SHA256 signature verification: valid signature passes, wrong secret fails, tampered body fails, missing header fails, malformed header fails. Then a second class tests the full view — valid request returns 200, invalid returns 401, unknown slug returns 404.

`tests/test_idempotency.py` — proves the Redis `SET NX` deduplication is race-free. A key seen for the first time returns `False` (new event); the same key immediately after returns `True` (duplicate). Also covers TTL expiry: after the window expires, the same key is treated as new again.

`tests/test_routing.py` — covers `find_matching_routes()` and `evaluate_conditions()` exhaustively: exact event type match, wildcard route matches any event, JSONPath condition match and mismatch, multiple conditions where all must pass, multiple routes returned in priority order, inactive routes excluded, routes from a different source excluded.

`tests/test_transformers.py` — It asserts the output shape of all four built-in transformers against known input payloads. Ensures a GitHub push event produces a Slack `text` field, a Discord `embeds` list, and so on.

`tests/test_e2e.py` — end-to-end pipeline test. It fires a real HTTP POST to the ingestion view, runs the Celery task synchronously in the same process, intercepts the outbound `httpx.post` call, and asserts the `WebhookDelivery` row reaches `status='delivered'`. Four scenarios covered: happy path delivery, duplicate suppression (httpx called exactly once across two identical requests), sig_failed logging, and no-matching-route handling.

![Pytests Results](images/pytest.png)

---

## Project Structure

```
relaycore_project/
├── apps/
│   ├── api/            # DRF viewsets, serializers, REST endpoints
│   ├── core/           # Models: Source, Destination, Route, WebhookDelivery, MetricPoint
│   ├── delivery/       # Celery tasks, rate limiter
│   ├── idempotency/    # Redis SET NX deduplication
│   ├── routing/        # JSONPath + event-type route evaluator
│   └── transformers/   # BaseTransformer + registry + 4 built-in transformers
├── frontend/src/
│   ├── api/            # Axios clients per resource
│   ├── components/     # Layout, Modal, UI primitives
│   └── pages/          # Overview, Sources, Destinations, Routes, Deliveries
├── tests/              # pytest suite
├── relaycore/      # Django settings, Celery bootstrap, root URLs
└── requirements.txt
```
