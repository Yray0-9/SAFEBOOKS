"""Synthetic login limits; no real accounts, hosting services, or credentials."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from safebooks.models import AdminAccount, BookkeeperAccount
from safebooks.services import login_attempt_service as attempts
from safebooks.services.auth_service import _invalid_login_credentials
from safebooks.views import SESSION_ADMIN_ID_KEY, SESSION_BOOKKEEPER_ID_KEY


class LoginAttemptTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.clock = patch.object(attempts, "time", return_value=900)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_pair_limit_normalizes_case_whitespace_and_ipv6(self):
        for _ in range(10):
            self.assertIsNone(attempts.reserve_password_login(" Example@TEST.invalid ", "::1"))
        result = attempts.reserve_password_login("example@test.invalid", "0:0:0:0:0:0:0:1")
        self.assertEqual(result["error_code"], "login_rate_limited")
        self.assertEqual(result["retry_after_seconds"], 300)
        self.assertIsNone(attempts.reserve_password_login("different", "::1"))

    def test_identifier_limit_applies_across_different_origins(self):
        for index in range(30):
            self.assertIsNone(attempts.reserve_password_login("same-identifier", f"192.0.2.{index+1}"))
        self.assertEqual(attempts.reserve_password_login("same-identifier", "198.51.100.1")["error_code"], "login_rate_limited")

    def test_ip_limit_applies_across_identifiers_and_missing_credentials(self):
        for index in range(60):
            self.assertIsNone(attempts.reserve_password_login(f"identifier-{index}", "192.0.2.1"))
        self.assertEqual(attempts.reserve_password_login(None, "192.0.2.1")["error_code"], "login_rate_limited")

    def test_block_ends_at_next_window_and_rejections_do_not_extend_it(self):
        with patch.object(attempts, "time", return_value=1199):
            for _ in range(10):
                self.assertIsNone(attempts.reserve_password_login("window", "192.0.2.1"))
            self.assertEqual(attempts.reserve_password_login("window", "192.0.2.1")["retry_after_seconds"], 1)
        with patch.object(attempts, "time", return_value=1200):
            self.assertIsNone(attempts.reserve_password_login("window", "192.0.2.1"))

    def test_parallel_reservations_cannot_admit_more_than_pair_limit(self):
        with ThreadPoolExecutor(max_workers=16) as workers:
            results = list(workers.map(lambda _: attempts.reserve_password_login("race", "192.0.2.1"), range(40)))
        self.assertEqual(sum(result is None for result in results), 10)

    def test_expiry_race_uses_atomic_add_not_counter_overwrite(self):
        fake_cache = MagicMock()
        fake_cache.add.side_effect = [False, True]
        fake_cache.incr.side_effect = ValueError("expired")
        with patch.object(attempts, "cache", fake_cache):
            self.assertEqual(attempts._increment("synthetic-counter", 10), 1)
        fake_cache.set.assert_not_called()

    def test_incremented_counter_keeps_expiry_and_unconfirmed_expiry_fails_closed(self):
        fake_cache = MagicMock()
        fake_cache.add.return_value = False
        fake_cache.incr.return_value = 2
        fake_cache.touch.return_value = True
        with patch.object(attempts, "cache", fake_cache):
            self.assertEqual(attempts._increment("synthetic-counter", 10), 2)
            fake_cache.touch.assert_called_once_with("synthetic-counter", timeout=10)
            fake_cache.touch.return_value = False
            with self.assertRaises(RuntimeError):
                attempts._increment("synthetic-counter", 10)
        fake_cache.set.assert_not_called()

    def test_keys_are_opaque_and_only_contain_expiring_integer_counters(self):
        with patch.object(attempts.cache, "add", wraps=cache.add) as add:
            self.assertIsNone(attempts.reserve_password_login("private@example.test", "192.0.2.1"))
        self.assertEqual(add.call_count, 3)
        for call in add.call_args_list:
            key, value = call.args
            self.assertNotIn("private@example.test", key)
            self.assertNotIn("192.0.2.1", key)
            self.assertEqual(value, 1)
            self.assertEqual(call.kwargs["timeout"], 301)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LoginSecurityApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "SyntheticLoginOnly#123"
        cls.bookkeeper = BookkeeperAccount.objects.create(
            full_name="Synthetic Login", username="synthetic_login", email="login@example.test",
            password_hash=make_password(cls.password), status=BookkeeperAccount.STATUS_APPROVED,
            email_verified=True,
        )
        cls.admin = AdminAccount.objects.create(
            full_name="Synthetic Admin", email="admin-login@example.test", password_hash=make_password(cls.password),
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.clock = patch.object(attempts, "time", return_value=900)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def login(self, identifier, password="WrongSyntheticOnly#123", **extra):
        return self.client.post(reverse("api_login"), json.dumps({"identifier": identifier, "password": password}), content_type="application/json", **extra)

    def test_unknown_bookkeeper_and_admin_wrong_password_responses_match(self):
        responses = [self.login(identifier) for identifier in ("missing-synthetic", self.bookkeeper.username, self.admin.email)]
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), _invalid_login_credentials())
            self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    def test_inactive_admin_status_is_not_disclosed_with_wrong_password(self):
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])
        self.assertEqual(self.login(self.admin.email).json(), _invalid_login_credentials())
        self.assertEqual(self.login(self.admin.email, self.password).json()["error_code"], "account_inactive")
        self.assertNotIn(SESSION_ADMIN_ID_KEY, self.client.session)

    def test_unknown_account_performs_default_dummy_hash_work(self):
        with patch("safebooks.services.auth_service.make_password", wraps=make_password) as dummy:
            self.assertEqual(self.login("missing-synthetic").json(), _invalid_login_credentials())
        dummy.assert_called_once_with("WrongSyntheticOnly#123")

    def test_blocked_attempt_never_looks_up_or_hashes_even_correct_password(self):
        with patch("safebooks.views.login_user_or_admin", return_value=_invalid_login_credentials()) as authenticate:
            for _ in range(10):
                self.assertEqual(self.login(self.bookkeeper.username).status_code, 200)
            blocked = self.login(self.bookkeeper.username, self.password)
        self.assertEqual(authenticate.call_count, 10)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked["Retry-After"], "300")
        self.assertEqual(blocked["Cache-Control"], "no-store")
        self.assertEqual(blocked.json()["error_code"], "login_rate_limited")
        self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)
        with patch.object(attempts, "time", return_value=1200):
            self.assertTrue(self.login(self.bookkeeper.username, self.password).json()["ok"])

    def test_forwarded_ip_header_cannot_bypass_limits(self):
        for index in range(10):
            self.assertEqual(self.login("spoof-test", HTTP_X_FORWARDED_FOR=f"192.0.2.{index+1}").status_code, 200)
        self.assertEqual(self.login("spoof-test", HTTP_X_FORWARDED_FOR="198.51.100.1").status_code, 429)

    def test_falsy_json_identifier_cannot_bypass_its_string_budget(self):
        for _ in range(10):
            self.assertEqual(self.login(0).status_code, 200)
        self.assertEqual(self.login("0").status_code, 429)

    def test_cache_failure_blocks_login_without_leaking_exception_details(self):
        for method in ("add", "incr", "touch"):
            cache.clear()
            if method != "add":
                attempts.reserve_password_login(self.bookkeeper.username, "127.0.0.1")
            with patch.object(attempts.cache, method, side_effect=RuntimeError("synthetic-private-cache-details")), patch("safebooks.views.login_user_or_admin") as authenticate, self.assertLogs(attempts.logger, level="WARNING") as logs:
                response = self.login(self.bookkeeper.username, self.password)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error_code"], "login_unavailable")
            self.assertNotIn("synthetic-private-cache-details", response.content.decode() + " ".join(logs.output))
            authenticate.assert_not_called()
            self.assertNotIn(SESSION_BOOKKEEPER_ID_KEY, self.client.session)

    def test_missing_fields_still_report_validation_errors_and_malformed_json_is_safe(self):
        self.assertEqual(self.login("", "").json()["error_code"], "missing_credentials")
        response = self.client.post(reverse("api_login"), "[", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Cache-Control"], "no-store")


class SharedLoginAttemptProcessTests(SimpleTestCase):
    def test_two_processes_enforce_the_same_pair_and_ip_budgets(self):
        from fakeredis import TcpFakeServer
        server = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        environment = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC") if key in os.environ}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        script = f"""
import json, socket, sys
original_connect = socket.socket.connect
def only_own_server(sock, address):
    if address != ('127.0.0.1', {port}):
        raise RuntimeError('Only the disposable test cache may be contacted')
    return original_connect(sock, address)
socket.socket.connect = only_own_server
from django.conf import settings
mode, worker = sys.argv[1:]
settings.configure(SECRET_KEY='synthetic-login-limits-only', INSTALLED_APPS=['safebooks'], DATABASES={{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}}}, CACHES={{'default': {{
    'BACKEND': 'django.core.cache.backends.redis.RedisCache',
    'LOCATION': 'redis://127.0.0.1:{port}/0', 'KEY_PREFIX': 'synthetic-login-' + mode,
    'OPTIONS': {{'serializer': 'safebooks.cache.AuthStateJSONSerializer', 'socket_timeout': 3}},
}}}})
import django
django.setup()
from safebooks.services import login_attempt_service as attempts
attempts.time = lambda: 900
count = 10 if mode == 'pair' else 40
admitted = 0
for index in range(count):
    identifier = ' Shared-Identifier ' if mode == 'pair' and worker == '0' else 'shared-identifier' if mode == 'pair' else 'user-' + worker + '-' + str(index)
    result = attempts.reserve_password_login(identifier, '127.0.0.1')
    if result is None:
        admitted += 1
    else:
        assert result['error_code'] == 'login_rate_limited'
print(json.dumps({{'admitted': admitted}}))
"""
        workers = []
        try:
            for mode, maximum in (("pair", 10), ("ip", 60)):
                workers = [subprocess.Popen([sys.executable, "-B", "-c", script, mode, str(index)], cwd=Path(__file__).resolve().parents[2], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for index in range(2)]
                admitted = 0
                for worker in workers:
                    output, error = worker.communicate(timeout=30)
                    self.assertEqual(worker.returncode, 0, error)
                    admitted += json.loads(output)["admitted"]
                self.assertEqual(admitted, maximum)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
