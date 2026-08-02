import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        # configure SQLAlchemyJobStore for durable persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url=os.getenv('JOBSTORE_URL', DATABASE_URL))
        }
        _scheduler = BackgroundScheduler(jobstores=jobstores)
    return _scheduler


def start_scheduler():
    sched = get_scheduler()
    if not sched.running:
        sched.start()


def shutdown_scheduler():
    sched = get_scheduler()
    if sched.running:
        sched.shutdown()
