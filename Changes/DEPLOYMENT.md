# SafeBooks production preparation

This prepares an opt-in Linux deployment; it does not deploy the project or
certify the remaining readiness steps. Windows `manage.py runserver` continues
to use `safebooks.settings` and the existing local `.env`.

## Hosting requirements

- Python 3.14.8 (the patched hosting target in `.python-version`), installed from
  the host's maintained patch stream. Local tests currently run on Python 3.14.4;
  the hosting target still needs staging verification. This step does not replace
  the user's system interpreter. Install `requirements.txt` in a clean environment. The security
  patches are Django 6.0.9 and sqlparse 0.6.0; do not downgrade them.
- Managed PostgreSQL with encrypted connections, backups, and a restricted
  application role. Redis is temporary auth state, **not** a backup database.
- One writable TLS Redis primary accessible to every worker. Use the same
  endpoint and cache prefix across workers, but a distinct prefix/service for
  production, staging, and tests. Do not use HTTP-only/REST Redis endpoints,
  local-memory cache, read replicas, or a service that drops writes when paused.
- HTTPS and a verified reverse proxy. Private database and Redis access only;
  never expose Redis to arbitrary internet clients. Keep its server patched.
- SMTP with TLS or SSL and verified sender credentials. Google sign-in is
  optional; leave all three Google settings unset to disable it.

## Hosting environment secrets

Set `DJANGO_SETTINGS_MODULE=safebooks.settings_production`. This profile refuses
unsafe or incomplete settings and **does not load the local `.env`**. Production
never uses the development-only fallback signing key. Use these variable names:

| Variable | Required value |
| --- | --- |
| `SAFEBOOKS_SECRET_KEY` | A newly generated random key, at least 50 characters; identical on every worker. Store only in hosting secrets. |
| `SAFEBOOKS_ALLOWED_HOSTS` | Comma-separated exact public hostnames; no scheme, port, wildcard, or path. |
| `SAFEBOOKS_CSRF_TRUSTED_ORIGINS` | Optional comma-separated HTTPS origins for those exact hosts; defaults to their HTTPS origins. |
| `SAFEBOOKS_DB_NAME`, `SAFEBOOKS_DB_USER`, `SAFEBOOKS_DB_PASSWORD`, `SAFEBOOKS_DB_HOST` | Credentials for the **hosting** PostgreSQL database. |
| `SAFEBOOKS_DB_PORT` | Optional; defaults to 5432. |
| `SAFEBOOKS_DB_SSLMODE` | Defaults to `require`; prefer `verify-full` with the provider's CA where supported. `disable`/`prefer`/`allow` are rejected. |
| `SAFEBOOKS_DB_SSLROOTCERT` | Optional provider CA file path for certificate verification. |
| `SAFEBOOKS_REDIS_URL` | Provider's **authenticated TLS `rediss://`** primary connection URL, including the Redis password. Certificate validation is required. URL-encode credentials; query overrides, anonymous connections, and replica lists are rejected. |
| `SAFEBOOKS_CACHE_KEY_PREFIX` | Short identifier such as `safebooks-usability`; unique to this environment, identical on all workers. |
| `SAFEBOOKS_EMAIL_HOST`, `SAFEBOOKS_EMAIL_HOST_USER`, `SAFEBOOKS_EMAIL_HOST_PASSWORD`, `SAFEBOOKS_DEFAULT_FROM_EMAIL` | Verified hosting SMTP configuration. |
| `SAFEBOOKS_EMAIL_USE_TLS`, `SAFEBOOKS_EMAIL_USE_SSL` | Exactly one enabled. Defaults: TLS on, SSL off. |
| `SAFEBOOKS_EMAIL_PORT` | Defaults to 587 for TLS or 465 for SSL. |
| `SAFEBOOKS_GOOGLE_OAUTH_CLIENT_ID`, `SAFEBOOKS_GOOGLE_OAUTH_CLIENT_SECRET`, `SAFEBOOKS_GOOGLE_OAUTH_REDIRECT_URI` | Optional, but set all three together. Callback must be `https://<allowed-host>/auth/google/callback/`; register that exact URL with Google. |

Do not publish actual environment values, authentication proofs, reset codes,
tokens, request cookies, or connection URLs in tickets, logs, screenshots, Git,
or reports. Do not paste them into commands that will be saved in shell history.

## HTTPS proxy setup

Secure cookies and HTTPS redirect are mandatory in production. By default Django
does **not** trust forwarded-protocol headers. If the chosen host terminates TLS,
confirm that only its proxy can reach the application and it strips/overwrites
client-provided `X-Forwarded-Proto`. **Only then** set
`SAFEBOOKS_TRUST_PROXY_PROTO=1`; set `SAFEBOOKS_FORWARDED_ALLOW_IPS` to the trusted
proxy addresses according to the host's documentation. Never trust `*` on a
publicly reachable app server. Confirm HTTPS detection and lack of redirect loops.

HSTS intentionally remains off until the actual host's HTTPS behavior has been
verified. `check --deploy` therefore reports `security.W004`; do not silence or
mistake it for an already verified transport policy. Existing inline scripts and
CDN resources still require a separately tested CSP rollout; no restrictive CSP
was added that could unexpectedly break pages or printouts.

## Build and release commands (on the host)

With hosting secrets configured, run:

```sh
python -m pip install --upgrade pip==26.2.1
python -m pip install -r requirements.txt
python -m pip check
python manage.py collectstatic --noinput --settings=safebooks.settings_production
python manage.py check --deploy --settings=safebooks.settings_production
```

Collect assets before checks/page requests: the current favicon route resolves
through the production static-file manifest, which must already exist.

Run migrations **once as an explicit release action**, after backup/recovery and
migration review, not in each web worker or automatically during the build:

```sh
python manage.py migrate --plan --settings=safebooks.settings_production
python manage.py migrate --noinput --settings=safebooks.settings_production
python manage.py check_deployment_services --settings=safebooks.settings_production
```

The service probe runs `SELECT 1` and creates/increments/deletes only its own
short-lived random Redis key. It never flushes the cache or edits application
records. A cache flush/restart/eviction loses pending resets and attempt limits;
users may need to restart verification. Prefer sufficient capacity with
`noeviction`, monitor errors, and never fall back silently to per-process cache.

Start the web process using the supplied `Procfile`, or:

```sh
gunicorn --config gunicorn.conf.py safebooks.wsgi:application
```

The server configuration explicitly selects production settings. Gunicorn is
Linux/Unix-only and is deliberately not installed on Windows by the runtime
requirements marker. Begin with one worker and two threads on limited hosting.
Increase `WEB_CONCURRENCY` only after measuring memory, CPU, PostgreSQL connection
limits, forecasting latency, and simultaneous-user behavior. Every worker shares
the same database, session key, and Redis state. Access logs are disabled by
default because current URL query strings can identify clients; use sanitized
hosting metrics and error logs.

WhiteNoise serves only collected static assets (`staticfiles/`) with hashed
filenames and compression. Do not use it to serve private client files or uploaded
media. Uploaded media, if introduced, needs private durable storage and explicit
authorization; ephemeral hosting disks are not suitable for persistent data.

## Verification still needed before real users

Step 6 adds migration `0034_account_case_insensitive_unique`: unique expression
indexes on `UPPER(bookkeeper email)`, `UPPER(bookkeeper username)`, and
`UPPER(admin email)`, matching PostgreSQL case-insensitive account lookups. It
does not normalize, rewrite, merge, or delete account values and does not change
client/financial schemas. Audit case-insensitive duplicates on the target
database before release; conflicting legacy accounts stop the migration instead
of being repaired automatically. Resolve any such conflicts only with explicit
approval. Applying the indexes briefly requires database locks; schedule the
release outside active writes and verify the migration on staging first.

Shared validators now reject non-finite/overflowing financial inputs and totals,
overlong model text, malformed custom fields, and invalid JSON before writes.
Existing two-decimal rounding and valid zero values are retained. Friendly
uniqueness pre-checks are not concurrency protection: account constraints and
transaction rollback are the final safeguard. Run
`safebooks.tests.test_data_validation` and
`safebooks.tests.test_account_identifier_migration` on disposable PostgreSQL as
well; SQLite results do not verify the hosting database's collation, expression
index behavior, or concurrent writers. Browser integration and load testing
remain Step 9; no visual layout changes were made for Step 6.

Step 6 local verification (2026-10-11): 107 focused tests ran, with 106 passing
and the PostgreSQL-only row-lock test skipped. The broader run executed 385
tests: 384 passed and that same row-lock test was skipped. The known SQLite
approval-concurrency failure was excluded, not counted as passing. This run
included all 15 production-profile tests and the report/editor JavaScript test;
the financial modal JavaScript checks also passed separately. Django checks,
migration/model consistency, and diff whitespace checks passed. The isolated
upgrade/reverse/reapply tests preserved synthetic data; duplicate legacy fixtures
blocked the upgrade and rolled back all added constraints. With explicit user
approval, only migration 0034 was applied to the current PostgreSQL database.
All three indexes were verified, and before/after comparisons found no changes
to account, client, period, record, line-item, or audit values. The local `.env`
and SQLite file were unchanged. These checks are not a real-browser or hosted
multi-user certification.

Step 6 changed files:

- Shared validation and request parsing: `safebooks/validators/data_validator.py`,
  `safebooks/views.py`.
- Connected services: `safebooks/services/financial_record_service.py`,
  `client_service.py`, `auth_service.py`, `profile_service.py`,
  `admin_profile_service.py`.
- Account schema: `safebooks/models/user_model.py`, `admin_model.py`,
  `safebooks/migrations/0034_account_case_insensitive_unique.py`.
- Financial form: `templates/base/financial_records_client.html`.
- Regression checks: `safebooks/tests/test_data_validation.py`,
  `test_account_identifier_migration.py`,
  `safebooks/tests/js/test_financial_reliability.cjs`.
- Project rules and handoff: `AGENTS.md`, `DEPLOYMENT.md`.

## Step 7: truthful settings, delivery, logout, and client status

Theme preferences are saved only in the current browser, not to the account or
other devices. A blocked storage write is shown as not saved. Opening Settings
does not silently disable an existing follow-system preference. Server-rendered
email toggles reflect the saved account preferences, and Settings explains local
email backend and environment-wide delivery restrictions. Client-record email,
login-alert, and client-details-lock preferences commit with their audit entries;
an audit/storage failure rolls back the preference. An unknown save outcome
requires reloading Settings before retrying, not an automatic repeat write.

Client, approval, verification/reset, and login-alert email paths check
the backend's positive integer acknowledgement. Acceptance is **not** proof of
inbox delivery. Local console/file/dummy backends skip client and approval
notifications instead of claiming inbox delivery;
locmem remains a synthetic test capture, not a real delivery service. Local
verification/reset code generation retains development behavior and explicitly
states no inbox delivery. SMTP errors are logged by class, without exception
details or private message contents. Client notifications remain best-effort
after financial commit; a failed email never rolls back a saved transaction.
Durable delivery retries and provider delivery/bounce tracking are not added.

Logout redirects and browser-label cleanup happen only after a confirmed server
response or an already-unauthenticated response. Failed/malformed/unknown
responses keep the page visible with a retry warning. Duplicate clicks share one
pending request. An admin audit failure cannot prevent session removal; a session
storage failure is reported as unconfirmed, not successful logout.

Calculated client status uses owned, non-future financial records, not empty or
future periods. Closed clients stay Closed. The existing **calendar-month**
12-month inactivity threshold takes priority over two distinct recorded periods
becoming Active. Where neither threshold applies, existing manual remarks are
retained. Directories, dashboards, analytics, and client-detail reads calculate
status without saving it. Explicit client/financial writes persist status under
the owned-client lock. No existing values are bulk rewritten. The directory's
Inactive tab still uses its established Closed-or-Separated filter; the name and
heading now accurately describe it. Reopening shows the returned status rather
than assuming Active. Financial amounts, periods, and forecasting rules are
unchanged.

Step 7 final local verification (2026-10-11): 407 tests were discovered; 406 ran,
with 405 passing and the PostgreSQL-only row-lock test skipped. The known SQLite
approval-concurrency test was explicitly excluded, not counted as passing. The
run includes the 15 production-profile tests, existing report/editor JavaScript
checks, and new settings/logout/status JavaScript checks. All tests used synthetic
data in an in-memory SQLite database, local test mail/cache, and blocked external
connections except the disposable loopback Redis emulator used by its own tests.
The initial focused run identified a new logout test's stale test-client cookie;
correcting that fixture and rerunning verified actual session removal even when
admin audit storage fails. Tests also confirmed preference/audit rollback, zero
email acknowledgements, failed requests without false success, owned status
calculation, read-only status displays, and status persistence on explicit writes.
Eleven affected template script blocks and four static scripts parsed; the
financial modal and authenticator JavaScript regressions passed separately.
Django checks, migration/model consistency, and diff whitespace checks passed.
No Step 7 migration was needed. The current database was not accessed or changed,
and `.env` and the SQLite file hashes remained unchanged. Real inbox delivery,
live-browser visual/integration behavior, hosted services, and PostgreSQL
multi-worker contention still require staging verification in Steps 9-10.

Step 7 changed files:

- Request boundaries: `safebooks/views.py`.
- Status and existing write consumers: `safebooks/services/client_service.py`,
  `dashboard_service.py`, `analytics_service.py`, `financial_record_service.py`.
- Delivery handling: `safebooks/services/email_delivery_service.py`,
  `client_notification_service.py`, `approval_notification_service.py`,
  `auth_service.py`.
- Shared/browser behavior: `static/js/app_shared.js`, `settings_page.js`,
  `profile_page.js`, `reports_page.js`.
- Connected templates: `templates/base/settings.html`, `bookkeeper_base.html`,
  `clients.html`, `client_details.html`, `dashboard.html`, `analytics.html`,
  `financial_records.html`, `financial_records_client.html`;
  `templates/admin_panel/partials/admin_scripts.html`;
  `templates/authentication/email_verification.html`, `pending_approval.html`.
- Regression checks: `safebooks/tests/test_settings_delivery_logout.py`,
  `test_financial_reliability.py`, `test_admin_approvals_api.py`,
  `safebooks/tests/js/test_settings_logout.cjs`.
- Project rules and this handoff: `AGENTS.md`, `DEPLOYMENT.md`.

Financial writes now keep record/line-item/status changes and their financial audit entry in one transaction. All financial writers lock the owned client first; edit and delete requests require the loaded record's `revision` as `expected_revision`. Refresh any tabs opened before this update. Notification email is best-effort after commit, not a durable delivery queue. A lost response can leave the save outcome unknown: refresh the records before submitting again; automatic retry/durable create-request deduplication is not implemented. Run `safebooks.tests.test_financial_reliability` against a **disposable PostgreSQL test database** before accepting production concurrency behavior; SQLite tests do not verify PostgreSQL row locks. Do not point test commands at the live database.

- Run authentication, 2FA, reset, session-revocation, CSRF, email, and Google flows
  against isolated staging PostgreSQL and **real hosted TLS Redis** with two or
  more workers. Current developer-machine tests cannot certify hosting TLS,
  Redis capacity/eviction, credentials, sender delivery, or Linux Gunicorn startup.
- Run the approval-concurrency test on disposable PostgreSQL. Its known SQLite
  locking failure is not a passing production-concurrency result.
- Complete the remaining readiness fixes and Step 9 browser/load testing.
- Verify backups, restore procedure, monitoring, host limits, persistence, and
  maintenance responsibilities (Step 10). Do not use real client financial data
  until those safeguards and applicable data handling requirements are satisfied.
- Re-run dependency auditing for a clean **Linux** install shortly before each
  release; a Windows environment excludes Gunicorn. Tools: `pip-audit` (audit only,
  do not blindly use automatic fixes). The audit queries public package names and
  versions, not `.env` or client data. Pin reviewed transitive runtime dependencies.

Local verification tools are listed separately in `requirements-dev.txt`.
The Redis cross-process regression uses a disposable loopback protocol emulator,
not a real hosted Redis service; it is not a hosting/TLS certification.

The Step 4 configuration preparation leaves the current database and `.env`
unchanged; account schema migrations in Steps 3 and 6 are separate, explicitly
approved release actions. Production signing keys differ from development keys; existing browser
sessions are not transferable and users must sign in on the hosted origin.

## Step 8: query growth and synchronous workload budgets

Financial records and report rows now load ordered line items in bounded batches,
instead of bypassing prefetch and making another query for each record. Deadline
completion reuses owned activity aggregates rather than querying once per card.
Directory reads defer saved passwords/custom fields. Analytics reads its financial
history once, reuses it for recent-month totals, and groups workflow counts by
frequency/period instead of loading every raw historical record or counting each
frequency separately. Prior-frequency queries clear default ordering before
`distinct()` so old records do not produce duplicate frequency values. Monetary
classification, rounding, financial totals, revision checks, and write/audit
transactions are unchanged.

With explicit user approval, `safebooks/services/workload_limits.py` defines
initial synchronous budgets: 5,000 records, 20,000 transaction details, 60 forecast
series, 240 observations per series, and a 1-12 month forecast horizon. Histories
use a one-over-limit sentinel and a **global** detail budget, not an unbounded
prefetch or 20,000 details multiplied by each record. Financial entry validation
also rejects more than 20,000 submitted details before creating lines. Forecasts
check all series before fitting; no history is shortened to fit the limit. The
existing 240-period forecast scheduling loop now rejects excessive spans rather
than silently returning a shortened projection. Oversized read requests return
HTTP 400 with `code: workload_limit`, without partial summaries, rows, or forecasts.
The analytics error contains only owned directory-safe selector metadata so the
user can narrow an initially oversized All Clients request.

The report endpoint additionally accepts `years_only=1` with `client_id`, returning
owned `available_years` metadata and the same credential-redacted client summary,
never transaction details. Client Details uses this lightweight request to populate
the year selector, then loads only the current bookkeeping year. Selecting another
year fetches that year; All Years remains an explicit action subject to the same
budgets. Switching year/closing the modal invalidates stale requests and disables
stale printing. Workload errors are persistent accessible alerts, not a claim of
zero/no financial records; narrowing controls stay usable. No page layout/CSS,
database migration, data rewrite, `.env`, or hosting configuration was changed.

Measured service query budgets with 1 versus 30 synthetic clients/records are
constant: dashboard 3/3, financial directory 1/1, client directory 1/1, record
list 5/5, report 4/4, and client analytics 4/4. These are query counts, **not**
latency or memory guarantees. Directories still return complete client selectors;
server-side directory pagination remains a larger coordinated API/UI improvement
if real account sizes warrant it. Limits bound synchronous materialization and
forecast fitting, not database aggregate/sort time, input note byte size, or the
number of concurrent requests. Step 9 must measure PostgreSQL query plans,
indexes, largest permitted workloads, memory, timeouts, repeated forecasts, and
multiple workers/users before these initial limits are accepted for hosting.
No new cache, background queue, rate limiter, or schema index was introduced.

Step 8 final local verification (2026-10-11): 154 focused tests ran, with 153
passing and the PostgreSQL-only row-lock test skipped. The run covered query
growth, workload limits, financial CRUD/reliability, client ownership/privacy,
dashboards, analytics/workflows, reports, settings/delivery/logout, and real SARIMA
numerical regressions. Exact 5,000-record and 20,000-detail boundaries passed;
one-over requests returned no partial money. Tests also checked global detail
limits, invalid/huge query parameters, early forecast rejection, owned year-only
metadata without loading details, and recovery through narrower filters.
All tests used synthetic data in explicitly shared in-memory SQLite, local test
mail/cache, and blocked external socket connections. An earlier run with literal
`:memory:` hit two threaded test failures because worker connections could not
share the schema; the corrected isolated test setup passed both concurrency
regressions. The application conflict handler was not changed to hide those
fixture failures. SQLite success is still not PostgreSQL row-lock certification.

Four standalone JavaScript regression scripts passed: workload/report loading,
financial modal revisions/draft/error behavior, client/report privacy, and
settings/logout. The workload script also parsed the three affected templates;
the settings/logout script parsed eleven template script blocks and four static
scripts. New report checks covered current-year-only requests, explicit year/All
Years changes, workload errors without stale printing, recovery, stale responses,
and closing a pending modal. A first syntax-check attempt treated the template's
JSON data block as executable JavaScript; correcting the test to skip that data
block resolved it without changing the application's JSON markup. Django checks,
model/migration consistency, and diff whitespace checks passed. The grouped
workflow query compiled for PostgreSQL without opening a connection; execution
and query plans remain unverified. No real-browser visual/load test or full-suite
Step 9 certification is claimed. `.env` and the local SQLite file hashes were
unchanged; the current PostgreSQL database was not accessed.

Step 8 changed files:

- Services: `safebooks/services/client_service.py`, `dashboard_service.py`,
  `financial_record_service.py`, `analytics_service.py`, `forecasting_service.py`,
  and new `workload_limits.py`.
- Request boundary: `safebooks/views.py`.
- Connected pages: `templates/base/client_details.html`, `analytics.html`,
  `financial_records_client.html`.
- Regression tests: `safebooks/tests/test_query_growth.py`,
  `test_workload_limits.py`, `safebooks/tests/js/test_workload_limits.cjs`.
- Project rules and handoff: `AGENTS.md`, `DEPLOYMENT.md`.

## Step 9: disposable PostgreSQL, browser and load verification

Completed local verification on 2026-10-12: the full suite passed twice on
disposable PostgreSQL 18.3 (426 tests each run, no failures or skips). Cross-process
financial races, ownership/CSRF checks, session revocation, real mobile/desktop
browser flows and bounded multi-user loads were also exercised with synthetic
data only. Five standalone JavaScript regressions passed.

**Deployment sign-off remains blocked.** Permitted dense analytics exceeded a
15-second test query timeout and returned HTTP 500; the permitted forecast ceiling
took 38.78 seconds; analytics failures leave a misleading missing-record schedule
card. Smaller ordinary loads passed, but this is not hosted capacity certification.
Real TLS Redis, Linux Gunicorn/HTTPS proxy, delivery, monitoring and backup/restore
verification remain external release requirements.

See [the detailed Step 9 report](Changes/Verification/step9_deployment_verification_2026-10-12.md)
for measured results, severity, browser coverage, limitations and safe reproduction.
The new `safebooks/tests/deployment_probe.py` is an opt-in isolated test harness,
not application or production configuration. No application fix or live data
change was made during Step 9; obtain approval for corrective work before release.

## Step 10: approved follow-up fixes and local recovery preparation

The Step 9 section above is the historical pre-fix baseline. The subsequently
approved changes remove the dense workflow query's per-detail correlated lookup,
return safe JSON 503 for analytics-service database failures, and distinguish
unavailable/loading schedules from genuinely missing records. Report failures
also stop claiming that preview years are still loading.

Forecasts reuse identical immutable inputs only within one request, with separate
client metadata. In addition to the existing history/per-series limits, reject
more than 8 distinct eligible fits or 960 observations across those fits before
fitting anything. Unsupported, irregular and insufficient histories do not consume
this fit budget. No data is truncated and no partial totals/forecasts are returned.

Local verification completed 2026-10-12: **436 Django tests passed on disposable
PostgreSQL 18.3, with no skips**; five standalone JavaScript regressions passed;
five cross-process edit races and 330 isolated HTTP load requests passed. Dense
5,000-record/20,000-detail analytics now completed successfully. The previous
60-series/240-observation fixture reused three actual fits instead of sixty,
but still took approximately 10.5 seconds locally; these are not hosting guarantees.
Client analytics uses a constant 5/5 queries for 1 versus 30 records/clients,
including the separate latest-record batch (previously 4/4).

A real `pg_dump`/`pg_restore` drill restored synthetic data to a newly created
disposable database, compared all 20 tables, and checked totals, ownership,
constraints, sequences and cloned-session invalidation. Its source was unchanged.
The temporary database cluster/accounts/dumps were removed after verification;
the normal PostgreSQL database and `.env` were not used or modified.

**Hosted verification remains pending.** No hosting account, real SMTP delivery,
TLS Redis service, HTTPS proxy, provider backup job, continuous alerting or hosted
restore/capacity test was configured or certified. A restored system must remain
private until restored sessions/auth state are invalidated and post-backup security
changes are reconciled; a rolled-back security counter alone is not sufficient.
No new production settings, routes, schema migration or stored-data rewrite was
introduced by this follow-up.

See [the detailed local results and limitations](Changes/Verification/step10_local_preparation_2026-10-12.md)
and [the owner-operated usability deployment guide](USABILITY_DEPLOYMENT.md).
Start the hosted trial with a fresh database and fictional client data. Resolve
credential-at-rest and private Git/backup-history concerns separately before
sensitive live use. Complete the guide's real-host release gate before invitations.

## Hosted recovery: missing database migrations on Render Free

Recorded from the November 4, 2026 incident. The owner-provided logs confirmed
that migrations `0035` through `0040` were pending. All six subsequently finished
with `OK`, and Render reported the service Live. Client-list and save checks are
still required after deployment; a Live status alone does not verify those flows.

### Why pushing code did not update the database

Git push sends application code and migration files to GitHub. Render then builds
and runs the code from its connected branch. In this deployment, that process
does **not** automatically run Django migrations against the hosted Neon database.

- `makemigrations` creates migration files during development. Include those files
  in the commit when a model change requires them.
- `migrate` applies the existing migration files to the selected database. Applying
  them locally does not apply them to Neon; these are separate databases.

On November 4, the application expected the VAT/Non-VAT field, but the hosted
database lacked the column created by `0038_client_tax_registration`. The logs
reported:

```text
django.db.utils.ProgrammingError: column clients.tax_registration does not exist
```

Both `/api/clients/` and `/api/financial-records/clients/` failed while reading
clients. This prevents the lists from displaying; it does not by itself prove
that existing records were deleted. An earlier audit entry also does not establish
whether a later save succeeded. Check existing clients after recovery before
entering the same client again.

### 1. Confirm the error and preserve the working startup command

Open the failed request in Render's Logs and read the final exception line.
`Internal Server Error` alone is not enough to diagnose missing migrations.
If the error concerns a missing column or table, check migration status below.
If it concerns another cause, investigate that cause before applying changes.

Before editing Settings, copy the current working Start Command somewhere safe.
The owner's full working command for this incident was:

```sh
env GUNICORN_CMD_ARGS="" SAFEBOOKS_ALLOWED_HOSTS="${SAFEBOOKS_ALLOWED_HOSTS:-$RENDER_EXTERNAL_HOSTNAME}" gunicorn --config gunicorn.conf.py safebooks.wsgi:application
```

Preserve the complete command when restoring it. The prefix clears extra
`GUNICORN_CMD_ARGS` options and supplies Render's hostname when
`SAFEBOOKS_ALLOWED_HOSTS` is unset or empty. A shorter plain Gunicorn command
relies on the environment already supplying the same required configuration.

### 2. Check hosting configuration before the migration command

In Render, open the SafeBooks service's **Environment** page. Ensure the key
`SAFEBOOKS_ALLOWED_HOSTS` has this value for the recorded usability site:

```text
safebooks-usability.onrender.com
```

Use the actual public hostname if the site address changes. Do not include
`https://`, a trailing slash, quotation marks, or a wildcard. Preserve existing
database credentials, signing keys, Redis configuration, and email settings.

During the incident, the first checking deployment failed with:

```text
Production requires SAFEBOOKS_ALLOWED_HOSTS in hosting environment secrets.
```

The hostname fallback in the normal command applies only to the Gunicorn process.
It does not configure a preceding `python manage.py ...` command. That is why the
hostname must be available in Render's Environment for these management commands.
Save the environment change and deploy; do not switch to development settings to
bypass a production configuration error. If another required variable is missing,
correct it privately using the hosting configuration described earlier in this guide.

### 3. Read migration status without paid Shell access

On Render Free, use **Settings → Build & Deploy → Start Command** temporarily.
Paste the following as **one line**, without adding surrounding quotation marks:

```sh
python manage.py showmigrations safebooks --settings=safebooks.settings_production && env GUNICORN_CMD_ARGS="" SAFEBOOKS_ALLOWED_HOSTS="${SAFEBOOKS_ALLOWED_HOSTS:-$RENDER_EXTERNAL_HOSTNAME}" gunicorn --config gunicorn.conf.py safebooks.wsgi:application
```

Click **Save Changes once**. Saving the command triggers a deployment. Open that
deployment's logs, rather than repeatedly saving or starting more deployments.
After the build, the command prints a list such as:

```text
[X] 0034_account_case_insensitive_unique
[ ] 0035_financialrecordline_worksheet_amounts
[ ] 0036_financialrecordline_remarks
[ ] 0037_financialrecordline_coverage_frequency
[ ] 0038_client_tax_registration
[ ] 0039_client_details_lock_opt_in
[ ] 0040_bookkeeper_verification_proof
```

`[X]` means applied; `[ ]` means pending. This command only checks status, then
starts the web server. Wait for the deployment status to become **Live** or
**Failed**. The log stream stays open while Gunicorn runs; that is normal. If
Deploying lasts more than about ten minutes, inspect the latest logs instead of
continuing to wait or repeatedly redeploying.

If `0038` is already marked `[X]` but its column is missing, stop and investigate
the migration-history/schema mismatch and the database selected by the service.
Do not use `--fake` or manually add the column to hide the mismatch.

### 4. Apply the reviewed pending migrations

The following command is the **specific recovery command used for the November 4
incident**, when only `0035`–`0040` were pending. Those reviewed migrations add
worksheet fields, line remarks, coverage, tax registration, the opt-in lock
default, and the proof table; they do not reset the database or recalculate saved
financial amounts. They update migration history, add defaults for new fields,
and can acquire schema locks. Use an appropriate maintenance window and the
existing hosted backup/recovery arrangements.

```sh
python manage.py migrate safebooks 0040_bookkeeper_verification_proof --noinput --settings=safebooks.settings_production && env GUNICORN_CMD_ARGS="" SAFEBOOKS_ALLOWED_HOSTS="${SAFEBOOKS_ALLOWED_HOSTS:-$RENDER_EXTERNAL_HOSTNAME}" gunicorn --config gunicorn.conf.py safebooks.wsgi:application
```

Set this as the temporary Start Command, save once, and inspect the new deployment's
logs. Each pending migration should finish with `OK`, followed by Gunicorn startup
and Render's **Live** status. The `&&` starts Gunicorn only if migration succeeds.

**For a future update, do not blindly reuse the `0040` target.** Review the actual
pending migration files and their dependencies, and select the appropriate forward
target. Targeting an older migration can reverse newer migrations. If necessary,
temporarily run `python manage.py migrate safebooks --plan --settings=safebooks.settings_production`
before the normal startup command to inspect the plan without applying it. New
migrations may have different data or availability consequences.

If migration fails, stop and inspect the error. Some earlier migrations may already
have committed. Do not delete tables, reset the database, run `makemigrations` on
the host, use `--fake`, or issue manual repair SQL as a substitute for diagnosis.
`No migrations to apply` with the same missing-column error needs investigation,
not repeated execution.

### 5. Restore normal startup and verify the feature

After successful migration, restore the **full original Start Command** saved in
step 1. For the recorded deployment, it is:

```sh
env GUNICORN_CMD_ARGS="" SAFEBOOKS_ALLOWED_HOSTS="${SAFEBOOKS_ALLOWED_HOSTS:-$RENDER_EXTERNAL_HOSTNAME}" gunicorn --config gunicorn.conf.py safebooks.wsgi:application
```

Save and wait for the resulting deployment to become Live. Do not leave migration
commands in the permanent startup command: this recovery runs before one Gunicorn
master, not separately inside web workers or application imports.

Then verify the hosted application:

1. Refresh Clients and Financial Records; confirm existing clients load.
2. Clear search/status filters if a particular client is not visible.
3. Check whether an earlier save succeeded before entering the same client again.
4. Save one clearly fictitious test client, then refresh and confirm it remains
   visible in both client directories.
5. Check the latest logs for another error before asking the bookkeeper to resume
   testing. If other affected features changed, check those flows too.

No new code commit is required merely to change these Render settings. Future
releases that contain new migration files still need a planned hosted migration
step in addition to pushing code. Successful migration and Live status confirm
schema application/startup, not complete user-workflow verification.

References: [Render deployments](https://render.com/docs/deploys) and
[Render environment variables](https://render.com/docs/configure-environment-variables).

### Release 0041: Encrypt client email and ORUS passwords

1. Generate a **new** Fernet key privately in a trusted terminal with
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   after installing the pinned requirements. Save it as the Render secret
   `SAFEBOOKS_CLIENT_CREDENTIAL_KEY` and keep a secure recovery copy. Use a
   different key for local development. Keep each database paired with its key.
2. Plan a maintenance window and stop client writes while applying this
   release. Keep a protected pre-migration database backup. It contains the
   original readable passwords and needs restricted access.
3. Build the release with its updated requirements and apply
   `python manage.py migrate --noinput --settings=safebooks.settings_production`
   against the hosted database with the key set. If using the temporary Start
   Command procedure above, keep the original Gunicorn command after the
   migration command with `&&`. Restore the original Start Command after the
   migration succeeds. Start the updated application code only after applying
   migration 0041.
4. Verify Client Details with an authorized bookkeeper using a test credential.
   Check that the database contains ciphertext and that the application can
   save and reveal the test value. Migration 0041 is irreversible through Django.
   Preserve the configured key for recovery and follow the database recovery
   procedure if rollback is needed.
