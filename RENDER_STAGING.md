# Render zero-cost staging deployment

This Blueprint targets **$0/month Render compute** using one Free web service
and one Free PostgreSQL database. It deliberately does not provision a
background worker, Redis/Key Value, paid compute, or persistent disk.

## Free-tier constraints

- Free web services spin down after 15 minutes without inbound traffic and
  can take about a minute to wake. Their local filesystem is ephemeral.
- Free Render Postgres is limited to 1 GB, has no backups, and expires 30 days
  after creation. After expiry, there is a 14-day upgrade grace period before
  Render deletes the database and its data.
- Free web services can be restarted at any time. Do not treat this as
  production hosting or store real customer data.
- Render's free usage includes limits on instance hours, bandwidth, and build
  pipeline minutes. Usage beyond included amounts may suspend services when
  no payment method is on file; a payment method can result in overage charges.
- The workspace must remain within its included free usage for this to stay
  at $0. Review the Render dashboard's usage and billing before applying.

## Deployment

1. Connect this repository to Render.
2. Create a Blueprint from the branch containing `render.yaml`.
3. Confirm the proposed web service and database are both on the **Free** plan.
4. Confirm there are no worker, Key Value, disk, or paid resources in the
   Blueprint preview before applying.
5. Record the database creation date and export any staging data before day 30.

## Configuration

The Blueprint generates `SECRET_KEY`, `WEBHOOK_SECRET`, and
`APP_API_KEY`. Keep these values in Render; never commit them to GitHub.

The API uses `APP_ENV=production`, which requires `APP_API_KEY` for campaign
and token-management routes. Send it in the `X-API-Key` request header.
Delivery webhooks remain independently protected by the HMAC signature and
`WEBHOOK_SECRET`.

Redis/RQ is intentionally not configured. The application therefore uses
APScheduler in the web process for retry scheduling. Because the free web
service sleeps when idle and can restart, scheduled retry execution is
**best-effort only** and is not a reliable background-processing guarantee.
This staging setup is for API, authentication, database, and basic smoke tests,
not load testing or production job processing.

## Smoke tests

- `GET /` returns the service identity.
- `GET /healthz` returns HTTP 200.
- `GET /api/tokens/` without `X-API-Key` returns HTTP 401.
- `GET /api/tokens/` with the generated `X-API-Key` returns HTTP 200.
- Verify campaign create/read and webhook HMAC validation using test data.
- Confirm the scheduler starts in the web-service logs; do not infer reliable
  retry execution from a successful API health check.

## Known functional limitation

The Instagram and X adapters are simulation adapters. A successful simulated
response is not a real social-network post. Real platform publishing,
production-grade durable retries, backups, and formal database migrations
remain separate work.
