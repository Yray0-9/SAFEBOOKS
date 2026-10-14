"""Synthetic production settings; no real secrets, DB, SMTP, or Redis access."""
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import textwrap
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from safebooks.cache import AuthStateJSONSerializer


class ProductionConfigurationTests(SimpleTestCase):
    def setUp(self):
        # Do not inherit the .env that Django loaded for the main test process.
        self.environment = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC") if key in os.environ}
        self.environment.update({
            "DJANGO_SETTINGS_MODULE": "safebooks.settings_production",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SAFEBOOKS_SECRET_KEY": secrets.token_urlsafe(60),
            "SAFEBOOKS_ALLOWED_HOSTS": "app.example.com,www.example.com",
            "SAFEBOOKS_DB_NAME": "synthetic_database",
            "SAFEBOOKS_DB_USER": "synthetic_user",
            "SAFEBOOKS_DB_PASSWORD": "SyntheticDatabaseOnly#123",
            "SAFEBOOKS_DB_HOST": "db.example.com",
            "SAFEBOOKS_REDIS_URL": "rediss://synthetic-user:synthetic-only@cache.example.com:6380/0",
            "SAFEBOOKS_CACHE_KEY_PREFIX": "synthetic-staging",
            "SAFEBOOKS_EMAIL_HOST": "smtp.example.com",
            "SAFEBOOKS_EMAIL_HOST_USER": "sender@example.com",
            "SAFEBOOKS_EMAIL_HOST_PASSWORD": "SyntheticSMTPOnly#123",
            "SAFEBOOKS_DEFAULT_FROM_EMAIL": "SafeBooks <sender@example.com>",
        })

    def _run(self, source, *, changes=None, unset=(), build_static=False):
        environment = {**self.environment, **(changes or {})}
        for name in unset:
            environment.pop(name, None)
        preamble = "import socket\nsocket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('External connections blocked in configuration tests'))\n"
        if build_static:
            # Run the real production asset build, but never create preview or
            # collected assets in the repository or touch deployment services.
            source = """
import django, tempfile
django.setup()
from django.conf import settings
from django.core.management import call_command
with tempfile.TemporaryDirectory(prefix='safebooks-static-test-') as build_dir:
    settings.STATIC_ROOT = build_dir
    call_command('collectstatic', interactive=False, verbosity=0)
""" + textwrap.indent(source, "    ")
        return subprocess.run([sys.executable, "-B", "-c", preamble + source], cwd=Path(__file__).resolve().parents[2], env=environment, capture_output=True, text=True, timeout=30)

    def _assert_rejected(self, *, changes=None, unset=(), expected):
        result = self._run("import safebooks.settings_production", changes=changes, unset=unset)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        # Startup errors must name settings, never reveal connection values.
        for key in ("SAFEBOOKS_SECRET_KEY", "SAFEBOOKS_DB_PASSWORD", "SAFEBOOKS_REDIS_URL", "SAFEBOOKS_EMAIL_HOST_PASSWORD"):
            self.assertNotIn(self.environment[key], result.stderr)

    def test_valid_configuration_uses_secure_shared_state_and_never_local_env(self):
        result = self._run("""
import json, django
django.setup()
from django.conf import settings as s
print(json.dumps({
 'debug': s.DEBUG, 'database': s.DATABASES['default']['ENGINE'],
 'database_name': s.DATABASES['default']['NAME'], 'sslmode': s.DATABASES['default']['OPTIONS']['sslmode'],
 'cache': s.CACHES['default']['BACKEND'], 'serializer': s.CACHES['default']['OPTIONS']['serializer'],
 'certificate_validation': s.CACHES['default']['OPTIONS']['ssl_cert_reqs'],
 'session': s.SESSION_ENGINE, 'cookies': [s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SESSION_COOKIE_HTTPONLY],
 'csrf_readable': not s.CSRF_COOKIE_HTTPONLY, 'redirect': s.SECURE_SSL_REDIRECT,
 'hosts': s.ALLOWED_HOSTS, 'origins': s.CSRF_TRUSTED_ORIGINS,
 'proxy': s.SECURE_PROXY_SSL_HEADER, 'google': bool(s.SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID),
 'static_storage': s.STORAGES['staticfiles']['BACKEND'], 'email': s.EMAIL_BACKEND,
 'email_timeout': s.EMAIL_TIMEOUT,
}))
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["debug"])
        self.assertEqual(data["database"], "django.db.backends.postgresql")
        self.assertEqual(data["database_name"], "synthetic_database")
        self.assertEqual(data["sslmode"], "require")
        self.assertEqual(data["cache"], "django.core.cache.backends.redis.RedisCache")
        self.assertEqual(data["serializer"], "safebooks.cache.AuthStateJSONSerializer")
        self.assertEqual(data["certificate_validation"], "required")
        self.assertEqual(data["session"], "django.contrib.sessions.backends.db")
        self.assertEqual(data["cookies"], [True, True, True])
        self.assertTrue(data["csrf_readable"])
        self.assertTrue(data["redirect"])
        self.assertIsNone(data["proxy"])
        self.assertFalse(data["google"])
        self.assertEqual(data["origins"], ["https://app.example.com", "https://www.example.com"])
        self.assertIn("CompressedManifest", data["static_storage"])
        self.assertEqual(data["email"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(data["email_timeout"], 10)

    def test_missing_required_secrets_fail_without_reading_local_env(self):
        for name in ("SAFEBOOKS_SECRET_KEY", "SAFEBOOKS_ALLOWED_HOSTS", "SAFEBOOKS_DB_NAME", "SAFEBOOKS_DB_USER", "SAFEBOOKS_DB_PASSWORD", "SAFEBOOKS_DB_HOST", "SAFEBOOKS_REDIS_URL", "SAFEBOOKS_CACHE_KEY_PREFIX", "SAFEBOOKS_EMAIL_HOST", "SAFEBOOKS_EMAIL_HOST_USER", "SAFEBOOKS_EMAIL_HOST_PASSWORD", "SAFEBOOKS_DEFAULT_FROM_EMAIL"):
            with self.subTest(setting=name):
                self._assert_rejected(unset=(name,), expected=name)

    def test_unsafe_signing_keys_are_rejected(self):
        for value in ("short", "x" * 70, "django-insecure-" + "abcdefghijklmnop" * 5):
            with self.subTest(kind=len(value)):
                self._assert_rejected(changes={"SAFEBOOKS_SECRET_KEY": value}, expected="strong, random")

    def test_production_cannot_enable_debug_or_disable_https(self):
        for name, value in (("SAFEBOOKS_DEBUG", "1"), ("SAFEBOOKS_SESSION_COOKIE_SECURE", "0"), ("SAFEBOOKS_CSRF_COOKIE_SECURE", "0"), ("SAFEBOOKS_SECURE_SSL_REDIRECT", "0"), ("SAFEBOOKS_USE_POSTGRESQL", "0")):
            with self.subTest(setting=name):
                self._assert_rejected(changes={name: value}, expected="Production")

    def test_host_validation_and_csrf_allowlist_reject_unsafe_values(self):
        for value in ("*", ".example.com", "https://app.example.com", "app.example.com/path", "app.example.com:8000", "app.example.com,"):
            with self.subTest(host=value):
                self._assert_rejected(changes={"SAFEBOOKS_ALLOWED_HOSTS": value}, expected="exact hostnames")
        for value in ("http://app.example.com", "https://*.example.com", "https://other.example.com", "https://app.example.com/path", "https://app.example.com:8443"):
            with self.subTest(origin=value):
                self._assert_rejected(changes={"SAFEBOOKS_CSRF_TRUSTED_ORIGINS": value}, expected="HTTPS origins")

    def test_cache_requires_single_tls_endpoint_without_security_overrides(self):
        for value in ("redis://cache.example.com/0", "https://cache.example.com", "rediss:///0", "rediss://cache.example.com/0", "rediss://cache.example.com/0?ssl_cert_reqs=none", "rediss://cache.example.com/0,rediss://replica.example.com/0", "rediss://cache.example.com:bad/0", "rediss://cache.example.com/not-a-db"):
            with self.subTest(kind=value.split(":", 1)[0]):
                self._assert_rejected(changes={"SAFEBOOKS_REDIS_URL": value}, expected="one TLS")
        self._assert_rejected(changes={"SAFEBOOKS_CACHE_KEY_PREFIX": "invalid prefix"}, expected="environment-specific")

    def test_database_smtp_and_numeric_configuration_fail_closed(self):
        cases = (
            ({"SAFEBOOKS_DB_SSLMODE": "disable"}, "PostgreSQL"),
            ({"SAFEBOOKS_EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"}, "SMTP"),
            ({"SAFEBOOKS_EMAIL_USE_TLS": "0", "SAFEBOOKS_EMAIL_USE_SSL": "0"}, "exactly one"),
            ({"SAFEBOOKS_EMAIL_USE_TLS": "1", "SAFEBOOKS_EMAIL_USE_SSL": "1"}, "exactly one"),
            ({"SAFEBOOKS_DEFAULT_FROM_EMAIL": "invalid"}, "valid sender"),
            ({"SAFEBOOKS_DB_PORT": "invalid"}, "integer"),
            ({"SAFEBOOKS_DB_CONN_MAX_AGE": "-1"}, "range"),
            ({"SAFEBOOKS_BOOKKEEPER_TWO_FACTOR_LOGIN_MAX_ATTEMPTS": "0"}, "range"),
            ({"SAFEBOOKS_TRUST_PROXY_PROTO": "typo"}, "boolean"),
        )
        for change, message in cases:
            with self.subTest(setting=next(iter(change))):
                self._assert_rejected(changes=change, expected=message)

    def test_google_configuration_is_optional_but_complete_and_https_when_enabled(self):
        self._assert_rejected(changes={"SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID": "synthetic-google-id"}, expected="SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET")
        config = {"SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID": "synthetic-google-id", "SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET": "synthetic-google-secret", "SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI": "https://app.example.com/auth/google/callback/"}
        result = self._run("import safebooks.settings_production", changes=config)
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in ("http://app.example.com/auth/google/callback/", "https://other.example.com/auth/google/callback/", "https://app.example.com/incorrect/"):
            with self.subTest(kind=value.split(":", 1)[0]):
                self._assert_rejected(changes={**config, "SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI": value}, expected="Google OAuth redirect")

    def test_https_redirect_headers_login_and_csrf_work_without_database_access(self):
        result = self._run("""
import django
django.setup()
from django.test import Client
from django.core.checks import run_checks
client = Client(enforce_csrf_checks=True)
issues = run_checks(include_deployment_checks=True)
assert {issue.id for issue in issues} == {'security.W004'}, [issue.id for issue in issues]
http = client.get('/login/', HTTP_HOST='app.example.com')
assert http.status_code == 301 and http['Location'] == 'https://app.example.com/login/'
https = client.get('/login/', HTTP_HOST='app.example.com', secure=True)
assert https.status_code == 200
assert https['X-Content-Type-Options'] == 'nosniff'
assert https['X-Frame-Options'] == 'DENY'
assert https.cookies['csrftoken']['secure']
assert not https.cookies['csrftoken']['httponly']
from django.contrib.staticfiles.storage import staticfiles_storage
asset_url = staticfiles_storage.url('images/favicon.ico')
assert asset_url.startswith('/static/') and asset_url != '/static/images/favicon.ico'
asset = client.get(asset_url, HTTP_HOST='app.example.com', secure=True)
assert asset.status_code == 200 and asset['X-Content-Type-Options'] == 'nosniff'
asset.close()
favicon = client.get('/favicon.ico', HTTP_HOST='app.example.com', secure=True)
assert favicon.status_code == 302 and favicon['Location'] == asset_url
rejected = client.post('/api/auth/login/', '{}', content_type='application/json', HTTP_HOST='app.example.com', secure=True)
assert rejected.status_code == 403
untrusted = client.get('/login/', HTTP_HOST='app.example.com', HTTP_X_FORWARDED_PROTO='https')
assert untrusted.status_code == 301
bad_host = client.get('/login/', HTTP_HOST='attacker.example.net', secure=True)
assert bad_host.status_code == 400
print('PASS')
""", build_static=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_proxy_trust_is_explicit_and_gunicorn_does_not_use_runserver(self):
        result = self._run("""
import django, runpy
django.setup()
from django.conf import settings
from django.test import Client
assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
assert Client().get('/login/', HTTP_HOST='app.example.com', HTTP_X_FORWARDED_PROTO='https').status_code == 200
config = runpy.run_path('gunicorn.conf.py')
assert config['raw_env'] == ['DJANGO_SETTINGS_MODULE=safebooks.settings_production']
assert config['worker_class'] == 'gthread' and config['accesslog'] is None
assert config['workers'] == 1 and config['threads'] == 2
print('PASS')
""", changes={"SAFEBOOKS_TRUST_PROXY_PROTO": "1"}, build_static=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class AuthCacheSerializerTests(SimpleTestCase):
    def test_round_trips_all_existing_auth_state_types_and_atomic_integer_format(self):
        serializer = AuthStateJSONSerializer()
        for value in (1, 0, True, False, None, "synthetic", 1760000000.5, {"hash": "synthetic-hash", "expires_at": 1760000000.5}, {"account_id": 1, "authorization_digest": "synthetic-digest", "session_version": 0, "password_hash": "synthetic-hash", "expires_at": 1760000000.5}):
            dumped = serializer.dumps(value)
            if type(value) is int:
                self.assertIs(type(dumped), int)
                dumped = str(dumped).encode()
            self.assertEqual(serializer.loads(dumped), value)
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            serializer.loads(b"\x80\x04pickle-not-json")
        with self.assertRaises(ValueError):
            serializer.dumps(float("nan"))


class SharedAuthStateProcessTests(SimpleTestCase):
    def test_separate_worker_processes_share_values_and_atomic_counters(self):
        try:
            from fakeredis import TcpFakeServer
        except ImportError:
            self.skipTest("Install requirements-dev.txt for the isolated Redis-protocol integration test.")
        from django.core.cache.backends.redis import RedisCache

        # Own disposable loopback server only. This emulates Redis protocol;
        # real hosted Redis/TLS and capacity must still be verified on staging.
        server = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        address, port = server.server_address
        cache_url = f"redis://{address}:{port}/0"
        parameters = {"KEY_PREFIX": "synthetic-workers", "OPTIONS": {"serializer": "safebooks.cache.AuthStateJSONSerializer", "socket_timeout": 3, "socket_connect_timeout": 3}}
        shared = RedisCache(cache_url, parameters)
        environment = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC") if key in os.environ}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        script = f"""
import socket
original_connect = socket.socket.connect
def only_own_server(sock, address):
    if address != ('127.0.0.1', {port}):
        raise RuntimeError('Only the disposable protocol emulator may be contacted')
    return original_connect(sock, address)
socket.socket.connect = only_own_server
from django.core.cache.backends.redis import RedisCache
cache = RedisCache({cache_url!r}, {parameters!r})
"""
        try:
            first = subprocess.run([sys.executable, "-B", "-c", script + "cache.set('reset-grant', {'account_id': 1, 'session_version': 0, 'authorization_digest': 'synthetic-only'}, 30)\nassert cache.add('attempts', 0, 30)\n"], cwd=Path(__file__).resolve().parents[2], env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run([sys.executable, "-B", "-c", script + "assert cache.get('reset-grant')['authorization_digest'] == 'synthetic-only'\nassert not cache.add('attempts', 0, 30)\n"], cwd=Path(__file__).resolve().parents[2], env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 0, second.stderr)
            workers = [subprocess.Popen([sys.executable, "-B", "-c", script + "for _ in range(50):\n    cache.incr('attempts')\n"], cwd=Path(__file__).resolve().parents[2], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
            for worker in workers:
                try:
                    output, error = worker.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.communicate()
                    self.fail("Disposable worker timed out")
                self.assertEqual(worker.returncode, 0, error)
            self.assertEqual(shared.get("attempts"), 100)
            self.assertEqual(shared.get("reset-grant")["account_id"], 1)
        finally:
            shared._cache.get_client(write=True).connection_pool.disconnect()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


@override_settings(DEBUG=False, SETTINGS_MODULE="safebooks.settings_production")
class DeploymentServiceProbeTests(SimpleTestCase):
    def test_probe_only_selects_one_and_touches_its_own_expiring_key(self):
        fake_connection = MagicMock()
        fake_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
        fake_cache = MagicMock()
        fake_cache.add.return_value = True
        fake_cache.get.return_value = 1
        fake_cache.incr.return_value = 2
        with patch("safebooks.management.commands.check_deployment_services.connection", fake_connection), patch("safebooks.management.commands.check_deployment_services.cache", fake_cache):
            output = io.StringIO()
            call_command("check_deployment_services", stdout=output)
        fake_connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1")
        key = fake_cache.add.call_args.args[0]
        self.assertTrue(key.startswith("deployment-probe:"))
        self.assertEqual(fake_cache.add.call_args.kwargs, {"timeout": 30})
        fake_cache.delete.assert_called_once_with(key)
        fake_cache.clear.assert_not_called()
        self.assertIn("passed", output.getvalue())

    def test_service_failures_do_not_expose_connection_details_or_use_fallback(self):
        for failure in ("database", "redis"):
            fake_connection = MagicMock()
            fake_connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            fake_cache = MagicMock()
            if failure == "database":
                fake_connection.cursor.side_effect = RuntimeError("synthetic-private-connection")
            else:
                fake_cache.add.side_effect = RuntimeError("synthetic-private-connection")
            with patch("safebooks.management.commands.check_deployment_services.connection", fake_connection), patch("safebooks.management.commands.check_deployment_services.cache", fake_cache):
                with self.assertRaises(CommandError) as error:
                    call_command("check_deployment_services")
            self.assertNotIn("synthetic-private-connection", str(error.exception))
            fake_cache.clear.assert_not_called()

    @override_settings(DEBUG=True, SETTINGS_MODULE="safebooks.settings")
    def test_probe_refuses_local_development_mode(self):
        with self.assertRaises(CommandError):
            call_command("check_deployment_services")
