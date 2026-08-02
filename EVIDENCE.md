EVIDENCE — Social Campaign Publisher Capstone

1) Automated tests (idempotency, publish flow, webhook verification)
$ pytest -q
4 passed, 11 warnings

2) Key proofs (examples):
- Idempotency: tests/test_idempotency.py shows ensure_idempotent created and reused a record
- Rate-limit handling: tests/test_publish_flow.py simulates adapter returning rate_limited and verifies SocialPostEntry recorded and retry scheduling logic (manual demo also available)
- Webhook trust: tests/test_webhook.py demonstrates forged webhook rejected (400) and valid webhook updates status to published

Run these locally as in README to reproduce the test outputs above.
