"""Demo script: enqueue a retry job for a simulated publish.

Usage examples:
  - Use APScheduler fallback (no REDIS_URL set): the script will schedule a retry via the in-process scheduler (start app to observe)
  - Use RQ (set REDIS_URL) to enqueue a durable retry job. Start an RQ worker to process the job:
      redis-server &
      rq worker publish-retries
      python demo.py

This script demonstrates scheduling a retry job and prints structured logs to stdout.
"""
import os
from datetime import datetime, timedelta

REDIS_URL = os.getenv("REDIS_URL")

print(f"Demo starting at {datetime.utcnow().isoformat()}Z; REDIS_URL={'set' if REDIS_URL else 'not-set'}")

# Minimal demonstration: enqueue retry_publish to run in ~5 seconds
from app.services.worker import retry_publish

campaign_id = 1
platform_entry = {"platform": "fake-x", "simulate_429": True}
idempotency_key = "demo-1"
spe_id = 1

if REDIS_URL:
    print("Enqueuing to RQ (durable)")
    from redis import Redis
    from rq import Queue
    r = Redis.from_url(REDIS_URL)
    q = Queue("publish-retries", connection=r)
    q.enqueue_in(5, retry_publish, campaign_id, platform_entry, idempotency_key, spe_id)
    print("Enqueued. Start an RQ worker named 'publish-retries' to process it: rq worker publish-retries")
else:
    print("No REDIS_URL: using APScheduler fallback. Ensure the app is running so the scheduler can execute the job.")
    from app.services.scheduler import get_scheduler
    sched = get_scheduler()
    run_at = datetime.utcnow() + timedelta(seconds=5)
    # schedule with the in-process scheduler
    sched.add_job(retry_publish, 'date', run_date=run_at, args=[campaign_id, platform_entry, idempotency_key, spe_id])
    print("Scheduled job in APScheduler; keep the app process running to let it execute.")

print("Demo script finished")
