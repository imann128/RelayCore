"""
Load test for the Webhook Relay ingestion endpoint.

Sends N concurrent webhook requests and reports:
  - Total requests sent
  - Requests per second (throughput)
  - Success / duplicate / error counts
  - p50, p95, p99 latency in milliseconds

Usage (with all 4 processes running):
    python load_test.py

Optional flags:
    python load_test.py --url http://localhost:8000 --slug github-production \
                        --requests 500 --concurrency 20 --secret your-hmac-secret
"""

import argparse
import hashlib
import hmac
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


# ---------------------------------------------------------------------------
# Defaults — change these or pass via CLI flags
# ---------------------------------------------------------------------------
DEFAULT_URL         = 'http://localhost:8000'
DEFAULT_SLUG        = 'github-production'
DEFAULT_SECRET      = ''          # leave blank if source has no HMAC secret
DEFAULT_REQUESTS    = 300
DEFAULT_CONCURRENCY = 20

PAYLOAD = {
    'ref': 'refs/heads/main',
    'pusher': {'name': 'load-test'},
    'repository': {'full_name': 'iman/webhook-relay'},
    'commits': [{'id': 'a1b2c3d', 'message': 'load test commit'}],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(
        key=secret.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f'sha256={digest}'


def send_one(url: str, slug: str, secret: str, body: bytes) -> dict:
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': 'push',
    }
    if secret:
        headers['X-Hub-Signature-256'] = make_signature(secret, body)

    start = time.perf_counter()
    try:
        r = httpx.post(
            f'{url}/webhooks/receive/{slug}/',
            content=body,
            headers=headers,
            timeout=10.0,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {'status': r.status_code, 'body': r.json(), 'ms': elapsed_ms}
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {'status': 0, 'error': str(exc), 'ms': elapsed_ms}


def percentile(data: list, p: float) -> float:
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Webhook Relay load test')
    parser.add_argument('--url',         default=DEFAULT_URL)
    parser.add_argument('--slug',        default=DEFAULT_SLUG)
    parser.add_argument('--secret',      default=DEFAULT_SECRET)
    parser.add_argument('--requests',    type=int, default=DEFAULT_REQUESTS)
    parser.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY)
    args = parser.parse_args()

    # Use unique payloads so idempotency doesn't drop them all as duplicates.
    # Each request gets a unique commit id.
    bodies = [
        json.dumps({**PAYLOAD, 'commits': [{'id': f'load{i:06d}', 'message': f'commit {i}'}]}).encode()
        for i in range(args.requests)
    ]

    print(f'\nWebhook Relay — Load Test')
    print(f'  Target      : {args.url}/webhooks/receive/{args.slug}/')
    print(f'  Requests    : {args.requests}')
    print(f'  Concurrency : {args.concurrency}')
    print(f'  HMAC secret : {"set" if args.secret else "none"}\n')
    print('Running...', flush=True)

    results = []
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(send_one, args.url, args.slug, args.secret, body)
            for body in bodies
        ]
        for future in as_completed(futures):
            results.append(future.result())

    wall_elapsed = time.perf_counter() - wall_start

    # Tally results
    ok        = [r for r in results if r['status'] == 200 and r.get('body', {}).get('status') == 'accepted']
    duplicate = [r for r in results if r['status'] == 200 and r.get('body', {}).get('status') == 'duplicate']
    errors    = [r for r in results if r['status'] not in (200,) or 'error' in r]
    latencies = [r['ms'] for r in results]

    rps = len(results) / wall_elapsed

    print(f'\n{"─" * 44}')
    print(f'  Total sent    : {len(results)}')
    print(f'  Accepted      : {len(ok)}')
    print(f'  Duplicates    : {len(duplicate)}')
    print(f'  Errors        : {len(errors)}')
    print(f'{"─" * 44}')
    print(f'  Throughput    : {rps:.1f} req/s')
    print(f'  Wall time     : {wall_elapsed:.2f}s')
    print(f'{"─" * 44}')
    print(f'  Latency p50   : {percentile(latencies, 50):.1f} ms')
    print(f'  Latency p95   : {percentile(latencies, 95):.1f} ms')
    print(f'  Latency p99   : {percentile(latencies, 99):.1f} ms')
    print(f'  Latency mean  : {statistics.mean(latencies):.1f} ms')
    print(f'  Latency max   : {max(latencies):.1f} ms')
    print(f'{"─" * 44}\n')

    if errors:
        print('First 3 errors:')
        for e in errors[:3]:
            print(f'  status={e["status"]} error={e.get("error") or e.get("body")}')


if __name__ == '__main__':
    main()
