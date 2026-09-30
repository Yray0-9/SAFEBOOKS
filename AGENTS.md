# SafeBooks Agent Instructions

## Read first

Inspect only the files directly related to the request, including the relevant view, service, model, template, browser-side code, and tests.

SafeBooks is a Django financial-management application. Changes must be narrow, explainable, and safe for bookkeepers and their clients.

## Project context

- SafeBooks uses Django 6, Django templates, vanilla JavaScript and CSS.
- Page and API routes are in `safebooks/urls.py`; request boundaries are in `safebooks/views.py`.
- Business logic belongs in `safebooks/services/`, persistent models in `safebooks/models/`, and tests in `safebooks/tests/`.
- SQLite is the local default; PostgreSQL is supported through environment configuration.
- The main workflows cover authentication, bookkeeper approvals, clients, financial records, dashboards, reports, settings, and audit logs.

## Working boundaries

- Work on the active feature branch. Do not switch, merge, reset, or modify `main` unless the user explicitly requests it.
- Preserve unrelated user changes. Do not delete, rewrite, or reformat files that are outside the requested scope.
- Do not modify database models, migrations, routes, authentication, authorization, financial calculations, audit logging, or external integrations unless the request requires it.
- Ask for direction before making a change that changes stored data, a public API contract, user permissions, deployment configuration, or a financial-recording rule.

## Architecture rules

- Keep request handling and authorization at the view boundary in `safebooks/views.py`.
- Put business rules in the appropriate module under `safebooks/services/`.
- Keep persistent schema changes in `safebooks/models/` and use migrations for model changes.
- Reuse validators in `safebooks/validators/` rather than duplicating validation rules in templates or JavaScript.
- Keep page markup in `templates/`, page styles in `static/css/`, and browser behavior in `static/js/` or the page's established script location.
- Preserve existing JSON field names and response envelopes unless a coordinated backend and frontend change is requested.

## Data and authorization safety

- A bookkeeper must only access and change their own clients and financial records.
- Preserve client ownership, record relationships, and audit history.
- Do not silently transform existing client data during a user-interface or validation change.
- Treat financial totals, line items, periods, reports, and forecasts as high-impact data. Trace the full calculation and persistence flow before changing them.
- Treat passwords, client account credentials, recovery codes, OAuth secrets, and `.env` values as sensitive. Never print, commit, hard-code, or expose them.

## Frontend change rules

- Inspect the complete create, edit, save, cancel, reset, and error paths before changing a modal or form.
- Keep existing form submission handlers, show/hide password controls, disabled styling, keyboard behavior, and accessibility attributes unless the request explicitly includes them.
- When a form uses a hidden field for its API payload, preserve its name, submitted format, and validation behavior.
- Use progressive enhancement for external browser APIs: show a clear loading or retry state and do not replace valid saved data if the external service is unavailable.
- Keep selectors, IDs, and data attributes stable when other scripts rely on them.

## Verification

Run checks appropriate to the change using the project virtual environment:

```powershell
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test <relevant_test_module>
```

For template, JavaScript, or CSS changes, also verify the affected page or template path. State clearly which checks passed and which could not run.

## Documentation and handoff

- Update `AGENTS.md` when a lasting project rule or important architectural boundary changes.
- In the final handoff, name the changed files, summarize user-visible behavior, and call out any remaining limitation or external dependency.
- Do not claim a test passed unless it was actually run and completed successfully.
