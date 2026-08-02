# Social Campaign Publisher

Multi-platform social campaign publishing service with durable retries, webhook verification, and end-to-end monitoring.

**Repository**: https://github.com/ReignnRule11/social-campaign-publisher

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start](#quick-start)
- [API Examples](#api-examples)
- [Monitoring & Dashboards](#monitoring--dashboards)
- [Secret Management](#secret-management)
- [Docker Deployment](#docker-deployment)
- [Documentation](#documentation)

## Overview

This is a FlyRank capstone project implementing a FastAPI service that:

1. **Accepts campaigns** — blog post + metadata
2. **Generates per-platform artifacts** — tailored content for each social network
3. **Publishes idempotently** — exactly-once semantics with retry logic
4. **Handles rate limits** — exponential backoff + full jitter retries
5. **Verifies delivery** — HMAC-SHA256 signed webhooks
6. **Monitors everything** — Prometheus metrics, Grafana dashboards, Alertmanager alerts

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Client                                                      │
│ (curl, SDK, web)                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI App (http://localhost:8000)                        │
├─────────────────────────────────────────────────────────────┤
│ POST /api/campaigns          → Create campaign              │
│ POST /api/campaigns/{id}/publish → Publish to platforms     │
│ POST /api/tokens             → Store encrypted tokens       │
│ POST /api/webhooks/social-delivery → Delivery verification  │
│ GET  /metrics                → Prometheus metrics           │
└────────────────────┬────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
  ┌────────┐    ┌────────┐    ┌──────────┐
  │ SQLite │    │ Redis  │    │ Twitter  │
  │  DB    │    │ Queue  │    │ LinkedIn │
  └────────┘    └───┬────┘    │ Facebook │
                    │         │ (adapters)
                    ▼         └──────────┘
              ┌──────────────┐
              │ RQ Worker    │ (retry_publish)
              │ Process      │
              └──────────────┘

Monitoring Stack (docker-compose.monitoring.yml):
┌─────────────────────────────────────────────────────────────┐
│ Prometheus (localhost:9090) ← scrapes /metrics              │
│                                                              │
│ Alertmanager (localhost:9093) ← fires alerts to Slack/email │
│                                                              │
│ Grafana (localhost:3000) ← visualizes metrics               │
│ ├── Social Campaign Publisher - Retries dashboard           │
│ └── Alerts panel                                            │
└─────────────────────────────────────────────────────────────┘
```

## Features

### ✅ Core Functionality
- **Idempotent Publishing**: composite key (idempotency_key, platform) prevents duplicate posts
- **Smart Retry Logic**: exponential backoff + full jitter + max attempts (configurable)
- **Token Encryption**: AES-GCM encrypted token storage per platform
- **Webhook Verification**: HMAC-SHA256 signature validation
- **Durable Persistence**: SQLite + optional Redis + RQ for job durability

### ✅ Monitoring & Observability
- **Prometheus Metrics**: retry counts, attempt tracking, failure rates
- **Grafana Dashboards**: auto-provisioned, auto-loaded on container start
- **Alertmanager Integration**: multi-receiver routing (Slack, email, etc.)
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Docker Secrets**: secure credential injection in production

### ✅ Security
- **Pre-commit Hooks**: detect secrets before commit (webhook URLs, API keys, SSH keys)
- **CI Secret Scanning**: GitHub Actions runs detect-secrets + heuristic scanner
- **Secrets Baseline**: audited `.secrets.baseline` prevents false positives
- **Environment Isolation**: dev/staging/prod secrets via env vars + Docker secrets

## Quick Start

### Prerequisites
```bash
Python 3.11+, Docker (optional), Git
```

### Step 1: Clone & Setup

```bash
git clone https://github.com/ReignnRule11/social-campaign-publisher.git
cd social-campaign-publisher

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Generate a secure `SECRET_KEY`:

```python
python -c "import os; print('SECRET_KEY=' + os.urandom(32).hex())"
```

Edit `.env`:

```ini
SECRET_KEY=your-32-byte-hex-key
WEBHOOK_SECRET=your-webhook-secret
DATABASE_URL=sqlite:///./dev.db
MAX_RETRIES=5
BASE_BACKOFF_SECONDS=2
```

### Step 3: Initialize Database

```bash
python -c "from app.db import get_engine; from app.models import init_db; init_db(get_engine())"
```

### Step 4: Run Tests

```bash
pytest -v
```

Expected output:
```
tests/test_idempotency.py::test_ensure_idempotent_creates_and_reuses PASSED
tests/test_publish_flow.py::test_publish_with_simulated_429 PASSED
tests/test_webhook.py::test_webhook_valid_and_invalid PASSED
====== 4 passed in 2.34s ======
```

### Step 5: Run the App

```bash
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000 → you should see `{"status": "ok"}`

## API Examples

### 1. Create a Campaign

```bash
curl -X POST "http://127.0.0.1:8000/api/campaigns/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summer Sale 2024",
    "body": "Get 50% off all products this summer!"
  }'
```

Response:
```json
{
  "id": 1,
  "title": "Summer Sale 2024",
  "body": "Get 50% off all products this summer!"
}
```

### 2. Create Encrypted Token for a Platform

```bash
curl -X POST "http://127.0.0.1:8000/api/tokens/" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitter",
    "token": "eJwDAAAAAAA="
  }'
```

Response:
```json
{
  "id": 1,
  "platform": "twitter",
  "token": "encrypted-token-string"
}
```

### 3. Publish to Platform (with Simulated Rate Limit)

```bash
curl -X POST "http://127.0.0.1:8000/api/campaigns/1/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": [
      {
        "platform": "twitter",
        "simulate_429": true,
        "token_id": 1
      }
    ]
  }'
```

Response (rate-limited):
```json
[
  {
    "platform": "twitter",
    "status": "rate_limited",
    "retries": 0,
    "spe_id": 123
  }
]
```

App logs:
```json
{
  "timestamp": "2024-08-02T10:30:45.123Z",
  "level": "INFO",
  "message": "scheduling retry",
  "spe_id": 123,
  "platform": "twitter",
  "retry_count": 1,
  "next_retry_seconds": 2
}
```

### 4. Monitor Retry Progress

Check metrics endpoint:

```bash
curl http://127.0.0.1:8000/metrics | grep scpublisher_retry
```

Example output:
```
# HELP scpublisher_retry_scheduled_total Retries scheduled
# TYPE scpublisher_retry_scheduled_total counter
scpublisher_retry_scheduled_total{method="apscheduler",platform="twitter"} 2.0

# HELP scpublisher_current_retries Current retry count per entry
# TYPE scpublisher_current_retries gauge
scpublisher_current_retries{platform="twitter",spe_id="123"} 1.0

# HELP scpublisher_retry_max_reached_total Retries reached maximum
# TYPE scpublisher_retry_max_reached_total counter
scpublisher_retry_max_reached_total{platform="twitter"} 0.0
```

### 5. Send Delivery Webhook

Compute HMAC-SHA256 signature:

```python
import hmac, hashlib, json, requests

body = {
    "platform_post_id": "tw-123456",
    "status": "delivered"
}

body_bytes = json.dumps(body).encode('utf-8')
sig = 'sha256=' + hmac.new(
    b"your-webhook-secret",
    body_bytes,
    hashlib.sha256
).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Signature": sig
}

response = requests.post(
    "http://127.0.0.1:8000/api/webhooks/social-delivery",
    json=body,
    headers=headers
)
print(response.status_code)  # 200
```

Or with curl:

```bash
BODY='{"platform_post_id":"tw-123456","status":"delivered"}'
SIG="sha256=$(echo -n "$BODY" | openssl dgst -sha256 -hmac 'your-webhook-secret' | awk '{print $2}')"

curl -X POST "http://127.0.0.1:8000/api/webhooks/social-delivery" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```

Response:
```json
{
  "message": "Delivery confirmed",
  "platform_post_id": "tw-123456"
}
```

## Monitoring & Dashboards

### View Prometheus Metrics

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Visit Prometheus
open http://localhost:9090

# Query: sum(rate(scpublisher_retry_scheduled_total[5m])) by (method)
```

### Access Grafana Dashboard

```
URL: http://localhost:3000
Username: admin
Password: admin (default, change in production!)

Dashboard: Social Campaign Publisher - Retries
├── Retry jobs scheduled (total)
├── Retry attempts (by platform)
├── Retries reached max (failures)
└── Alert status
```

**Dashboard panels:**

1. **Scheduled Retries** — total jobs queued for retry
2. **Retry Attempts** — per-platform attempt counts
3. **Max Retries Reached** — failures after exhausting retries
4. **Alert Status** — Alertmanager integration status

### Configure Alertmanager

Edit `alertmanager.yml` to route alerts to Slack/email:

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: '/run/secrets/slack_webhook'  # Docker secret
        channel: '#alerts'
        title: 'Retry Failure Alert'
```

Then deploy with secrets:

```bash
echo -n "https://hooks.slack.com/services/..." | docker secret create slack_webhook -
docker stack deploy -c docker-compose.yml -c docker-compose.monitoring.yml scp
```

## Secret Management

### Pre-commit Hooks (Local)

Hooks automatically scan staged files before every commit:

```bash
# Install hooks
pip install pre-commit
pre-commit install

# Manual run
pre-commit run --all-files
```

Hooks check for:
- Webhook URLs
- AWS keys
- SSH keys
- High-entropy strings

Example: attempting to commit a secret

```bash
echo "SLACK_WEBHOOK=https://hooks.slack.com/..." >> app/config.py
git add app/config.py
git commit -m "Add Slack webhook"

# Output:
# detect-secrets..FAILED
# Secret detected: Base64 High Entropy String
# Commit aborted.
```

### CI/CD Secret Scanning

GitHub Actions runs automatically on every push/PR:

```
.github/workflows/secret-scan.yml
├── Runs detect-secrets (Yelp ML-based detector)
├── Runs heuristic scanner (regex patterns)
├── Posts PR comments with findings
└── Blocks merge if secrets found
```

### Generate & Audit Baseline

```bash
# Generate baseline (scans repo)
detect-secrets scan > .secrets.baseline

# Audit interactively
detect-secrets audit .secrets.baseline

# Review findings:
# Secret:      1 / 1
# Filename:    prometheus.yml
# Type:        Base64 High Entropy String
# Value:       [redacted]
# Is this valid? [y/n]: n  # Mark as false positive

# Commit audited baseline
git add .secrets.baseline
git commit -m "Add audited detect-secrets baseline"
```

**Note**: `.secrets.baseline` is committed but should only contain false positives. Never commit real secrets.

## Docker Deployment

### Development Setup (Redis + RQ Worker)

```bash
docker-compose up --build
```

Services running:
- App: http://localhost:8000
- Redis: localhost:6379
- RQ Worker: processes publish-retries queue

### Full Stack (App + Monitoring + Alerting)

```bash
docker-compose -f docker-compose.yml \
  -f docker-compose.monitoring.yml \
  up --build
```

Services running:
- App: http://localhost:8000
- Redis: localhost:6379
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093

### Production Deployment

See [SETUP.md](./SETUP.md) for:
- Environment-specific configuration
- Docker secrets management
- Kubernetes deployment
- Scaling considerations

## Documentation

- **[SETUP.md](./SETUP.md)** — Development setup, testing, Docker deployment, troubleshooting
- **[SECURITY.md](./SECURITY.md)** — Secret management, rotation, incident response
- **[MONITORING_README.md](./MONITORING_README.md)** — Prometheus, Grafana, Alertmanager setup
- **[DEMO_CHECKLIST.md](./DEMO_CHECKLIST.md)** — Demo recording steps
- **[EVIDENCE.md](./EVIDENCE.md)** — Test outputs and verification

## Project Structure

```
social-campaign-publisher/
├── app/
│   ├── main.py                 # FastAPI app + startup/shutdown
│   ├── db.py                   # SQLModel engine & session
│   ├── models.py               # Campaign, SocialPostEntry, IdempotencyRecord, TokenStorage
│   ├── api/
│   │   ├── campaign.py         # POST /campaigns, POST /campaigns/{id}/publish
│   │   ├── tokens.py           # CRUD endpoints for encrypted tokens
│   │   └── webhooks.py         # POST /webhooks/social-delivery (HMAC verification)
│   ├── adapters/
│   │   ├── base.py             # SocialPublisher abstract interface
│   │   ├── fake_adapter.py     # FakePlatformPublisher (simulation)
│   │   └── real_adapter.py     # RealPlatformPublisher stub
│   ├── services/
│   │   ├── idempotency.py      # ensure_idempotent (exactly-once semantics)
│   │   ├── publish.py          # publish_campaign service
│   │   ├── worker.py           # retry_publish worker + exponential backoff
│   │   ├── scheduler.py        # APScheduler wrapper + SQLAlchemyJobStore
│   │   └── image_pipeline.py   # Image variant generation stub
│   └── utils/
│       ├── crypto.py           # AES-GCM encryption/decryption
│       ├── logging.py          # JSON formatter + structured logging
│       ├── metrics.py          # Prometheus counters/gauges (no-op fallback)
│       └── webhook.py          # HMAC-SHA256 verification
├── tests/
│   ├── test_idempotency.py
│   ├── test_publish_flow.py
│   ├── test_webhook.py
│   └── test_placeholder.py
├── scripts/
│   └── check_secrets.py        # Heuristic secret scanner
├── docker-compose.yml           # Redis + app + RQ worker
├── docker-compose.monitoring.yml # Prometheus + Grafana + Alertmanager
├── prometheus.yml              # Scrape config
├── prometheus_alerts.yml       # Alert rules
├── alertmanager.yml            # Alert routing
├── grafana_dashboard.json      # Grafana dashboard
├── grafana_datasource.yml      # Auto-provisioning
├── grafana_dashboard_provider.yml
├── requirements.txt
├── .env.example
├── .pre-commit-config.yaml
├── .secrets.baseline
└── README.md
```

## Contributing

1. Clone the repo
2. Create a feature branch
3. Make changes and run tests: `pytest -v`
4. Pre-commit hooks will scan for secrets
5. Push and create a PR
6. GitHub Actions runs secret scanning + tests
7. Merge after approval

## License

MIT
