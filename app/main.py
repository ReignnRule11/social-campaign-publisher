import os

from fastapi import Depends, FastAPI, Response

from app.api.campaign import router as campaign_router
from app.api.tokens import router as tokens_router
from app.api.webhooks import router as webhooks_router
from app.db import get_engine
from app.models import init_db
from app.security import require_api_key
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.utils.metrics import metrics_response

app = FastAPI(title="Social Campaign Publisher Capstone")

# Management APIs require a shared staging API key. Delivery webhooks remain
# independently protected by HMAC and are not covered by this dependency.
app.include_router(campaign_router, prefix="/api/campaigns", dependencies=[Depends(require_api_key)])
app.include_router(tokens_router, prefix="/api/tokens", dependencies=[Depends(require_api_key)])
app.include_router(webhooks_router, prefix="/api/webhooks")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    data, content_type = metrics_response()
    return Response(content=data, media_type=content_type)


@app.on_event("startup")
def startup_event():
    init_db(get_engine())
    if os.getenv("ENABLE_SCHEDULER", "true").lower() in {"1", "true", "yes"}:
        start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    if os.getenv("ENABLE_SCHEDULER", "true").lower() in {"1", "true", "yes"}:
        shutdown_scheduler()


@app.get("/")
async def root():
    return {"status": "ok", "service": "social-campaign-publisher"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
