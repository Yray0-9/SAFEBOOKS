"""Explicit, bounded readiness probe; never run against local development data."""
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Verify production PostgreSQL and shared Redis connectivity without changing application records."

    def handle(self, *args, **options):
        if settings.DEBUG or settings.SETTINGS_MODULE != "safebooks.settings_production":
            raise CommandError("Use --settings=safebooks.settings_production with hosting environment secrets.")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    raise ValueError("Unexpected database response")
        except Exception:
            # Connection exceptions may contain private URLs or credentials.
            raise CommandError("PostgreSQL readiness check failed; inspect hosting connectivity and TLS configuration privately.") from None

        key = f"deployment-probe:{uuid.uuid4().hex}"
        try:
            if not cache.add(key, 1, timeout=30) or cache.get(key) != 1 or cache.incr(key) != 2:
                raise ValueError("Unexpected cache response")
            cache.delete(key)
        except Exception:
            # Never flush shared auth state. A failed probe expires by itself.
            raise CommandError("Redis readiness check failed; inspect hosting connectivity, credentials, TLS, and cache capacity privately.") from None
        self.stdout.write(self.style.SUCCESS("PostgreSQL and shared Redis readiness checks passed. No application records changed."))
