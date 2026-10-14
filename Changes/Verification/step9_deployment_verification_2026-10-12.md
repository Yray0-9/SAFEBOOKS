# Step 9: isolated deployment verification

Assessment completed 2026-10-12; initial measurements were taken on 2026-10-11.

This is the historical, pre-fix assessment. The subsequently approved fixes,
436-test PostgreSQL run, repeat load tests and synthetic restore drill are in
[the Step 10 local report](step10_local_preparation_2026-10-12.md). Results below
are retained as the original baseline, not a claim that those fixes remain undone.

## Verdict

**Not ready for deployment sign-off.** The complete automated suite and ordinary
multi-user flows passed, but permitted large analytics workloads exposed an
unhandled database timeout, expensive forecasts, and misleading schedule UI after
an analytics failure. Address those findings and re-test before accepting the
workload limits for low-resource hosting. Hosted infrastructure remains Step 10.

No application code, financial rules, routes, models, migrations, production
settings, current database, or `.env` was changed in Step 9. The only repository
changes are the opt-in test harness, this report, and the deployment-document link.

## Isolation and coverage

- Independently initialized PostgreSQL 18.3 cluster in a dedicated temporary
  `safebooks-step9-*` directory, listening only on loopback port 55439. Every
  harness process verifies `SHOW data_directory` before operating. Never used
  the existing PostgreSQL service/database or port 5432.
- The full suite creates and destroys only `test_safebooks_step9_suite` in that
  temporary cluster. No test exclusions or skips. External connections blocked;
  only the disposable database/application/cache-emulator endpoints permitted.
- Test settings suppress `.env` loading. Functional suite uses fast MD5 fixture
  hashing; browser and HTTP load fixtures use the actual configured password
  hasher. MD5 is never installed into application/production configuration.
- Separate browser/load database initially contained 10 synthetic bookkeepers,
  100 clients, 3,300 records, and 6,600 details. Additional boundary fixtures
  were synthetic only. Email used dummy/locmem test backends; no real delivery.
- Two isolated Python WSGI processes, each with two active request slots. Both
  use PostgreSQL sessions and one disposable Redis-protocol emulator. This is
  not Linux Gunicorn, HTTPS, a hosting proxy, or real TLS Redis certification.
- The in-app Chromium browser used only the isolated port 8541 app. Desktop
  viewport 1366x900 and mobile override 393x852 (reported inner width about 394).

## Completed results

| Check | Evidence/result |
| --- | --- |
| Full Django suite, first run | 426 tests; all passed, no skips; 70.964 seconds |
| Full suite after interrupted-session recovery | 426 tests; all passed, no skips; 120.044 seconds |
| Django system check | No issues |
| Model/migration consistency | No changes detected |
| JavaScript checks | All five standalone scripts passed: auth enforcement, client privacy, financial reliability, settings/logout, workload/report loading |
| PostgreSQL row-lock concurrency | Same-client creates, competing edits, create/delete cleanup and competing admin approvals passed |
| Cross-process HTTP financial races | Five rounds: one edit HTTP 200, competing edit HTTP 409; stale delete rejected; latest-revision delete succeeded; totals equaled detail sums; exactly 15 financial audit entries |
| HTTP access boundaries | CSRF-less write rejected 403; foreign-owner record read rejected 404 |
| Shared authentication state | Authenticated cookie worked on either worker; logged-out cookie replay rejected on other worker; durable session-version change rejected older session on other worker |
| Query counts, 1 vs 30 rows/clients | Dashboard 3/3; financial/client directories 1/1; records 5/5; report 4/4; analytics 4/4 |
| Typical PostgreSQL query plans | Real `EXPLAIN (ANALYZE, BUFFERS)` on synthetic data; no disk sorts. Dashboard SQL 2.9 ms total; records 0.2 ms; report 0.1 ms; analytics 0.9 ms. These are representative small reads, not upper-limit guarantees |
| Exact history/detail boundary | 5,000 records / 20,000 details: records HTTP 200, 742 ms, about 3.0 MB JSON, complete total 20,000.00; report HTTP 200, 668 ms, about 2.4 MB JSON |
| One-over record boundary | Records/report/analytics returned controlled HTTP 400 `workload_limit`, no partial histories or totals |
| Narrowing recovery | API and real mobile month selector recovered to September 2026, correct zero records and client identity, persistent read-error cleared |

The suite covers authentication/reset/Google/2FA/session security, admin
approval/account management/audit/settings/profile, client APIs/profile locks/
privacy, financial validation/CRUD/revisions/atomic rollback/audits, dashboard,
analytics/SARIMA, reports, migration constraints, settings/delivery/logout, and
workload budgets. It is automated coverage, not proof of every possible flow.
Logged synthetic failure messages are deliberate fault-injection tests, not
unreported suite failures. An initial reusable-harness run failed before tests
because replacing Django's normalized `TEST` dictionary removed `MIRROR`; the
harness was corrected to change only `TEST.NAME`, then all 426 tests passed.

## HTTP load measurements

Each user made sequential requests, alternating between the two processes. The
mixed workload used dashboard, client directory, financial directory, full client
record history, and current-year report APIs. Owner-specific synthetic name
markers were checked in successful responses to detect cross-user leakage.

| Simultaneous users | Requests | Errors | Latest p50 | Latest p95 | Latest maximum |
| --- | --- | --- | --- | --- | --- |
| 1, mixed reads | 20 | 0 | 88 ms | 199 ms | 199 ms |
| 5, mixed reads | 100 | 0 | 230 ms | 472 ms | 539 ms |
| 10, mixed reads | 200 | 0 | 501 ms | 1,024 ms | 1,159 ms |
| 5, real SARIMA reads | 10 | 0 | 3,806 ms | 4,103 ms | 4,103 ms |

Mixed reads were exercised twice. The earlier 10-user p95 was 781 ms; the second
was 1,024 ms. This variation illustrates why local timings are not a capacity
promise. The first analytics probe selected only nine monthly observations and
did not exercise model fitting; it was replaced with All Years / 33 observations
and an assertion that a real SARIMA forecast was returned. Do not use the first
analytics timing as forecast performance evidence. No forecasts were mocked in
the final load probe. Hosted default configuration has one worker/two threads,
less concurrency than the four slots used in this local two-process probe.

## Browser verification

- Login; dashboard queue keyboard activation; automatic client-access password
  modal for the chosen client; incorrect-password feedback; correct confirmation
  opens that exact client's details without a second search.
- Dashboard, Clients, Financial Records directory, client financial records,
  Audit Log, Settings, Profile and Client Details were inspected on mobile.
  The seven directory/account/record pages were also checked at desktop size.
  Completed mobile page reads had no page-wide horizontal overflow.
- Current-year preview contained only 2026 entries (sales 9,000.00, expenses
  1,800.00); explicit 2025 selection gave 12,000.00 / 2,400.00; explicit All Years
  gave 33,000.00 / 6,600.00. No password labels in the preview. Printing disabled
  during year changes. Modal closed by keyboard/close controls.
- Oversized report error kept the year selector usable, hid report output and
  disabled printing. No stale or partial report was printable.
- Financial modal required-field validation, Sales starter, zero-value create,
  saved row/summary/toast, edit open/cancel, and a real stale-edit conflict.
  Another HTTP process saved 9.99 while the mobile draft held 45.67; the stale
  update did not overwrite it, retained amount/description, and showed a clear
  conflict message. Screenshot evidence is stored outside the repository.
- Browser console showed no errors during the normal desktop page sweep. Later
  deliberately rejected workload/conflict requests are expected negative cases.
- `/reports/` redirects to the Clients directory intentionally; reports are
  accessed through Client Details. A standalone reports page is not missing
  because of a failing route.

## Confirmed findings requiring follow-up

### High: permitted dense analytics fails with an unhandled timeout

One synthetic client with exactly 5,000 monthly records in one period and four
details each (20,000 details) passed records/report reads but failed analytics.
The disposable cluster's 15-second statement timeout canceled the grouped
workflow query with PostgreSQL SQLSTATE 57014. Direct service reproduction raised
`OperationalError` in `analytics_service.py:570`, through `bounded_list`, after
22.4 seconds. HTTP reproduction returned 500 and HTML, not the normal JSON error
envelope, after 21.3 seconds. No partial financial result was accepted.

The grouped workflow query contains a correlated latest-record subquery while
joining detail rows. Its constant query count does not bound work within that
query; dense per-period data is the confirmed failing shape. Optimize that
workflow query and add safe timeout/error handling plus a dense PostgreSQL
regression. Do not just remove the timeout or raise the workload limits.

The 15-second timeout is a **test safety setting**, not a newly applied production
setting. A host without such a timeout may hold the request longer instead of
failing quickly; the observed case does not claim ordinary small reads fail.

### Medium/high: permitted forecasts can occupy workers for a long time

A separate synthetic owner with 20 clients, 4,800 records, 14,400 details,
60 monthly series with 240 observations each and a 12-month horizon returned a
real forecast, but took **38.78 seconds** in a single service call. Concurrent
smaller forecasts already reached about four seconds at five users. These
histories were simple, constant values, not worst-case optimization histories.

Re-measure on the intended host and obtain approval for appropriately lower
synchronous limits or an asynchronous forecast workflow. Increasing timeouts
alone does not solve worker saturation. Forecast accuracy is outside this load
assessment; existing numerical regression tests passed.

### Medium: schedule UI claims missing records when analytics is unavailable

For the boundary client after adding a 5,001st October record, analytics correctly
returned `workload_limit`, but Client Details still displayed **Needs record** /
**No monthly record saved for current period**. There were thousands of monthly
October records. `applyClientWorkflowStatus({})` and the analytics-failure path
leave an absence-shaped schedule card visible. Use an unavailable/not-loaded
schedule state on failures, and restore actual schedule data only after success.

### Low: stale report loading hint and hidden desktop tooltip extent

- After a completed oversized-report error, the year hint still said “Loading
  the available bookkeeping years...” although the error was displayed and
  printing was disabled. Replace that stale hint on failure.
- At 1366px, hidden `.safebooks-tooltip-content` extends Settings/Profile document
  width to about 1410/1425px. Visible cards/controls stayed within the viewport
  and body horizontal overflow is hidden. This is not confirmed visible card
  clipping; review edge tooltip positioning/accessibility separately.
- An oversized direct financial-record URL containing only `client_id` initially
  shows blank client identity because failed history supplies no client metadata.
  Identity restores after successful narrowing; normal generated links also
  include display metadata. A lightweight owned identity read would improve
  this direct-link error case.

## Limitations and next decision

Not verified: actual hosting, Linux Gunicorn, hosting proxy/HTTPS trust, real TLS
Redis failover/capacity, real SMTP delivery, live Google OAuth, physical mobile
devices/other browsers, actual print/PDF dialogs, prolonged soak tests, peak
memory/leaks, very large client directories, maximum-sized financial writes, and
slow/lossy networks. OS detailed-process inspection was permission-limited;
do not infer memory capacity from these latency results. Prior at-rest credential
and private-backup/Git-history concerns are not resolved by passing this suite.

Recommended order: optimize dense analytics and safe failure responses; correct
the schedule/report failure UI; verify revised synchronous forecast budgets on
the intended host; repeat affected PostgreSQL/browser/load cases; then complete
Step 10 hosting, monitoring, backup/restore and recovery verification. No fixes
were implemented as part of this testing stage.

## Re-running safely

`safebooks/tests/deployment_probe.py` is an opt-in, non-runtime test helper, not a
page or production configuration. It offers `suite`, `seed`, `serve`, `load`,
`concurrency`, and `plans` modes. Use the project virtual environment and existing
`requirements-dev.txt`; the HTTP probe also uses its installed `requests` library.
Do not run it against the existing project database or a copied production dump.

Initialize a new dedicated temporary PostgreSQL cluster using installed vendor
binaries, loopback only and a non-default port. Its role must be
`safebooks_step9`; create only `safebooks_step9_browser` inside that independent
cluster. Test-only trust authentication is acceptable only for this transient
loopback synthetic cluster, never for deployment. Then:

```powershell
# Replace the placeholder with the verified, independently initialized temp cluster.
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe suite --cluster '<dedicated safebooks-step9-* directory>'
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe seed --cluster '<dedicated safebooks-step9-* directory>'
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe serve --cluster '<dedicated safebooks-step9-* directory>'
# In a separate terminal, while the isolated workers run:
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe load --cluster '<dedicated safebooks-step9-* directory>'
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe concurrency --cluster '<dedicated safebooks-step9-* directory>'
& .\.venv\Scripts\python.exe -B -m safebooks.tests.deployment_probe plans --cluster '<dedicated safebooks-step9-* directory>'
```

Seed refuses non-empty data rather than resetting anything. Full-suite test data
is separate from browser/load fixtures. Stop the isolated workers/cache and
database after verification. The boundary fixtures in this report were additional
explicit synthetic probes, not part of the default seed workload; add repeatable
regressions for these failure shapes during the approved corrective work.

## Final cleanup and file checks

The isolated HTTP ports 8541/8542 and cache-emulator port 56379 were confirmed
closed. The dedicated PostgreSQL cluster was stopped, its exact temporary target
and absence of external tablespaces checked, then only that synthetic directory
was removed. Synthetic data/logs are no longer retained; they can be regenerated.
The browser test tab was closed and its viewport override reset. Screenshot
evidence remains outside the repository. `.env` and `db.sqlite3` hashes matched
their starting values; the configured existing PostgreSQL database was never
accessed. Harness syntax and Git whitespace checks passed. Existing unrelated
work, including the user's plan edit, was preserved; no commit or push was made.
