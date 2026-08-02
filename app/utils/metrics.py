try:
    from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
    _PROM_AVAILABLE = True
except Exception:
    # prometheus_client not installed; provide no-op fallbacks so tests don't require it
    _PROM_AVAILABLE = False

    class _NoOp:
        def labels(self, *a, **k):
            return self

        def inc(self, *a, **k):
            return None

        def set(self, *a, **k):
            return None

    def generate_latest():
        return b""

    CONTENT_TYPE_LATEST = "text/plain"
    Counter = lambda *a, **k: _NoOp()
    Gauge = lambda *a, **k: _NoOp()

# Counters
retry_scheduled_total = Counter(
    "scpublisher_retry_scheduled_total",
    "Total retry jobs scheduled",
    ["method", "platform"],
)
retry_attempts_total = Counter(
    "scpublisher_retry_attempts_total",
    "Total retry attempts executed",
    ["platform"],
)
retry_failures_total = Counter(
    "scpublisher_retry_failures_total",
    "Total retry failures",
    ["platform"],
)
retry_max_reached_total = Counter(
    "scpublisher_retry_max_reached_total",
    "Retries that reached MAX_RETRIES and were marked failed",
    ["platform"],
)

# Gauges (optional)
current_retries = Gauge(
    "scpublisher_current_retries",
    "Current retries for an entry (labelled by spe_id)",
    ["spe_id", "platform"],
)


def metrics_response():
    return generate_latest(), CONTENT_TYPE_LATEST
