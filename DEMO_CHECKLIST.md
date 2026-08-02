Demo checklist: Retry & webhook flows

1. Prepare environment
   - Set DATABASE_URL to a writable SQLite or Postgres DB
   - (Optional) Set REDIS_URL to a running Redis instance for durable retries
   - Set SECRET_KEY and WEBHOOK_SECRET in env

2. Start services
   - If using REDIS_URL: start redis-server and an RQ worker:
       rq worker publish-retries
   - Start the FastAPI app (uvicorn app.main:app)

3. Create a campaign and token
   - POST /api/campaigns to create a campaign
   - POST /api/tokens to create an encrypted token (if testing real adapter)

4. Trigger publish
   - POST /api/campaigns/{id}/publish with simulate_429 for a platform to force retry behavior

5. Observe retries
   - If REDIS_URL set: watch the RQ worker logs (should process scheduled job)
   - If not: watch app logs for APScheduler scheduling and execution
   - Verify SocialPostEntry.retries increments and final status updates

6. Webhook verification
   - Send a signed POST to /api/webhooks/social-delivery with X-Signature header
   - Observe entry status change to published/failed

7. Evidence
   - Capture logs that show attempts, retry scheduling method (rq vs apscheduler), and eventual delivery

Notes
- Use the demo script scripts/demo.py to quickly enqueue a retry job. If REDIS_URL is set it will enqueue to RQ, otherwise it will schedule via APScheduler.
