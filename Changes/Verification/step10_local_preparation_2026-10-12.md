# Step 10: approved analytics fixes and local deployment/recovery preparation

Completed local follow-up on 2026-10-12, on `deployment-readiness-fixes`.

## Verdict

**Local approved fixes and isolated verification complete; hosting sign-off still
requires verification.** This is preparation for an owner-operated usability
deployment, not a completed deployment or a certification for sensitive live data.

The earlier [Step 9 assessment](step9_deployment_verification_2026-10-12.md) is the
pre-fix baseline. This follow-up addressed its dense analytics timeout, misleading
schedule/report failure states, and excessive repeated forecast fitting. It also
exercised a real PostgreSQL logical backup/restore in isolation and prepared
[the hosting/backup/monitoring/recovery guide](../../USABILITY_DEPLOYMENT.md).

No hosting accounts were created, no real emails sent, and no hosting settings or
services changed. The normal PostgreSQL database was not accessed. `.env` and the
local SQLite file retain their baseline hashes. There was no migration, financial
data rewrite, route change, Git commit/push, branch switch or unrelated plan edit.

## Scope and safeguards

- Followed `AGENTS.md` and the financial-records skill: traced the financial
  models/services, owned analytics boundary, forecasting inputs, connected client
  detail/report behavior and regression tests. The skill kept money, periods,
  ownership and persistence rules unchanged.
- User approved safe analytics JSON 503 plus coordinated unavailable UI, and
  request-local fit reuse plus the combined 8-fit/960-observation budget.
- Independent PostgreSQL 18.3 on loopback port 55439, in an explicitly disposable
  `safebooks-step9-final-*` directory. Harness checks `SHOW data_directory` before
  operating. Never used the existing PostgreSQL service or port 5432.
- Suppressed `.env` loading; permitted only the isolated PG/cache/HTTP endpoints.
  Dummy/locmem email and isolated OAuth settings prevented external delivery.
- Functional suite used fast fixture hashing only. Browser/load fixtures used the
  application's real configured password hasher. No test credentials were added
  to the normal application database or production configuration.
- Two isolated Windows Python WSGI processes with two active slots each and a
  shared Redis-protocol emulator. This does not validate Linux Gunicorn, TLS
  Redis, HTTPS/proxy behavior, or any hosting provider.
- Initial browser/load fixtures: 10 synthetic bookkeepers, 100 clients, 3,300
  records and 6,600 details. Boundary fixtures added two synthetic owners, one
  dense client and twenty forecast clients. All of these were disposable.

## Changes and user-visible behavior

### Dense workflow query

Workflow counts now use a grouped query and a separate bounded latest-record
batch on record rows, not a correlated latest-record lookup per joined detail.
Latest ordering still uses period, entry date and ID; a later backdated insertion
cannot incorrectly win the entry-date tie-break. Owner/client scoping remains.

Client analytics query count is constant **5/5** for 1 versus 30 records/clients.
The additional bounded query replaces the expensive shape; a lower query count
alone would not prove better performance. Workflow metadata remains usable when
the financial history is narrowed to a year.

### Failure states

- Analytics-service database errors produce HTTP 503, `code: analytics_unavailable`,
  no-store JSON and no partial money/workflow. Logs contain the error class only,
  not the database exception message or private connection information.
- Client Details shows `Checking` while loading and `Not loaded` / `Schedule
  unavailable` on failure. It does not assert that a monthly record is missing
  until valid workflow data has loaded. A successful narrowed request restores
  the real schedule state.
- A failed report preview says `Preview not loaded`, retains usable year controls
  and keeps printing disabled. Existing stale-response/cancel protection remains.
- This catch is at the analytics-service boundary. A total database outage during
  session/auth middleware before the view is not claimed to be covered by it.

### Forecast work

Identical frequency/history/projection inputs share an immutable model result
only within the current request. Returned per-client models are separate copies;
there is no global cache or cross-user/request result reuse. Existing SARIMA
order, optimizer, iterations, monetary rounding and contribution rules remain.

Before any fit, reject more than **8 distinct eligible histories** or **960 total
observations across those distinct histories**. Histories that are unsupported,
irregular, incomplete or do not need a future fit do not consume this fit budget.
The existing limits remain: 5,000 records, 20,000 details, 60 series, 240
observations per series, and horizon 1-12 months. Oversized requests return the
existing controlled workload error with owned selector metadata, not truncated
data or partial financial totals. Narrowing controls remain available.

These guards are work bounds, not CPU/time/memory service guarantees.

## Completed automated checks

| Check | Result |
| --- | --- |
| Full suite before final additional API regression | 435 tests passed on disposable PostgreSQL; no skips; 87.841 seconds |
| Final full suite | **436 tests passed**, no skips; **86.457 seconds** |
| Django system check through isolated harness | No issues |
| Model/migration consistency | No changes detected |
| JavaScript regression scripts | All five passed: auth enforcement, client privacy, financial reliability, settings/logout, workload/report behavior |
| Final interrupted-turn continuation | All five JS scripts passed again; seven scoped Python files passed AST syntax checks without generating bytecode |
| Dependency consistency | Project virtual environment `pip check`: no broken requirements |
| Diff whitespace | Passed; Git's existing LF/CRLF warnings are not failed checks |
| Constant query counts, 1 vs 30 | Dashboard 3/3; both directories 1/1; records 5/5; reports 4/4; analytics 5/5 |

The full suite includes the prior reset/2FA/session, ownership/privacy, financial
validation/CRUD/revision/atomic audit, account-constraint migration, admin approval,
dashboard/report/settings and SARIMA regressions. Ten new resilience tests cover:
dense reads under a PostgreSQL 5-second per-statement timeout; backdated ordering
and foreign-owner exclusion; safe 503 and private-log redaction; unauthenticated
denial; API workload rejection without fitting/partial money; identical-fit reuse;
8/9-fit and 960/1,000-observation boundaries; insufficient histories; independent
model copies and no reuse across requests.

An initial focused run had four errors because the new in-memory forecasting
fixture lacked `period_id`. The fixture was corrected, not application behavior;
the completed PostgreSQL runs above then passed. Deliberate fault-injection log
messages in the suite are not unreported test failures. No test is claimed to have
passed merely because it was started.

## Cross-process and load results

Five HTTP edit races across the two workers each produced one HTTP 200 and one
HTTP 409. Stale delete was rejected; latest-revision delete succeeded. Totals
equaled detail sums, with exactly 15 expected financial audit entries. CSRF-less
writes were rejected 403 and foreign-owner record reads 404. Logout-cookie replay
and durable session-version revocation were rejected by the other worker.

| Isolated load | Requests | Median | p95 | Maximum | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 user, mixed ordinary reads | 20 | 80.0 ms | 223.8 ms | 223.8 ms | No errors |
| 5 users, mixed ordinary reads | 100 | 168.4 ms | 286.5 ms | 354.2 ms | No errors |
| 10 users, mixed ordinary reads | 200 | 353.1 ms | 440.0 ms | 548.1 ms | No errors |
| 5 users, real SARIMA requests | 10 | 2,318.7 ms | 2,585.0 ms | 2,585.0 ms | No errors; actual SARIMA asserted |

All **330 requests** passed response/owned-data assertions. These short local
loads do not prove long-duration stability, peak memory, arbitrary histories or
free-host capacity. Four local active request slots are not the same capacity as
the documented initial hosting worker/thread configuration.

## Large permitted workloads

| Workload | Before (Step 9) | After, actual execution |
| --- | --- | --- |
| 5,000 records / 20,000 details in one period | Query timeout at 15 seconds; HTTP 500 | Complete analytics totals/workflow; 7.53 seconds during competing work, 3.90 seconds on a separate repeat |
| 60 monthly series, 240 observations each, 12-month horizon | About 38.78 seconds; 60 fits | Three distinct real fits reused across the series; 10.44 seconds, then 10.48 seconds on repeat |

The larger forecast fixture has twenty clients, 4,800 records and 14,400 details,
with three identical category histories per client. More distinct histories are
rejected by the new combined guard. The repeated fixture is favorable to reuse;
it is not a claim that every allowed eight-fit history will complete this quickly.
Both dense and forecast repeats returned complete valid results. No stored
history was shortened to achieve the timings.

## Browser verification

Used only the isolated app with synthetic accounts, at desktop 1366x900 and mobile
393x852 (reported inner width around 394). Verified Client Details:

- One-over 5,001-record request showed the workload error and `Not loaded`, not
  `Needs record` / a false missing-month claim.
- Oversized report preview retained year narrowing and disabled printing; no
  misleading `Loading years` hint remained after failure.
- Closing the modal and choosing a narrower year recovered the valid workflow
  and cleared the error. The controlled one-over test sentinel was removed only
  from the synthetic fixture; a repeat 5,000-record read displayed sales
  20,000.00 and a ready workflow with all 20,000 details.
- No horizontal overflow in the affected mobile state (document width 378,
  viewport about 394) or final desktop state (1351 versus 1366). Browser console
  errors were empty in the checked state.

The full earlier page baseline remains in Step 9. No CSS was changed here and no
claim is made to have retested every page/device. Some browser-tool waits
timed out while analytics was still loading; later observation confirmed the
completed successful response. Tool wait timeouts were not treated as successful
checks or hidden application failures.

Screenshot evidence is retained outside the repository in the task's visualization
folder as `final-schedule-unavailable.jpg`, alongside the earlier mobile conflict
proof. These are synthetic test data, not deployment assets.

## Backup/restore and service probe

Used installed PostgreSQL 18 `pg_dump` and `pg_restore` on the verified disposable
cluster. Restored a custom archive into a **new**, absent-target database; never
overwrote the source or any existing database. Compared primary-key-ordered
fingerprints of every table and checked financial totals, owner/period
relationships, case-insensitive uniqueness and insert sequences.

The final enhanced drill compared **20 tables**, including financial audit and
session rows; archive size **768,673 bytes**; elapsed **10.24 seconds**. The source
fingerprints remained unchanged. On the restored clone only, cleared sessions and
incremented account security versions; an actual restored synthetic session proof
was invalid afterward. The clone and temporary dump were removed by the helper.

That proves a local logical recovery of synthetic data, not provider backup
automation, retention, permissions, RPO/RTO or safe live cutover. Raw backups can
restore old passwords, 2FA, approval state and authentication grants. Before a real
recovered app reopens, use fresh signing/auth-cache state consistently and reconcile
security changes after the backup; incrementing a rolled-back counter alone can
collide with versions already used. Those operations require an approved recovery
plan and were not performed on the normal database.

The existing deployment service command also passed SQL `SELECT 1` and isolated
cache add/get/increment/delete checks using disposable PG and a Redis-protocol
emulator. The probe was permitted by test overrides, not an actual production
profile/TLS connection. Continuous monitoring or a received external alert was
not configured; the guide explains how the owner must verify them on the host.

## Remaining limitations / release requirements

1. Choose/provision the host, fresh managed PostgreSQL and authenticated TLS Redis.
   Verify Linux Python/dependency build, Gunicorn, static files, connection budgets,
   HTTPS, proxy header trust and secure cookies on that exact environment.
2. Verify actual SMTP inbox delivery/failures and optional Google OAuth callbacks.
   Tests intentionally did not send email or contact third-party services.
3. Configure and receive monitoring/backup failure alerts; verify private encrypted
   backups, retention and a hosted isolated restore with agreed recovery objectives.
4. Measure peak memory, CPU, connection use, sustained traffic, distinct/volatile
   forecast histories and target simultaneous users. The heavy forecast still takes
   about 10.5 seconds on this PC and may be unsuitable for a small free tier.
5. Review client-credential encryption at rest and historical private backup/Git
   objects before sensitive live use or making the repository public. Neither was
   changed in this scope. Start usability trials with fictional data/credentials.
6. Historical low-priority findings remain: hidden desktop tooltip overflow in some
   earlier pages and initially blank client heading on an oversized hand-written
   ID-only financial URL. Generated links carry identity metadata. This follow-up
   did not expand into those unrelated layout/URL fixes.
7. Printed/PDF output, actual target devices/networks, total infrastructure outages,
   provider restore privileges and real security-state reconciliation still need
   hosted/manual verification. No production-safe guarantee is inferred from tests.

## Files changed by this follow-up

- `safebooks/services/analytics_service.py`: bounded workflow latest batch and
  request-local forecast reuse/combined work guard.
- `safebooks/services/forecasting_service.py`: fit eligibility/cost planning only.
- `safebooks/services/workload_limits.py`: the two approved combined constants.
- `safebooks/views.py`: safe analytics-service database error boundary.
- `templates/base/client_details.html`: honest loading/unavailable/recovery states
  and failed-preview hint, preserving report controls and financial form handlers.
- `safebooks/tests/test_analytics_resilience.py` (new), `test_query_growth.py`,
  `safebooks/tests/js/test_workload_limits.cjs`: targeted regressions.
- `safebooks/tests/deployment_probe.py`: opt-in synthetic boundary/recovery modes;
  never the production server, scheduler, cache or backup job.
- `AGENTS.md`, `DEPLOYMENT.md`, `USABILITY_DEPLOYMENT.md` (new), this report, and a
  historical-report follow-up link: lasting rules and owner-operated handoff.

Unrelated existing feature-branch edits, including the user's planning document,
were preserved. Do not interpret this list as all changes accumulated in Steps 1-8.

## Cleanup and continuation after interruption

The completed 436-test run, load/concurrency checks, browser observations and
restore drill were not restarted solely because the turn was interrupted. Saved
code/results were reviewed; dependency/diff checks were repeated. The independent
services had already stopped: ports 55439, 8541, 8542 and 56379 had no listeners,
and `pg_ctl status` confirmed no disposable PostgreSQL server running.

Removed only the exact stopped generated `safebooks-step9-final-*` directory after
checking its resolved path, absence of reparse points and empty tablespace links.
Synthetic accounts/data are no longer present; fixtures can be regenerated. The
normal project/database files were not cleanup targets. One inaccessible offline
test browser tab could not be bound under the browser security policy; no bypass
was attempted. It may be closed manually and has no running test backend.

Next: the owner selects hosting services; use `USABILITY_DEPLOYMENT.md` to complete
provider-specific staging setup and the real-host release gate before invitations.
