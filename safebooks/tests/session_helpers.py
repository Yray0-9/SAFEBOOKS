"""Test-only fixtures for sessions whose complete authentication already passed."""

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.services.session_security_service import account_session_auth_hash
from safebooks.views import (
    SESSION_ADMIN_AUTH_HASH_KEY, SESSION_ADMIN_ID_KEY,
    SESSION_BOOKKEEPER_AUTH_HASH_KEY, SESSION_BOOKKEEPER_ID_KEY,
)


def bind_authenticated_session(session):
    for model, id_key, proof_key in (
        (AdminAccount, SESSION_ADMIN_ID_KEY, SESSION_ADMIN_AUTH_HASH_KEY),
        (BookkeeperAccount, SESSION_BOOKKEEPER_ID_KEY, SESSION_BOOKKEEPER_AUTH_HASH_KEY),
    ):
        account = model.objects.filter(pk=session.get(id_key)).first()
        if account is not None:
            session[proof_key] = account_session_auth_hash(account)
