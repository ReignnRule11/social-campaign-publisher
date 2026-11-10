# Render staging deployment

This repository includes a Render Blueprint in `render.yaml` for a staging
API, PostgreSQL database, Redis-compatible Key Value instance, and RQ worker.

## Before creating resources

1. Review service plans and current prices in Render. The background worker
   and Key Value instance may incur charges. Render's free PostgreSQL plan is
   temporary and is not suitable for production data.
2. Connect this GitHub repository to Render and create a Blueprint from the
   branch containing this file.
3. Review the proposed resources before applying the Blueprint.
4. Wait for the web service, database, Key Value instance, and worker to become
   available.

## Configuration

The Blueprint generates `SECRET_KEY`, `WEBHOOK_SECRET`, and
`APP_API_KEY`. Keep these values in Render; do not copy them into GitHub or
commit them to the repository.

The web service uses `APP_ENV=production`, which requires `APP_API_KEY` for
campaign and token-management routes. Send it as the `X-API-Key` request
header. The signed social-delivery webhook remains protected by
`WEBHOOK_SECRET` and its HMAC signature.

The web service disables APScheduler because retries are delegated to the
separate RQ worker. The API and worker share the same database, Redis queue,
and token-encryption key.

## Smoke tests

After deployment:

- `GET /` should return the service identity.
- `GET /healthz` should return HTTP 200.
- `GET /api/tokens/` without `X-API-Key` should return HTTP 401.
- `GET /api/tokens/` with the generated `X-API-Key` should return HTTP 200.
- Check Render logs to confirm the RQ worker connects to Redis and remains
  running.

Do not send real customer data or real social credentials to staging until
access controls, backups, retention, and platform integrations have been
reviewed.

## Known functional limitation

The Instagram and X adapters in this repository are simulation adapters.
A successful simulated response is not a real social-network post. This
staging deployment validates the API, authentication, database, queue, and
worker infrastructure only. Real publishing integrations are a separate
implementation and verification task.
