"""Opt-in synthetic browser/load harness. Never uses .env or a real database.

Not an automatically discovered test. Requires an independently initialized
loopback PostgreSQL cluster whose temporary directory starts safebooks-step9-.
Redis protocol is emulated, not production TLS Redis. Windows WSGI workers are
test servers, not a substitute for hosted Gunicorn/proxy/capacity verification.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import tempfile
from copy import deepcopy
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "safebooks_step9_browser"
FIXTURE_PASSWORD = "SyntheticTestOnly-Step9!"


def configure(args):
    cluster = Path(args.cluster).resolve()
    if not cluster.name.startswith("safebooks-step9-") or not (cluster / "pgdata" / "PG_VERSION").is_file():
        raise RuntimeError("A dedicated temporary PostgreSQL cluster is required")
    if args.port == 5432 or not 1024 <= args.port <= 65535:
        raise RuntimeError("Do not use the existing PostgreSQL port")
    os.environ["DJANGO_SETTINGS_MODULE"] = "safebooks.settings"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from django.conf import settings
    with patch("dotenv.load_dotenv", return_value=False):
        # Force settings initialization while dotenv loading is disabled.
        settings.DEBUG = False
    settings.SECRET_KEY = hashlib.sha256(str(cluster).encode()).hexdigest()
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
    settings.DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": DATABASE,
        "USER": "safebooks_step9", "HOST": "127.0.0.1", "PORT": str(args.port),
        "CONN_MAX_AGE": 0, "OPTIONS": {"connect_timeout": 3},
    }}
    settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
    settings.SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID = ""
    settings.SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET = ""
    settings.CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://127.0.0.1:{args.cache_port}/0",
        "KEY_PREFIX": "synthetic-step9", "OPTIONS": {
            "serializer": "safebooks.cache.AuthStateJSONSerializer",
            "socket_connect_timeout": 3, "socket_timeout": 3,
        },
    }}
    original_connect = socket.socket.connect
    allowed = {("127.0.0.1", args.port), ("127.0.0.1", args.cache_port)}
    allowed.update(("127.0.0.1", port) for port in args.http_ports)

    def only_own_services(sock, address):
        if address not in allowed:
            raise RuntimeError("Only disposable test services may be contacted")
        return original_connect(sock, address)

    socket.socket.connect = only_own_services
    import django
    django.setup()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SHOW data_directory")
        actual = Path(cursor.fetchone()[0]).resolve()
        if actual != cluster / "pgdata":
            raise RuntimeError("Database isolation check failed")
    return allowed


def suite(args, allowed):
    from django.conf import settings
    from django.core.management import call_command
    from fakeredis import TcpFakeServer
    settings.DATABASES["default"]["TEST"]["NAME"] = "test_safebooks_step9_suite"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "step9-suite"}}
    # Functional fixtures only; seed/browser/load modes retain real hashers.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    original_init = TcpFakeServer.__init__
    def register_fake(server, *values, **options):
        original_init(server, *values, **options)
        allowed.add(server.server_address)
    TcpFakeServer.__init__ = register_fake
    call_command("check")
    call_command("makemigrations", check=True, dry_run=True, verbosity=1)
    call_command("test", "safebooks.tests", interactive=False, verbosity=1)


def seed():
    from django.contrib.auth.hashers import make_password
    from django.core.management import call_command
    from django.db import transaction
    from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
    call_command("migrate", interactive=False, verbosity=0)
    if BookkeeperAccount.objects.exists() or Client.objects.exists():
        raise RuntimeError("Seed requires an empty disposable database; it never resets data")
    # Use the real configured password hasher, unlike fast unit-test fixtures.
    password_hash = make_password(FIXTURE_PASSWORD)
    with transaction.atomic():
        for owner_index in range(10):
            owner = BookkeeperAccount.objects.create(
                full_name=f"Synthetic Bookkeeper {owner_index:02}",
                username=f"step9_{owner_index}", email=f"step9-{owner_index}@example.test",
                password_hash=password_hash, status=BookkeeperAccount.STATUS_APPROVED,
                client_details_password_required=owner_index == 0,
                client_record_email_notifications_enabled=False,
            )
            for client_index in range(10):
                client = Client.objects.create(
                    bookkeeper=owner, client_name=f"Synthetic Client {owner_index:02}-{client_index:02}",
                    tin_number=f"{owner_index + 1:03}{client_index + 1:03}000000",
                    trade_name="Synthetic Trading", location="Synthetic Test City",
                    remarks=Client.REMARK_ACTIVE,
                )
                periods = Period.objects.bulk_create([
                    Period(client=client, year=2024 + month // 12, month=month % 12 + 1)
                    for month in range(33)
                ])
                records = FinancialRecord.objects.bulk_create([
                    FinancialRecord(bookkeeper=owner, client=client, period=period,
                                    entry_date=date(period.year, period.month, 15), total_amount="1200.00")
                    for period in periods
                ])
                FinancialRecordLine.objects.bulk_create([
                    FinancialRecordLine(record=record, type_code=kind, amount=amount,
                                        description="Synthetic fixture", sort_order=order)
                    for record in records
                    for order, kind, amount in ((0, "Sales", "1000.00"), (1, "Expenses", "200.00"))
                ])
    print("Seeded: 10 synthetic owners, 100 clients, 3300 records, 6600 details", flush=True)


def worker(args):
    from django.core.wsgi import get_wsgi_application
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
    from whitenoise import WhiteNoise

    class TestServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, *unused):
            pass

    application = WhiteNoise(get_wsgi_application(), root=str(ROOT / "static"), prefix="static/", autorefresh=True)
    slots = threading.BoundedSemaphore(2)

    def bounded_application(environ, start_response):
        # Hold the slot through response iteration, not just construction.
        with slots:
            response = application(environ, start_response)
            try:
                yield from response
            finally:
                if hasattr(response, "close"):
                    response.close()

    server = make_server("127.0.0.1", args.worker_port, bounded_application,
                         server_class=TestServer, handler_class=QuietHandler)
    print(f"Disposable WSGI worker ready on {args.worker_port}", flush=True)
    server.serve_forever()


def serve(args):
    from fakeredis import TcpFakeServer
    server = TcpFakeServer(("127.0.0.1", args.cache_port), server_type="redis")
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    workers = []
    try:
        for port in args.http_ports:
            workers.append(subprocess.Popen([
                sys.executable, "-B", "-m", "safebooks.tests.deployment_probe", "worker",
                "--cluster", args.cluster, "--port", str(args.port),
                "--cache-port", str(args.cache_port), "--worker-port", str(port),
            ], cwd=ROOT))
        while all(process.poll() is None for process in workers):
            time.sleep(1)
        raise RuntimeError("An isolated worker stopped unexpectedly")
    finally:
        for process in workers:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def load(args):
    import requests
    from safebooks.models import Client
    clients = [Client.objects.filter(bookkeeper__username=f"step9_{index}").first().id for index in range(10)]
    sessions = []
    for index in range(10):
        session = requests.Session()
        session.trust_env = False
        base = f"http://127.0.0.1:{args.http_ports[index % 2]}"
        assert session.get(base + "/login/", timeout=15).status_code == 200
        response = session.post(base + "/api/auth/login/", json={"identifier": f"step9_{index}", "password": FIXTURE_PASSWORD},
                                headers={"X-CSRFToken": session.cookies["csrftoken"], "Origin": base}, timeout=15)
        assert response.status_code == 200 and response.json()["ok"]
        # Verify the authenticated cookie works on the other worker process.
        other = f"http://127.0.0.1:{args.http_ports[1 - index % 2]}"
        assert session.get(other + "/api/dashboard/summary/", timeout=15).status_code == 200
        sessions.append(session)

    def run_user(index, repetitions, analytics=False):
        session = sessions[index]
        paths = ["/api/dashboard/summary/", "/api/clients/", "/api/financial-records/clients/",
                 f"/api/financial-records/client/{clients[index]}/records/?month=all",
                 f"/api/reports/print-layout/?client_id={clients[index]}&date_from=2026-01-01&date_to=2026-12-31"]
        if analytics:
            paths = [f"/api/analytics/summary/?client_id={clients[index]}&year=all&horizon=3"]
        results = []
        for round_index in range(repetitions):
            for path in paths:
                base = f"http://127.0.0.1:{args.http_ports[(index + round_index) % 2]}"
                started = time.perf_counter()
                response = session.get(base + path, timeout=45)
                body = response.json()
                assert response.status_code == 200 and body.get("ok"), (response.status_code, body.get("code"))
                if analytics:
                    forecast = body["predictive_forecast"]
                    assert forecast["has_forecast"] and forecast["sales_method"] == "SARIMA", "Actual SARIMA fitting must be exercised"
                serialized = json.dumps(body)
                assert not any(f"Synthetic Client {other:02}-" in serialized for other in range(10) if other != index)
                results.append((time.perf_counter() - started, len(response.content)))
        return results

    for users, repetitions, analytics in ((1, 4, False), (5, 4, False), (10, 4, False), (5, 2, True)):
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=users) as executor:
            results = [result for batch in executor.map(lambda index: run_user(index, repetitions, analytics), range(users)) for result in batch]
        elapsed = time.perf_counter() - started
        latencies = sorted(result[0] for result in results)
        percentile = lambda fraction: round(latencies[min(len(latencies)-1, int(len(latencies)*fraction))] * 1000, 1)
        print(json.dumps({"users": users, "analytics": analytics, "requests": len(results), "errors": 0,
                          "seconds": round(elapsed, 2), "requests_per_second": round(len(results)/elapsed, 2),
                          "p50_ms": percentile(.5), "p95_ms": percentile(.95), "max_ms": percentile(1),
                          "max_response_bytes": max(result[1] for result in results)}), flush=True)


def concurrency(args):
    """Real HTTP/CSRF/session boundaries, writes racing across both processes."""
    import requests
    from django.db.models import Sum
    from safebooks.models import BookkeeperAccount, BookkeeperAuditLog, Client, FinancialRecord
    owner = BookkeeperAccount.objects.get(username="step9_1")
    ledger = Client.objects.filter(bookkeeper=owner).first()
    base = [f"http://127.0.0.1:{port}" for port in args.http_ports]
    sessions = []
    for index in range(2):
        session = requests.Session()
        session.trust_env = False
        session.get(base[index] + "/login/", timeout=15).raise_for_status()
        response = session.post(base[index] + "/api/auth/login/", json={"identifier": owner.username, "password": FIXTURE_PASSWORD},
                                headers={"X-CSRFToken": session.cookies["csrftoken"]}, timeout=15)
        assert response.status_code == 200 and response.json()["ok"]
        sessions.append(session)
    path = f"/api/financial-records/client/{ledger.id}/records/"
    payload = {"date": "2026-10-11", "frequency": "monthly", "notes": "Synthetic HTTP race",
               "line_items": [{"type_code": "Sales", "description": "Synthetic", "amount": "123.45"}]}
    def write(index, method, route, data):
        return sessions[index].request(method, base[index] + route, json=data,
                                       headers={"X-CSRFToken": sessions[index].cookies["csrftoken"]}, timeout=20)
    before = BookkeeperAuditLog.objects.filter(bookkeeper=owner).count()
    denied = sessions[0].post(base[0] + path, json=payload, timeout=15)
    assert denied.status_code == 403
    foreign = Client.objects.exclude(bookkeeper=owner).first()
    assert sessions[0].get(base[0] + f"/api/financial-records/client/{foreign.id}/records/?month=all", timeout=15).status_code == 404
    for repetition in range(5):
        created = write(0, "POST", path, payload)
        assert created.status_code == 201
        record = created.json()["record"]
        detail = path + str(record["id"]) + "/"
        barrier = threading.Barrier(2)
        def edit(index):
            barrier.wait(timeout=5)
            return write(index, "PATCH", detail, {"expected_revision": record["revision"],
                         "line_items": [{"type_code": "Sales", "description": "Winner", "amount": str(200 + index)}]})
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(edit, range(2)))
        assert sorted(response.status_code for response in results) == [200, 409]
        current = FinancialRecord.objects.get(pk=record["id"])
        assert current.total_amount == current.line_items.aggregate(total=Sum("amount"))["total"]
        assert write(0, "DELETE", detail, {"expected_revision": record["revision"]}).status_code == 409
        latest = next(response.json()["record"] for response in results if response.status_code == 200)
        assert write(1, "DELETE", detail, {"expected_revision": latest["revision"]}).status_code == 200
        assert not FinancialRecord.objects.filter(pk=record["id"]).exists()
    assert BookkeeperAuditLog.objects.filter(bookkeeper=owner).count() - before == 15
    # A logout on one worker invalidates that same cookie on the other worker.
    stale_cookie = sessions[0].cookies.get("sessionid")
    assert write(0, "POST", "/api/auth/logout/", {}).status_code == 200
    replay = requests.Session()
    replay.trust_env = False
    replay.cookies.set("sessionid", stale_cookie)
    assert replay.get(base[1] + "/api/dashboard/summary/", timeout=15).status_code == 401
    from django.db.models import F
    BookkeeperAccount.objects.filter(pk=owner.pk).update(session_version=F("session_version") + 1)
    assert sessions[1].get(base[0] + "/api/dashboard/summary/", timeout=15).status_code == 401
    print("PASS: 5 cross-process edit races; stale deletes; consistent totals; exactly 15 financial audits; CSRF/ownership denial; shared logout-cookie replay rejection; durable-version revocation", flush=True)


def plans(args):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from safebooks.models import BookkeeperAccount, Client
    from safebooks.services.dashboard_service import get_dashboard_summary_for_bookkeeper
    from safebooks.services.financial_record_service import list_records_for_client_period, list_transactions_for_client_range
    from safebooks.services.analytics_service import get_analytics_summary_for_bookkeeper
    owner = BookkeeperAccount.objects.get(username="step9_1")
    ledger = Client.objects.filter(bookkeeper=owner).first()
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE")
    operations = {
        "dashboard": lambda: get_dashboard_summary_for_bookkeeper(owner),
        "records": lambda: list_records_for_client_period(owner, ledger.id, "all"),
        "report": lambda: list_transactions_for_client_range(owner, ledger.id, "2026-01-01", "2026-12-31"),
        "analytics": lambda: get_analytics_summary_for_bookkeeper(owner, client_id=ledger.id, horizon=3),
    }
    for label, operation in operations.items():
        started = time.perf_counter()
        with CaptureQueriesContext(connection) as queries:
            assert operation()["ok"]
        timings, node_types, disk_sorts = [], set(), []
        def inspect(node):
            node_types.add(node["Node Type"])
            if node.get("Sort Space Type") == "Disk":
                disk_sorts.append(node.get("Sort Space Used"))
            for child in node.get("Plans", []):
                inspect(child)
        for query in queries:
            if not query["sql"].lstrip().upper().startswith("SELECT"):
                raise RuntimeError("Explain is restricted to inspected read-only SELECT queries")
            with connection.cursor() as cursor:
                cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query["sql"])
                plan = cursor.fetchone()[0][0]
            timings.append(plan["Execution Time"])
            inspect(plan["Plan"])
        print(json.dumps({"operation": label, "queries": len(queries), "wall_ms": round((time.perf_counter()-started)*1000,1),
                          "total_explain_execution_ms": round(sum(timings),1), "max_query_ms": round(max(timings),1),
                          "plan_nodes": sorted(node_types), "disk_sorts": disk_sorts}), flush=True)


def recovery(args):
    """Dump synthetic data; restore only into a newly created disposable clone."""
    from django.db import IntegrityError, connections, transaction
    from django.db.models import F
    from django.contrib.sessions.models import Session
    from safebooks.models import AdminAccount, BookkeeperAccount
    from safebooks.services.session_security_service import account_session_auth_hash
    from safebooks.views import SESSION_BOOKKEEPER_ID_KEY, SESSION_BOOKKEEPER_AUTH_HASH_KEY
    target = "safebooks_step9_recovery"
    alias = "step9_recovery"
    if not args.pg_bin:
        raise RuntimeError("Specify the installed PostgreSQL vendor bin directory")
    tools = {name: Path(args.pg_bin) / (name + (".exe" if os.name == "nt" else "")) for name in ("pg_dump", "pg_restore")}
    if not all(path.is_file() for path in tools.values()):
        raise RuntimeError("Installed pg_dump and pg_restore are required")
    source = connections["default"]

    def fingerprint(database_alias):
        conn = connections[database_alias]
        result = {}
        with conn.cursor() as cursor:
            for table in sorted(conn.introspection.table_names(cursor)):
                constraints = conn.introspection.get_constraints(cursor, table)
                primary = next(info["columns"] for info in constraints.values() if info["primary_key"])
                quoted = conn.ops.quote_name
                cursor.execute(f"SELECT * FROM {quoted(table)} ORDER BY {', '.join(quoted(column) for column in primary)}")
                digest, rows = hashlib.sha256(), 0
                while batch := cursor.fetchmany(1000):
                    for row in batch:
                        digest.update(json.dumps(row, default=str, sort_keys=True).encode())
                        rows += 1
                result[table] = (rows, digest.hexdigest())
        return result

    def command(name, arguments, environment):
        result = subprocess.run([str(tools[name]), *arguments], env=environment,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
        if result.returncode:
            # A dump/tool failure must not print connection details or SQL/data.
            raise RuntimeError(f"Synthetic {name} check failed; exit code {result.returncode}")

    before = fingerprint("default")
    created = False
    with source.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [target])
        if cursor.fetchone():
            raise RuntimeError("Recovery requires an absent target database; it never overwrites one")
        cursor.execute(f'CREATE DATABASE "{target}"')
        created = True
    try:
        config = deepcopy(source.settings_dict)
        config["NAME"] = target
        connections.databases[alias] = config
        with tempfile.TemporaryDirectory(prefix="recovery-check-", dir=args.cluster) as backup_directory:
            Path(backup_directory).resolve().relative_to(Path(args.cluster).resolve())
            archive = Path(backup_directory) / "synthetic.dump"
            environment = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC") if key in os.environ}
            environment["PGPASSFILE"] = str(Path(backup_directory) / "no-real-credentials")
            connection_arguments = ["--host=127.0.0.1", f"--port={args.port}", "--username=safebooks_step9", "--no-password"]
            started = time.perf_counter()
            command("pg_dump", [*connection_arguments, "--format=custom", "--no-privileges", "--lock-wait-timeout=5000", f"--file={archive}", DATABASE], environment)
            archive_bytes = archive.stat().st_size
            command("pg_restore", [*connection_arguments, "--no-owner", "--no-privileges", "--exit-on-error", "--single-transaction", f"--dbname={target}", str(archive)], environment)
            assert fingerprint(alias) == before, "Restored table data differ from the synthetic source"
            with connections[alias].cursor() as cursor:
                cursor.execute('SELECT count(*) FROM financial_records r LEFT JOIN (SELECT record_id, sum(amount) total FROM financial_record_lines GROUP BY record_id) l ON l.record_id=r.id WHERE r.total_amount <> coalesce(l.total,0)')
                assert cursor.fetchone()[0] == 0, "Restored financial totals are inconsistent"
                cursor.execute('SELECT count(*) FROM financial_records r JOIN clients c ON c.id=r.client_id JOIN periods p ON p.id=r.period_id WHERE r.bookkeeper_id<>c.bookkeeper_id OR r.client_id<>p.client_id')
                assert cursor.fetchone()[0] == 0, "Restored financial ownership/period relationships differ"
            existing = BookkeeperAccount.objects.using(alias).first()
            try:
                with transaction.atomic(using=alias):
                    BookkeeperAccount.objects.using(alias).create(full_name="Synthetic Duplicate", username="recovery_unique_probe", email=existing.email.upper(), password_hash="synthetic-unused")
            except IntegrityError:
                pass
            else:
                raise AssertionError("Restored case-insensitive uniqueness was not enforced")
            maximum = BookkeeperAccount.objects.using(alias).order_by("-pk").first().pk
            try:
                with transaction.atomic(using=alias):
                    probe = BookkeeperAccount.objects.using(alias).create(full_name="Synthetic Sequence", username="recovery_sequence_probe", email="recovery-sequence@example.test", password_hash="synthetic-unused")
                    assert probe.pk > maximum, "Restored sequence can collide with existing IDs"
                    raise RuntimeError("rollback-synthetic-probe")
            except RuntimeError as error:
                if str(error) != "rollback-synthetic-probe":
                    raise
            old_proof, sample_id = None, None
            for restored_session in Session.objects.using(alias).all():
                decoded = restored_session.get_decoded()
                if decoded.get(SESSION_BOOKKEEPER_ID_KEY) and decoded.get(SESSION_BOOKKEEPER_AUTH_HASH_KEY):
                    sample_id = decoded[SESSION_BOOKKEEPER_ID_KEY]
                    old_proof = decoded[SESSION_BOOKKEEPER_AUTH_HASH_KEY]
                    assert account_session_auth_hash(BookkeeperAccount.objects.using(alias).get(pk=sample_id)) == old_proof
                    break
            # Recovery security drill on the new clone only; never the source.
            with transaction.atomic(using=alias):
                Session.objects.using(alias).all().delete()
                for model in (AdminAccount, BookkeeperAccount):
                    model.objects.using(alias).all().update(session_version=F("session_version") + 1)
            assert not Session.objects.using(alias).exists()
            if old_proof:
                assert account_session_auth_hash(BookkeeperAccount.objects.using(alias).get(pk=sample_id)) != old_proof
            assert fingerprint("default") == before, "The backup/restore drill changed its source"
            print(json.dumps({"recovery": "passed", "tables_compared": len(before), "archive_bytes": archive_bytes,
                              "seconds": round(time.perf_counter()-started,2), "source_unchanged": True,
                              "financial_totals_and_ownership": "passed", "uniqueness_and_sequence": "passed",
                              "clone_sessions_cleared": True, "old_clone_proof_rejected": bool(old_proof)}), flush=True)
    finally:
        if alias in connections:
            connections[alias].close()
        if created:
            with source.cursor() as cursor:
                cursor.execute(f'DROP DATABASE "{target}"')


def benchmarks(args):
    """Reproduce dense reads and the formerly slow forecast with synthetic data."""
    from unittest.mock import patch
    from django.db import transaction
    from safebooks.models import BookkeeperAccount, Client, FinancialRecord, FinancialRecordLine, Period
    from safebooks.services import analytics_service as analytics
    if BookkeeperAccount.objects.filter(username__in=["step9_dense", "step9_ceiling"]).exists():
        raise RuntimeError("Benchmark fixtures already exist; no data will be reset")
    fixture_hash = BookkeeperAccount.objects.get(username="step9_0").password_hash
    def owner(username):
        return BookkeeperAccount.objects.create(full_name="Synthetic " + username, username=username,
            email=username + "@example.test", password_hash=fixture_hash, status="approved",
            client_details_password_required=False, client_record_email_notifications_enabled=False)
    with transaction.atomic():
        dense_owner = owner("step9_dense")
        ledger = Client.objects.create(bookkeeper=dense_owner, client_name="Synthetic Dense Boundary", tin_number="999888777000", location="Synthetic Test City")
        period = Period.objects.create(client=ledger, year=2026, month=10)
        records = FinancialRecord.objects.bulk_create([FinancialRecord(bookkeeper=dense_owner, client=ledger, period=period, entry_date=date(2026,10,1), total_amount=4) for _ in range(5000)])
        FinancialRecordLine.objects.bulk_create([FinancialRecordLine(record=record, type_code="Sales", description="Synthetic dense", amount=1, sort_order=index) for record in records for index in range(4)])
        ceiling_owner = owner("step9_ceiling")
        for index in range(20):
            client = Client.objects.create(bookkeeper=ceiling_owner, client_name=f"Synthetic Ceiling {index:02}", tin_number=f"998{index:03}000000", location="Synthetic Test City")
            periods = Period.objects.bulk_create([Period(client=client, year=2006+(month+10)//12, month=(month+10)%12+1) for month in range(240)])
            records = FinancialRecord.objects.bulk_create([FinancialRecord(bookkeeper=ceiling_owner, client=client, period=period, entry_date=date(period.year,period.month,1), total_amount=1250) for period in periods])
            FinancialRecordLine.objects.bulk_create([FinancialRecordLine(record=record, type_code=kind, description="Synthetic ceiling", amount=amount, sort_order=order) for record in records for order,kind,amount in ((0,"Sales",1000),(1,"Expenses",200),(2,"Taxes",50))])
    started = time.perf_counter()
    result = analytics.get_analytics_summary_for_bookkeeper(dense_owner, client_id=ledger.id, year_filter="2026")
    assert result["ok"] and result["summary"]["total_sales"] == 20000
    assert result["client_workflow"]["current_period_entry_count"] == 5000
    print(json.dumps({"dense_analytics": "passed", "records": 5000, "details": 20000, "client_id": ledger.id, "seconds": round(time.perf_counter()-started,2)}), flush=True)
    started = time.perf_counter()
    with patch.object(analytics, "build_sarima_forecast", wraps=analytics.build_sarima_forecast) as calls:
        result = analytics.get_analytics_summary_for_bookkeeper(ceiling_owner, horizon=12)
    assert result["ok"] and result["predictive_forecast"]["has_forecast"]
    assert calls.call_count == 3
    print(json.dumps({"forecast_ceiling": "passed", "series": 60, "observations_each": 240, "actual_distinct_models": calls.call_count, "seconds": round(time.perf_counter()-started,2)}), flush=True)
    # One-over fixture is for visible error/recovery checks, not a real write.
    FinancialRecord.objects.create(bookkeeper=dense_owner, client=ledger, period=period, entry_date=date(2026,10,1), total_amount=0)
    print("Synthetic dense client now intentionally exceeds the record budget for browser error tests", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("suite", "seed", "serve", "worker", "load", "concurrency", "plans", "recovery", "benchmarks"))
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--port", type=int, default=55439)
    parser.add_argument("--cache-port", type=int, default=56379)
    parser.add_argument("--http-ports", type=int, nargs=2, default=[8541, 8542])
    parser.add_argument("--worker-port", type=int, default=8541)
    parser.add_argument("--pg-bin", help="Installed PostgreSQL bin directory; required for synthetic recovery mode")
    args = parser.parse_args()
    allowed = configure(args)
    if args.mode == "suite":
        suite(args, allowed)
    elif args.mode == "seed":
        seed()
    else:
        globals()[args.mode](args)


if __name__ == "__main__":
    main()
