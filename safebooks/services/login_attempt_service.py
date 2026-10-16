"""Reserve password-login work before lookup/hashing, using shared atomic counters."""
from ipaddress import ip_address
import json
import logging
from time import time

from django.core.cache import cache
from django.utils.crypto import salted_hmac


logger = logging.getLogger(__name__)
WINDOW_SECONDS = 300
PAIR_LIMIT = 10
IDENTIFIER_LIMIT = 30
IP_LIMIT = 60


def _increment(key, timeout):
    # ADD/INCR are atomic on the production Redis primary. Never reset a
    # competitor's counter with SET when expiry races an increment.
    for _ in range(3):
        if cache.add(key, 1, timeout=timeout):
            return 1
        try:
            count = cache.incr(key)
            # Redis's EXISTS/INCR expiry race can recreate an integer without
            # a TTL. Keep it expiring; bucket names prevent sliding lockouts.
            if cache.touch(key, timeout=timeout):
                return count
        except ValueError:
            continue
    raise RuntimeError("Login counter could not be reserved")


def reserve_password_login(identifier, remote_addr):
    """Return a safe denial or None; count all attempts, including successful ones.

    Fixed five-minute windows prevent attempts extending the same block;
    sustained abuse can still fill later windows. Keys contain HMACs, never
    raw identifiers/IPs or any passwords.
    REMOTE_ADDR must be set correctly by the host; untrusted forwarded headers
    are deliberately not used. This never changes account state or sessions.
    """
    # Match the authentication service's string conversion, including falsy
    # JSON values; alternate representations must not bypass a target's budget.
    normalized = str(identifier).strip().casefold()
    try:
        origin = ip_address(str(remote_addr or "")).compressed
    except ValueError:
        origin = "unknown-origin"
    now = int(time())
    bucket, elapsed = divmod(now, WINDOW_SECONDS)
    retry_after = WINDOW_SECONDS - elapsed
    scopes = [("ip", [origin], IP_LIMIT)]
    if normalized:
        scopes.extend([
            ("identifier", [normalized], IDENTIFIER_LIMIT),
            ("pair", [normalized, origin], PAIR_LIMIT),
        ])
    try:
        for scope, values, maximum in scopes:
            digest = salted_hmac(
                "safebooks.password-login", json.dumps([scope, *values]), algorithm="sha256",
            ).hexdigest()
            key = f"safebooks:password-login:{bucket}:{scope}:{digest}"
            if _increment(key, retry_after + 1) > maximum:
                message = f"Too many sign-in attempts. Please wait up to {retry_after} seconds before trying again."
                return {
                    "ok": False, "message": message, "errors": [message],
                    "error_code": "login_rate_limited", "retry_after_seconds": retry_after,
                }
    except Exception as error:
        # Cache failures must not disable the guard or log connection secrets.
        logger.warning("Password login attempt state unavailable (%s).", type(error).__name__)
        message = "Sign-in is temporarily unavailable. Please try again shortly."
        return {
            "ok": False, "message": message, "errors": [message],
            "error_code": "login_unavailable",
        }
    return None
