"""Account-bound session proofs and durable revocation for custom auth models."""

import json

from django.db.models import F
from django.utils.crypto import constant_time_compare, salted_hmac


def account_session_auth_hash(account) -> str:
    # Like Django's session auth hash, this remains server-side and changes when
    # credentials change. The version also prevents old sessions reviving after
    # deactivation/reactivation or a security setting being changed back.
    state = json.dumps([
        account._meta.label_lower, account.pk, account.password_hash,
        account.session_version, bool(account.two_factor_enabled),
        account.two_factor_secret,
        account.two_factor_confirmed_at.isoformat() if account.two_factor_confirmed_at else "",
    ], separators=(",", ":"))
    return salted_hmac("safebooks.account-session.v1", state, algorithm="sha256").hexdigest()


def session_auth_hash_matches(account, stored_hash) -> bool:
    return (
        isinstance(stored_hash, str)
        and bool(stored_hash)
        and constant_time_compare(stored_hash, account_session_auth_hash(account))
    )


def save_account_security_change(account, update_fields) -> None:
    # Increment in the same UPDATE as the security change, without losing a
    # concurrent increment or relying on a process-local cache for revocation.
    account.session_version = F("session_version") + 1
    account.save(update_fields=[*update_fields, "session_version"])
    account.refresh_from_db(fields=["session_version"])
