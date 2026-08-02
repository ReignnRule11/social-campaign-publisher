import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # include structured extras if provided via record.__dict__
        for k in ("campaign_id", "spe_id", "platform", "attempts", "retry_after", "method"):
            v = record.__dict__.get(k)
            if v is not None:
                data[k] = v
        # include any explicit extra_fields dict
        extra = record.__dict__.get("extra_fields")
        if isinstance(extra, dict):
            data.update(extra)
        return json.dumps(data)


def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if not getattr(root, "_structured", False):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        # remove default handlers to avoid duplicate console lines in some test harnesses
        for h in list(root.handlers):
            root.removeHandler(h)
        root.addHandler(handler)
        root.setLevel(level)
        root._structured = True


def get_logger(name: str = __name__):
    setup_logging()
    return logging.getLogger(name)
