from fastapi import FastAPI
from app.api.campaign import router as campaign_router
from app.api.tokens import router as tokens_router
from app.api.webhooks import router as webhooks_router
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.db import get_engine
from app.models import init_db

app = FastAPI(title="Social Campaign Publisher Capstone")

app.include_router(campaign_router, prefix="/api/campaigns")
app.include_router(tokens_router, prefix="/api/tokens")
app.include_router(webhooks_router, prefix="/api/webhooks")

# prometheus metrics endpoint
from fastapi import Response
from app.utils.metrics import metrics_response


@app.get("/metrics")
async def metrics():
    data, content_type = metrics_response()
    return Response(content=data, media_type=content_type)


@app.on_event("startup")
def startup_event():
    # ensure DB tables exist and start background scheduler
    engine = get_engine()
    init_db(engine)
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()


@app.get("/")
async def root():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
