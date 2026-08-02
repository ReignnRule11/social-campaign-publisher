Social Campaign Publisher — Python FastAPI scaffold

This workspace contains an initial scaffold for the FlyRank capstone (Python + FastAPI + SQLite).

Quick start (local):

1. Create a virtual environment: python -m venv .venv
2. Activate it: .\.venv\Scripts\Activate.ps1 (PowerShell) or .\.venv\Scripts\activate
3. Install deps: pip install -r requirements.txt
4. Run tests: pytest -q
5. Run the app: uvicorn app.main:app --reload

What was created: minimal FastAPI app, basic models, image pipeline stub, scheduler, adapters, idempotency, worker, webhook verification, tests, and a plan.md in the session state.

Demo steps (retry & webhook flows)

1. Start the app: uvicorn app.main:app --reload
2. Create a campaign:
   curl -X POST "http://127.0.0.1:8000/api/campaigns/" -H "Content-Type: application/json" -d '{"title": "Hello", "body": "Content"}'
3. (Optional) Create an encrypted token for a platform:
   curl -X POST "http://127.0.0.1:8000/api/tokens/" -H "Content-Type: application/json" -d '{"platform": "x", "token": "fake-token"}'
   The endpoint returns a token id you can pass to the publish endpoint as token_id.
4. Trigger publish while simulating a rate limit (adapter will return rate_limited):
   curl -X POST "http://127.0.0.1:8000/api/campaigns/{id}/publish" -H "Content-Type: application/json" -d '{"platforms": [{"platform": "x", "simulate_429": true}] }'
   The worker records a SocialPostEntry with status "rate_limited" and schedules retries.
5. Observe scheduled retries: scheduler runs in-process; with JOBSTORE_URL set the retries survive restarts.

Prometheus metrics

- The app exposes /metrics (Prometheus format). Install prometheus_client in your environment.
- Useful metrics:
  - scpublisher_retry_scheduled_total{method,platform}
  - scpublisher_retry_attempts_total{platform}
  - scpublisher_retry_failures_total{platform}
  - scpublisher_retry_max_reached_total{platform}
  - scpublisher_current_retries{spe_id,platform}

RQ & Docker demo

- An example docker-compose.yml is included to bring up Redis, the app, and an RQ worker for durable retries.
- To run the full demo with Redis and RQ:
  1. Copy docker-compose.yml and set SECRET_KEY, WEBHOOK_SECRET in the environment variables under the app service or override via .env.
  2. docker-compose up --build
  3. The app will be available on http://localhost:8000 and metrics on http://localhost:8000/metrics
  4. The RQ worker will listen for publish-retries and process enqueued retry jobs.

Monitoring tips

- Scrape /metrics from Prometheus and create dashboards for retry counts and failed jobs.
- If using RQ, use rq-dashboard for visibility into queued/done/failed jobs.

6. Send delivery webhook (valid signature):
   - Compute HMAC-SHA256 over the JSON body with WEBHOOK_SECRET and send header X-Signature: sha256=<hex>
   - Example (Python):
       import hmac, hashlib, json
       body = json.dumps({"platform_post_id": "<id>", "status": "delivered"}).encode('utf-8')
       sig = 'sha256=' + hmac.new(b"your-webhook-secret", body, hashlib.sha256).hexdigest()
       # POST to /api/webhooks/social-delivery with header X-Signature: sig
7. Check SocialPostEntry status flips to "published" after a valid webhook; a forged signature returns 400 and leaves status unchanged.

EVIDENCE.md contains test outputs and pointers to verify behavior.
