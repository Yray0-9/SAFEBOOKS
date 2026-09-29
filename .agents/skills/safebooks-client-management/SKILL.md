---
name: safebooks-client-management
description: Plan, implement, or review SafeBooks client-management changes involving client creation, editing, status, location, credentials, validation, notifications, or client-detail UI. Do not use for unrelated financial-record calculations or general account settings.
---

# SafeBooks Client Management

Read the repository-root `knowledge.md` and `AGENTS.md` before acting.

## Trace the whole client flow

Inspect the relevant route and view in `safebooks/urls.py` and `safebooks/views.py`, the business rules in `safebooks/services/client_service.py`, the `Client` model, the affected templates and browser scripts, and `safebooks/tests/test_clients_api.py`.

For modal changes, check all client entry points:

- Create and edit flows in `templates/base/clients.html`.
- Detail editing in `templates/base/client_details.html`.
- Shared partials or static assets used by those pages.

## Preserve client invariants

- Scope every client query and mutation to the authenticated bookkeeper.
- Keep existing request field names and response envelopes compatible unless the task explicitly changes the contract.
- Preserve TIN uniqueness, service-layer validation, custom fields, remarks/status behavior, and client notification behavior.
- Treat email and ORUS credentials as sensitive. Do not log or expose them outside existing authorized responses.
- Do not silently rewrite stored values when adding selectors, formatting, or external data sources.
- If changing the Davao Region XI location selector, preserve the hidden `location` payload format: `Province, City/Municipality, Barangay`.

## Implement narrowly

Keep authorization and request parsing at the view boundary, client rules in `client_service.py`, markup in templates, and presentation or interaction behavior in the established CSS/JavaScript location. Do not change financial-record behavior as a side effect of a client UI task.

## Verify

Run:

```powershell
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test safebooks.tests.test_clients_api
```

Also verify the affected create, edit, cancel/reset, validation-error, and saved-client paths. Report any check that could not run.
