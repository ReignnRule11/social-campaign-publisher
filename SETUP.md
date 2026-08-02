# Setup & Development Guide

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Pre-commit Hooks](#pre-commit-hooks)
3. [Running Tests](#running-tests)
4. [Docker Deployment](#docker-deployment)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Secret Management](#secret-management)
7. [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites
- Python 3.11+
- Docker & docker-compose (for full stack)
- Redis (optional, for durable RQ queue)
- Git

### Step 1: Clone & Environment Setup

```bash
git clone https://github.com/ReignnRule11/social-campaign-publisher.git
cd social-campaign-publisher
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Configure Environment

Copy `.env.example` and customize:

```bash
cp .env.example .env
```

Example `.env` for local development:

```
DATABASE_URL=sqlite:///./dev.db
SECRET_KEY=your-32-byte-secret-key-here
WEBHOOK_SECRET=your-webhook-secret
MAX_RETRIES=5
BASE_BACKOFF_SECONDS=2
REDIS_URL=redis://localhost:6379/0
```

To generate a secure SECRET_KEY:

```python
import os
key = os.urandom(32).hex()
print(f"SECRET_KEY={key}")
```

### Step 3: Initialize Database

```bash
python -c "from app.db import get_engine; from app.models import init_db; init_db(get_engine())"
```

### Step 4: Run Tests

```bash
export SECRET_KEY="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
export WEBHOOK_SECRET="webhook-secret"
pytest -v
```

Expected output:
```
tests/test_idempotency.py::test_ensure_idempotent_creates_and_reuses PASSED
tests/test_publish_flow.py::test_publish_with_simulated_429 PASSED
tests/test_webhook.py::test_webhook_valid_and_invalid PASSED
tests/test_placeholder.py::test_placeholder PASSED

====== 4 passed in 2.34s ======
```

### Step 5: Run the App

```bash
uvicorn app.main:app --reload
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Application startup complete
```

Visit http://127.0.0.1:8000 → should return `{"status": "ok"}`

## Pre-commit Hooks

### Install Pre-commit

```bash
pip install pre-commit
pre-commit install
```

### Run Hooks Locally

```bash
# Run all hooks on staged files
pre-commit run --all-files

# Run specific hook
pre-commit run detect-webhook-urls --all-files
pre-commit run detect-secrets --all-files
```

### Example Hook Output

When a secret is detected:

```
detect-webhook-urls.....................................................FAILED
- hook id: detect-webhook-urls
  exit code: 1

Potential webhook URL(s) or secret-like strings detected:
 - alertmanager.yml: /run/secrets/slack_webhook
```

**Note:** This example shows a path (not a real secret) and should pass audit.

## Running Tests

### Full Test Suite

```bash
pytest -v --tb=short
```

### Test Specific Module

```bash
pytest tests/test_publish_flow.py -v
```

### Coverage Report

```bash
pip install pytest-cov
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View in browser
```

## Docker Deployment

### Local Docker Compose (with Redis + RQ worker)

```bash
docker-compose up --build
```

Services:
- **App**: http://localhost:8000
- **Redis**: localhost:6379
- **RQ Worker**: processes publish-retries queue

### Docker Compose with Monitoring

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up --build
```

Additional services:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Alertmanager**: http://localhost:9093

### Example: Deploy & Test Publish Flow

```bash
# 1. Start stack
docker-compose up -d

# 2. Create campaign
curl -X POST "http://localhost:8000/api/campaigns/" \
  -H "Content-Type: application/json" \
  -d '{"title": "Summer Sale", "body": "50% off all products"}'

# Response:
# {"id": 1, "title": "Summer Sale", "body": "50% off all products"}

# 3. Publish to platform with retry simulation
curl -X POST "http://localhost:8000/api/campaigns/1/publish" \
  -H "Content-Type: application/json" \
  -d '{"platforms": [{"platform": "x", "simulate_429": true}]}'

# Response:
# [{"platform": "x", "status": "rate_limited", "retries": 0}]

# 4. Monitor retries in logs
docker logs scp_app | grep "scheduling retry"
docker logs scp_rq_worker | grep "retry_publish"

# 5. View metrics
curl http://localhost:8000/metrics | grep scpublisher_retry
```

## Monitoring & Alerts

### Prometheus Queries

Query retry metrics in Prometheus UI (http://localhost:9090):

```promql
# Total retries scheduled (by method: rq or apscheduler)
sum(rate(scpublisher_retry_scheduled_total[5m])) by (method)

# Current retry attempts per platform
scpublisher_current_retries

# Max retries reached (failures)
sum(scpublisher_retry_max_reached_total) by (platform)
```

### Grafana Dashboard

1. Visit http://localhost:3000
2. Login: admin/admin
3. Dashboard "Social Campaign Publisher - Retries" auto-loads
4. Panels:
   - Retry jobs scheduled (total)
   - Retry attempts (by platform)
   - Retries reached max

### Alertmanager Notification Setup

#### Email Example

Edit `alertmanager.yml`:

```yaml
receivers:
  - name: 'team-email'
    email_configs:
      - to: 'alerts@mycompany.com'
        from: 'alertmanager@mycompany.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'noreply@mycompany.com'
        auth_password: '/run/secrets/smtp_pass'
```

#### Slack Example (Docker Secrets)

```bash
# Create secret locally
echo -n "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX" \
  | docker secret create slack_webhook -

# Update alertmanager.yml to reference it
# Then deploy with Docker Swarm:
docker stack deploy -c docker-compose.yml -c docker-compose.monitoring.yml scp
```

## Secret Management

### Generating & Auditing Baseline

```bash
# Step 1: Install tools
pip install detect-secrets

# Step 2: Scan repository for potential secrets
detect-secrets scan > .secrets.baseline

# Step 3: Audit findings interactively
detect-secrets audit .secrets.baseline

# Sample output:
# Secret:      1 / 1
# Filename:    /path/to/file.py
# Secret Type: Base64 High Entropy String
# Value:       <redacted>
#
# Is this a valid secret? [y/n]: n  # Mark as false positive

# Step 4: Commit baseline
git add .secrets.baseline
git commit -m "Add audited detect-secrets baseline"
```

### Pre-commit Secret Scanning

Local pre-commit hooks run on every commit:

```bash
# Simulate commit with a secret
echo "API_KEY=sk-1234567890abcdef" >> app/config.py
git add app/config.py
git commit -m "Add config"  # This will fail

# Output:
# detect-secrets.............................................................FAILED
# - hook id: detect-secrets
#   exit code: 1
#
# Secrets found in committed files. Aborting commit.

# Fix: remove secret, use environment variable instead
git restore app/config.py
```

### CI/CD Secret Scanning

GitHub Actions runs on every push/PR:

```yaml
# .github/workflows/secret-scan.yml automatically:
# 1. Runs detect-secrets
# 2. Runs heuristic scanner (check_secrets.py)
# 3. Comments on PR if secrets detected
# 4. Blocks merge if scanning fails
```

Example PR comment:

```
Secret scan detected potential secrets:

detect-secrets output:

Secret:      1 / 1
Filename:    alertmanager.yml
Secret Type: Base64 High Entropy String
Value:       <redacted>

heuristic scan output:

No webhook-like URLs detected.
```

## Troubleshooting

### Issue: Tests fail with "table ... has no column"

**Solution:** Re-initialize database

```bash
rm dev.db  # Remove SQLite file
python -c "from app.db import get_engine; from app.models import init_db; init_db(get_engine())"
pytest -v
```

### Issue: RQ worker not processing jobs

**Solution:** Verify Redis is running

```bash
redis-cli ping  # Should return PONG
docker logs scp_redis  # Check Redis logs

# Restart worker
docker-compose down
docker-compose up --build
```

### Issue: Prometheus not scraping metrics

**Solution:** Check Prometheus UI

```
http://localhost:9090/targets
# Ensure 'app' target shows state: UP
```

If DOWN, verify app is reachable:

```bash
curl http://app:8000/metrics  # From inside Prometheus container
```

### Issue: detect-secrets reports false positives

**Solution:** Audit and mark as false positive

```bash
detect-secrets audit .secrets.baseline
# Select [n] for false positives
# Commit updated baseline
```

### Issue: Pre-commit hooks slow (first run)

**Solution:** Hooks install dependencies on first run (cached afterwards)

```bash
# Skip hooks temporarily
git commit --no-verify -m "WIP: debugging"

# Force re-run
pre-commit install --install-hooks
pre-commit run --all-files
```

## Further Reading

- [SECURITY.md](./SECURITY.md) - Secret management best practices
- [MONITORING_README.md](./MONITORING_README.md) - Monitoring & alerting setup
- [DEMO_CHECKLIST.md](./DEMO_CHECKLIST.md) - Demo recording steps
- [EVIDENCE.md](./EVIDENCE.md) - Test outputs & verification
