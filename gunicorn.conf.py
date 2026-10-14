"""Linux hosting entry point. Does not change Windows/local runserver behavior."""
import os


def _integer(name, default, maximum):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        raise RuntimeError(f"{name} must be an integer.") from None
    if not 1 <= value <= maximum:
        raise RuntimeError(f"{name} is outside its supported range.")
    return value


raw_env = ["DJANGO_SETTINGS_MODULE=safebooks.settings_production"]
bind = f"0.0.0.0:{_integer('PORT', 8000, 65535)}"
workers = _integer("WEB_CONCURRENCY", 1, 8)
threads = _integer("SAFEBOOKS_WEB_THREADS", 2, 16)
worker_class = "gthread"
timeout = _integer("SAFEBOOKS_WEB_TIMEOUT_SECONDS", 60, 300)
max_requests = 1000
max_requests_jitter = 100
accesslog = None  # Query strings may contain client-identifying information.
errorlog = "-"
loglevel = "info"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"} if os.environ.get("SAFEBOOKS_TRUST_PROXY_PROTO", "").strip().lower() in {"1", "true", "yes", "on"} else {}
forwarded_allow_ips = os.environ.get("SAFEBOOKS_FORWARDED_ALLOW_IPS", "127.0.0.1,::1")
