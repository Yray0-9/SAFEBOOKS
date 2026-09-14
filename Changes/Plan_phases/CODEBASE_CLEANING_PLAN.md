# SafeBooks Codebase Cleaning Plan (Safe, Non-Destructive)

## 1) Objective
Create a careful cleanup path for files and code that do not actively support the current runtime system, without risking regressions.

This plan is intentionally conservative.
No deletion should happen until every item passes the validation gates below.

## 2) Scope And Hard Boundaries
Included in audit:
- Django runtime code (`safebooks/`)
- Templates (`templates/`)
- Frontend static assets (`static/`)
- Root operational files (`manage.py`, `requirements.txt`, etc.)
- Non-runtime artifacts in root/backups

Explicitly excluded from cleanup:
- `PromptUI/` folder (as requested)
- `.venv/` virtual environment internals

## 3) Audit Summary
What was verified:
- All main templates are rendered by active views.
- All CSS and JS files in `static/` are referenced by templates.
- Core API routes and test suites are active and passing.
- Several backup/dump artifacts are present and not used by runtime.
- A few code-level items appear to be optional/legacy and should be handled as medium-risk cleanup candidates.

Additional maintainability finding (important):
- The codebase is functionally valid, but several files are larger than ideal for long-term maintainability.
- Biggest files identified include:
  - `static/css/style.css` (~2951 lines)
  - `templates/base/financial_records_client.html` (~1631 lines)
  - `templates/base/clients.html` (~1158 lines)
  - `templates/base/analytics.html` (~1117 lines)
  - `templates/base/dashboard.html` (~1085 lines)
- Repeated inline JS logic exists across multiple pages (sidebar state, toast helper, cookie parsing, logout flow, auth user hydration).

Conclusion:
- Current structure can run and pass tests, but it is not the best modern/professional shape for scaling.
- A controlled refactor track is recommended before expanding feature breadth aggressively.

## 4) Candidate Cleanup Items

### A) High-confidence non-runtime artifacts (safe cleanup candidates)
These are likely historical export/backup artifacts, not runtime dependencies.

1. `datadump.json`
2. `backups/db.sqlite3.pre_postgres_20260425.bak`
3. `backups/safebooks_data_20260425.json`
4. `backups/sqlite_dump_20260425.json`
5. `backups/safebooks_row_counts_20260425.txt`

Recommended action:
- Move to external archival storage (preferred), or keep in a dedicated local archive outside app workspace.
- Do not delete permanently before archival verification.

Risk level: Low

### B) Medium-risk code cleanup candidates (needs controlled validation)

1. Alias route in `safebooks/urls.py`:
- `path('register/', views.signup_page_view, name='register')`

Observation:
- No internal references detected in templates or Python code.
- Current flow uses `signup/` and API `api/auth/register/`.

Possible action:
- Deprecate then remove `/register/` alias route.

Risk level: Medium (external bookmarked links may still use it)

2. Model registry helper in `safebooks/models/table_registry.py` and export in `safebooks/models/__init__.py` (`ALL_TABLE_MODELS`)

Observation:
- No runtime references detected beyond model package export.

Possible action:
- Keep if intended for governance/migration documentation.
- Remove only if team confirms it has no current or planned tooling usage.

Risk level: Medium

3. Service package export hub in `safebooks/services/__init__.py`

Observation:
- App runtime currently imports service modules directly in `safebooks/views.py`.
- No direct runtime imports of package-level exports detected.

Possible action:
- Keep for API cleanliness, or remove if team prefers strict direct-module imports only.

Risk level: Medium-Low

## 5) Keep (Do Not Clean)
These are active or operationally important and should remain:
- `safebooks/` app code, migrations, and tests
- `templates/` all current HTML pages
- `static/css/*.css`, `static/js/skeleton.js`, `static/images/Logo_safebooks.png`
- `db.sqlite3` (still relevant when SQLite mode is enabled via settings)
- `.env.example` and `requirements.txt`

## 6) Safe Execution Sequence

### Phase 1: Artifact archival only (low risk)
1. Create archive folder outside runtime workspace (or secure storage).
2. Copy all candidate backup/dump files.
3. Verify copy integrity (file size/hash).
4. Remove local duplicates only after verification.
5. Run validation suite:
- `python manage.py check`
- Full API tests currently used in project

### Phase 2: Route deprecation (medium risk)
1. Keep `/register/` for one transition cycle, add note in release log.
2. Monitor whether any external usage appears.
3. Remove alias route in next cleanup cycle if confirmed unused.
4. Re-run checks/tests and manual smoke test for signup/login navigation.

### Phase 3: Optional code hygiene cleanup (medium risk)
1. Team decision on `ALL_TABLE_MODELS` and `services/__init__.py` role.
2. Remove only if no tooling/docs/process depends on them.
3. Re-run tests and smoke checks.

### Phase 4: Structural refactor track (recommended before large new features)
1. Extract repeated frontend utilities from templates into shared JS modules under `static/js/`:
   - sidebar state helpers
   - toast helpers
   - auth user/session helpers
   - common fetch/json helpers
2. Move large inline page scripts into page-specific JS files:
   - `clients.js`, `dashboard.js`, `analytics.js`, `financial_records.js`, `financial_records_client.js`
3. Split oversized CSS into modular files (base/layout/components/page) while preserving visual output.
4. Reduce template size by extracting shared layout fragments (sidebar/topbar) to reusable template partials.
5. Keep behavior unchanged; refactor should be structural only.

Risk level: Medium

### Phase 5: Controlled backend modularization (optional, post-Phase 4)
1. Split large `safebooks/views.py` into focused view modules:
   - auth views
   - page views
   - client API views
   - financial API views
   - analytics/dashboard API views
2. Keep URL names and API contracts unchanged.
3. Re-run full validation gate.

Risk level: Medium

## 7) Modern Development Guardrails (New)
To keep future work professional and maintainable, enforce these thresholds:
- Preferred max file size:
  - Python module: 300-400 lines
  - Template file: 600 lines
  - CSS file: 800 lines
  - JS module: 300 lines
- No duplicated utility logic across page templates.
- New pages should use shared layout partials and shared utility modules by default.
- Any temporary duplication must include a scheduled cleanup task in the active phase plan.

## 8) Validation Gate (Required After Every Cleanup Step)
- `python manage.py check`
- API suite:
  - `safebooks.tests.test_auth_api`
  - `safebooks.tests.test_dashboard_summary_api`
  - `safebooks.tests.test_analytics_summary_api`
  - `safebooks.tests.test_clients_api`
  - `safebooks.tests.test_financial_records_api`
- UI smoke pass:
  - Login, signup, dashboard, clients, financial records, analytics
  - Sidebar navigation
  - Core CRUD and analytics load

## 9) Rollback Strategy
If any regression appears:
1. Restore removed artifacts/code from archive or VCS immediately.
2. Re-run validation gate.
3. Reclassify failed item as "Do Not Clean" until root cause is fully understood.

## 10) Final Recommendation
1. Start with Phase 1 immediately (backup/dump artifact archival) for low-risk wins.
2. Begin Phase 4 structural refactor track before major feature expansion.
3. Use the Validation Gate after each refactor step.
4. Treat route/code removals as controlled, explicit sign-off actions.

## 11) Feature Readiness Gate
Reports page implementation should start only after:
1. Phase 1 completed.
2. At least the high-duplication JS utility extraction from Phase 4 is done.
3. Validation Gate passes fully.

Planning for Reports can proceed now, but build execution should follow this readiness gate.

## 12) Execution Log
### 2026-04-27: Phase 1 cleanup execution (completed)
Completed actions:
1. Archived non-runtime artifacts into:
  - `cleanup_archive/non_runtime_20260427_034851`
2. Verified archive integrity with SHA256 hash comparison before deletion.
3. Removed original files only after hash-match confirmation for all targets.
4. Verified post-cleanup state:
  - Originals absent in root/backups paths
  - Archived copies present under archive root

Validation gate results after cleanup:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 1 (Artifact archival only) is complete and validated.
- No runtime regression detected in required API validation gate.

### 2026-04-27: Phase 4 structural refactor kickoff (safe slice)
Completed actions:
1. Added shared frontend helper module:
  - `static/js/app_shared.js`
2. Updated Dashboard page to use shared helpers for:
  - toast rendering
  - safe JSON parsing
  - cookie access
  - logout flow
  - header auth-user hydration
3. Kept all Dashboard behavior/contracts unchanged (structural extraction only).

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 has started with a low-risk, single-page extraction and full validation.
- Next safe step is to migrate remaining pages one-by-one using the same validate-after-each-step gate.

### 2026-04-27: Phase 4 structural refactor slice 2 (Clients page)
Completed actions:
1. Migrated `templates/base/clients.html` to shared helper usage from `static/js/app_shared.js` for:
  - toast rendering
  - safe JSON parsing
  - cookie access
  - logout flow
  - header auth-user hydration
2. Preserved existing Clients page behavior and API interaction contracts.

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 remains green after the second page migration.
- Next safe step is to migrate another single page and repeat the same full validation gate.

### 2026-04-27: Phase 4 structural refactor slice 3 (Analytics page)
Completed actions:
1. Migrated `templates/base/analytics.html` to shared helper usage from `static/js/app_shared.js` for:
  - toast rendering
  - safe JSON parsing
  - cookie access
  - logout flow
  - header auth-user hydration
2. Preserved existing Analytics page behavior and API interaction contracts.

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 remains green after the third page migration.
- Next safe step is to migrate another single page and repeat the same full validation gate.

### 2026-04-27: Phase 4 structural refactor slice 4 (Financial Records list page)
Completed actions:
1. Migrated `templates/base/financial_records.html` to shared helper usage from `static/js/app_shared.js` for:
  - toast rendering
  - safe JSON parsing
  - cookie access
  - logout flow
  - header auth-user hydration
2. Preserved existing Financial Records list page behavior and API interaction contracts.

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 remains green after the fourth page migration.
- Next safe step is to migrate another single page and repeat the same full validation gate.

### 2026-04-27: Phase 4 structural refactor slice 5 (Financial Records client-detail page)
Completed actions:
1. Migrated `templates/base/financial_records_client.html` to shared helper usage from `static/js/app_shared.js` for:
  - toast rendering
  - safe JSON parsing
  - cookie access
  - logout flow
  - header auth-user hydration
2. Preserved existing Financial Records client-detail page behavior and API interaction contracts.

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 remains green after the fifth page migration.
- Shared helper extraction for toast/session/auth utilities is now applied across all current core dashboard pages.

### 2026-04-27: Phase 4 structural refactor slice 6 (Shared sidebar-state utility)
Completed actions:
1. Added shared sidebar initializer in `static/js/app_shared.js` (`initializeSidebarBehavior`).
2. Migrated duplicated sidebar behavior to shared helper across core pages:
  - `templates/base/dashboard.html`
  - `templates/base/clients.html`
  - `templates/base/analytics.html`
  - `templates/base/financial_records.html`
  - `templates/base/financial_records_client.html`
3. Preserved existing sidebar UX behavior (desktop collapse persistence + mobile drawer handling).

Validation gate results after this refactor slice:
- `python manage.py check` -> Passed (`System check identified no issues`)
- `python manage.py test safebooks.tests.test_auth_api safebooks.tests.test_dashboard_summary_api safebooks.tests.test_analytics_summary_api safebooks.tests.test_clients_api safebooks.tests.test_financial_records_api` -> Passed (`Ran 26 tests`, `OK`)

Status:
- Phase 4 shared utility extraction objective is complete for current core pages.
- Cleanup/refactor readiness gate for Reports is now satisfied.
