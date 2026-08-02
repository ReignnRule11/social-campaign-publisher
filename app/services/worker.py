from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlmodel import Session
from app.db import get_engine
from app.services.publish import _get_adapter
from app.models import SocialPostEntry, Campaign
from app.services.idempotency import ensure_idempotent
from app.services.scheduler import get_scheduler
import os
import random

from app.utils.logging import get_logger
logger = get_logger(__name__)

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
BASE_BACKOFF = int(os.getenv("BASE_BACKOFF_SECONDS", "2"))
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_URI")

# optional RQ queue only used when REDIS_URL is provided
if REDIS_URL:
    try:
        from redis import Redis
        from rq import Queue
        _redis_conn = Redis.from_url(REDIS_URL)
        _rq_queue = Queue("publish-retries", connection=_redis_conn)
        logger.info("using RQ queue for retries", extra={"method": "rq", "queue": "publish-retries"})
    except Exception as e:
        logger.exception("failed to initialize RQ client, falling back to APScheduler", extra={"error": str(e)})
        _rq_queue = None
else:
    _rq_queue = None


def _compute_backoff(attempts: int) -> int:
    # exponential backoff with full jitter: base * 2^attempts, then random between 0 and that
    base = BASE_BACKOFF * (2 ** attempts)
    return random.randint(0, max(1, int(base)))


def retry_publish(campaign_id: int, platform_entry: Dict, idempotency_key: Optional[str], spe_id: int):
    """Worker job to retry a single platform publish for a campaign and update the existing SocialPostEntry.

    platform_entry: {"platform": name, "encrypted_token": <opt>, "simulate_429": <opt>}
    """
    engine = get_engine()
    with Session(engine) as session:
        cam = session.get(Campaign, campaign_id)
        if not cam:
            return
        platform_name = platform_entry.get("platform")
        encrypted_token = platform_entry.get("encrypted_token")
        adapter = _get_adapter(platform_name, encrypted_token)

        composed_key = (idempotency_key or f"campaign-{campaign_id}") + f":{platform_name}"

        def _do_publish():
            payload = {"id": cam.id, "title": cam.title, "body": cam.body}
            if platform_entry.get("simulate_429"):
                payload["simulate_429"] = True
            return adapter.publish(payload, idempotency_key=composed_key)

        res, created = ensure_idempotent(session, composed_key, platform_name, _do_publish)

        # update existing SocialPostEntry with new status and metadata
        spe = session.get(SocialPostEntry, spe_id)
        if spe:
            # increment attempts count
            prev_attempts = spe.retries or 0
            spe.retries = prev_attempts + 1
            spe.platform_post_id = res.get("platform_post_id")
            spe.status = "published" if res.get("status") == "ok" else res.get("status")
            spe.metadata_json = res
            session.add(spe)
            session.commit()
            session.refresh(spe)
            # metrics: attempt executed
            try:
                from app.utils.metrics import retry_attempts_total, current_retries
                retry_attempts_total.labels(platform=platform_name).inc()
                current_retries.labels(spe_id=str(spe.id), platform=platform_name).set(spe.retries)
            except Exception:
                pass
            logger.info("updated SocialPostEntry after publish attempt",
                        extra={"campaign_id": cam.id, "spe_id": spe.id, "platform": platform_name, "attempts": spe.retries})

        # If still rate_limited and a retry_after is given, schedule another retry with exponential backoff and max attempts
        if res.get("status") == "rate_limited":
            attempts = spe.retries if spe else 0
            if attempts < MAX_RETRIES:
                # prefer server-supplied retry_after when present, otherwise compute backoff
                retry_after = int(res.get("retry_after")) if res.get("retry_after") else _compute_backoff(attempts)
                # add jitter / floor
                retry_after = max(1, int(retry_after))
                logger.info("scheduling retry", extra={"campaign_id": cam.id, "spe_id": spe.id if spe else None, "platform": platform_name, "attempts": attempts, "retry_after": retry_after})

                # metrics: scheduled
                try:
                    from app.utils.metrics import retry_scheduled_total
                    method = "rq" if _rq_queue else "apscheduler"
                    retry_scheduled_total.labels(method=method, platform=platform_name).inc()
                except Exception:
                    pass

                if _rq_queue:
                    # schedule job in RQ to run after retry_after seconds
                    try:
                        from datetime import timedelta as _td
                        _rq_queue.enqueue_in(_td(seconds=retry_after), retry_publish, campaign_id, platform_entry, idempotency_key, spe_id)
                        logger.info("enqueued retry job to RQ", extra={"campaign_id": cam.id, "spe_id": spe.id, "method": "rq", "retry_in": retry_after})
                    except Exception as e:
                        logger.exception("failed to enqueue RQ job, falling back to APScheduler", extra={"error": str(e)})
                        sched = get_scheduler()
                        run_at = datetime.utcnow() + timedelta(seconds=retry_after)
                        sched.add_job(retry_publish, 'date', run_date=run_at, args=[campaign_id, platform_entry, idempotency_key, spe_id])
                else:
                    run_at = datetime.utcnow() + timedelta(seconds=retry_after)
                    sched = get_scheduler()
                    sched.add_job(retry_publish, 'date', run_date=run_at, args=[campaign_id, platform_entry, idempotency_key, spe_id])
            else:
                # mark failed permanently
                if spe:
                    spe.status = "failed"
                    session.add(spe)
                    session.commit()
                    logger.warning("social post entry reached max retries and is marked failed",
                                   extra={"campaign_id": cam.id, "spe_id": spe.id, "platform": platform_name, "attempts": spe.retries})
                    try:
                        from app.utils.metrics import retry_max_reached_total
                        retry_max_reached_total.labels(platform=platform_name).inc()
                    except Exception:
                        pass
