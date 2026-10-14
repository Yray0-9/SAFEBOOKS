# SafeBooks usability-testing deployment guide

## Where we are now

The approved analytics-query, failure-state and forecast-workload fixes and their
isolated verification are complete. The remaining limitations are recorded in
[the Step 10 local report](Changes/Verification/step10_local_preparation_2026-10-12.md).
Hosting, real email delivery, provider backups, HTTPS/proxy trust, monitoring alerts
and hosted capacity are **not yet verified**. You will own the hosting accounts
and perform their setup; we will work through the provider-specific steps together.
Do not invite users based only on passing local tests.

Your current local records are test data. Start with a **fresh usability database**;
do not upload `db.sqlite3`, local PostgreSQL data, archived backups, `.env`, or the
disposable accounts used by the automated/browser tests. Migrations create the
application schema; they are not an instruction to import your local test records.

For the first trial, use fictional client details and transactions. Do not enter
real client email/ORUS passwords: credential-at-rest encryption and prior private
backup/Git-history concerns require separate resolution before sensitive live use.

## 1. Choose services before changing anything

The selected services must meet the actual requirements in [DEPLOYMENT.md](DEPLOYMENT.md):

- Supported Linux Python runtime and a clean build of the pinned dependencies.
- Durable managed PostgreSQL with encrypted connections and an appropriate role.
- One authenticated TLS Redis primary shared by every worker, not a REST-only
  endpoint, read replica or per-process memory cache.
- HTTPS with a documented, verifiable reverse proxy.
- Verified TLS/SSL SMTP sender for registration/reset/approval emails.
- Backup storage, restore access, logs/alerts, and enough CPU/memory/connections.

Check the chosen plan's sleep/expiry, storage, connection, email, backup and resource
limits. Do not assume a free plan includes permanent data retention or backups.
No provider has been selected or provisioned by this work. Google OAuth is optional;
its hosted callback and disabled-state feedback must be checked if offered to users.

Record these decisions privately before inviting testers:

| Decision | Must be filled in for the actual host |
| --- | --- |
| Hosting provider and environment | Separate usability/staging service, not localhost |
| Hosted database/cache | Fresh database and separate cache namespace |
| Public hostname and trusted proxy | Exact host, HTTPS, verified forwarding behavior |
| Backup owner and location | Who checks failures; encrypted private storage |
| Maximum acceptable data loss (RPO) | Agreed backup/PITR interval, not an assumed promise |
| Maximum acceptable downtime (RTO) | Recovery objective proven by a hosted restore drill |
| Retention and end-of-trial deletion | How long trial data/backups stay and who approves deletion |
| Alert recipient | An actual monitored address/channel, with a received test alert |

## 2. Prepare the code and hosting secrets

Review and push the tested `deployment-readiness-fixes` branch yourself. Do not
merge into `main` simply to deploy a trial. Confirm that the deployed commit contains
the fixes and that no `.env`, database, private backup or real credentials are
included. Historical private database objects in Git need separate review before
making a repository public; ignoring a file does not remove its history.

Set hosting variables through the provider's protected secret settings, using the
names in `DEPLOYMENT.md`. Never paste secret values into chat, Git, screenshots,
public logs or shell-history commands. Keep a protected inventory of secret names
and a secure recovery method for their values outside the database backup.

Production must explicitly use `safebooks.settings_production`; it ignores the
developer's `.env`. Never enable DEBUG, development signing keys, local-memory
authentication cache or HTTP-only cookies on the public trial. Only trust forwarded
HTTPS headers after checking the provider's proxy isolation/overwriting behavior.

## 3. Build and initialize the fresh hosted database

Follow the build/release commands in `DEPLOYMENT.md` **on the selected host**, not
against your current local database:

1. Install `requirements.txt` in a clean runtime and run `pip check`.
2. Collect production static files before page/startup checks.
3. Run `check --deploy` and investigate its results. The current HSTS warning is
   documented as pending verification; do not silence it as if HTTPS were proven.
4. Review the migration plan, then run migrations once as an approved release step.
   Do not run them automatically in every web worker or import a local test dump.
5. Run the production PostgreSQL/Redis readiness command.
6. Start Gunicorn with the supplied configuration; do not host with `runserver`
   or the synthetic WSGI/Redis test harness.

Create your first administrator using the existing interactive command on the
fresh hosting database:

```sh
python manage.py create_admin_account --settings=safebooks.settings_production
```

Enter a valid admin email/name and the password privately when prompted. Do **not**
use the `--password` argument, which can expose it in command history/process lists.
Do not create a shared public admin or copy test fixture credentials. Verify admin
sign-in and set up 2FA privately. Have testers register their own accounts and
approve the intended accounts through the normal admin workflow.

## 4. Verify the hosted application before invitations

- Confirm HTTPS works without redirect loops, cookies are secure and static assets
  load. Test the target Python/runtime/database versions, not just this Windows PC.
- Check one approved and one unapproved account; verify registration, real email
  verification, password reset, 2FA and session revocation with disposable accounts.
- Use two separate users to verify client/record ownership and absence of credential
  leakage. Lists/reports must not expose saved passwords/private custom fields.
- Create/edit/delete synthetic financial entries and check totals, revisions,
  conflict feedback and audit history. Confirm failed writes preserve drafts.
- Check report current-year defaults, explicit year/All Years, password-free
  print preview and real browser print/PDF behavior.
- Check mobile/desktop layouts, analytics loading/error/recovery and forecasts.
- Verify real inbox delivery/failed-delivery behavior; backend acceptance alone
  is not inbox confirmation. Do not trigger notifications to real clients in a drill.
- Measure simultaneous users and expensive operations on the chosen plan. The
  approved limits bound work but do not guarantee response time. Start with the
  documented small worker/thread configuration and check memory/CPU/DB connections.

## 5. Backups during usability testing

This is protection for **new hosted trial data**, not an obligation to migrate your
local test data. Prefer the provider's supported automated backup/PITR facilities
for routine recovery, with a separately verified logical export/restore drill.
`pg_dump` exports one database; it is not a backup of hosting secrets or database
roles. See [PostgreSQL backup guidance](https://www.postgresql.org/docs/18/backup-dump.html).

- Confirm the real backup job runs, retention matches the agreed policy, and someone
  receives/checks failure alerts. “Backup enabled” is not a successful restore test.
- Keep backups encrypted and access-restricted, separate from the application disk
  and Git repository. A compressed custom dump is **not encryption**. Backups can
  contain password hashes, 2FA secrets, client credentials and financial data.
- Take a verified recovery point before migrations or risky releases. Record its
  time/version privately so you know what changes a restore may lose.
- Store hosting secrets/connection and key-recovery procedures separately in a
  protected vault. Do not place passwords in dump/restore command arguments.

For a trusted logical dump, only after a private PostgreSQL connection service has
been configured for the chosen host, the command shapes are:

```sh
# Templates only: configured connection services must identify verified targets.
pg_dump --format=custom --file="<private-backup-file>" --dbname="service=<private-source-service>"
pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname="service=<fresh-isolated-restore-service>" "<trusted-private-backup-file>"
```

The restore service must point to a newly created **isolated** database, never the
live trial database. Do not add `--clean`/overwrite flags. Restore only trusted
backups: restored SQL can execute code from its source. Verify permissions/roles
after restoration; the example intentionally does not copy old ownership/ACLs.
See [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) and
[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

Test actual hosted recovery: compare the recovered schema/migrations, clients,
records, detail totals, ownership, audit history, constraints and sequences, then
run private application smoke tests with emails/integrations disabled or isolated.
Prove the recovery objective using hosted data volume and provider permissions.
The local synthetic drill does not certify those services or backup retention.

## 6. Monitoring and failure response

Existing server logs and `check_deployment_services` are useful building blocks;
they are **not an already configured continuous monitoring/alert service**.

- Configure an external HTTPS availability check for a public non-sensitive page
  such as `/login/`. Check response status, TLS certificate and redirects.
- A public page returning 200 does not prove PostgreSQL/Redis are healthy. Run the
  existing protected service probe through an approved private operational job;
  do not expose DB credentials or a diagnostic endpoint publicly.
- Alert on application errors, sustained latency, worker restarts, memory/CPU,
  database connections/storage, Redis failures/eviction, and backup failures.
- Confirm an actual test alert reaches its recipient. Choose thresholds after
  measuring the host; do not copy local timings as service guarantees.
- Keep alerts/logs free of passwords, codes, cookies, tokens, database URLs, raw
  request bodies and client-identifying query strings. Existing access-log defaults
  intentionally avoid those query strings; do not turn verbose logging on blindly.
- Record a received email-delivery failure/test and its response, not just a
  “sent” label. Give testers a clear way to report usability failures privately.

## 7. Recovery/rollback procedure

If a trial deployment fails, stop invitations/new writes as appropriate, preserve
the healthy database/recovery point and investigate. Do not reset/drop the hosted
database as an automatic retry.

1. Obtain approval for the exact recovery target and maintenance window. Record
   the backup time and expected lost work. Keep the recovered app private/offline.
2. Restore a trusted backup to a **new isolated database** and verify it first.
3. Before reopening, invalidate restored sessions, pending verification/reset/2FA
   state and authentication grants. Plan a fresh signing key and a fresh isolated
   auth-cache namespace consistently across workers; merely incrementing an older
   restored version can collide with versions used after the backup.
4. Reconcile account/security changes made after the backup, including password
   resets, 2FA/recovery changes, suspensions and access preferences. Old password or
   approval state can return in a raw restore. Require credential recovery for
   affected users and do not reopen accounts whose current state is unknown.
5. Verify schema/code compatibility, restricted-role permissions, totals/audits,
   fresh sign-in, isolation, delivery and service checks before an approved cutover.
6. Retain the old database/recovery point privately until sign-off; remove temporary
   clones/backups only under the agreed retention/deletion policy.

A code rollback must use an approved **security-fixed**, schema-compatible revision.
Do not revert to an older insecure `main` just because it starts. Do not assume
rolling back code requires reversing migrations or restoring the database. On a
first deployment with no known good secure release, keeping staging closed and
fixing forward is safer than an unreviewed rollback.

## Release gate

Mark each item verified on the real host before inviting users:

- [ ] Tested commit deployed; no local test data/secrets imported.
- [ ] HTTPS/proxy/cookies/static files and target runtime verified.
- [ ] Durable PostgreSQL and one authenticated TLS Redis primary verified.
- [ ] Correct admin/tester access, 2FA/reset/revocation and ownership verified.
- [ ] Real SMTP delivery and safe failures verified; optional OAuth verified or clearly unavailable.
- [ ] Current-year reports/print behavior and browser/device flows verified.
- [ ] Host capacity measured with expected simultaneous users and forecasts.
- [ ] Private automated backups, retention and received failure alerts verified.
- [ ] Hosted isolated restore, security invalidation and recovery objective proven.
- [ ] Monitoring alerts, support contact and rollback plan verified.
- [ ] Real-sensitive-data storage/privacy/Git-history concerns separately resolved.

**Current status: ready to work through provider-specific staging setup, not a
completed hosting/recovery certification or approval for sensitive live use.**
