# SafeBooks Project Knowledge

## Purpose

SafeBooks is a Django web application for bookkeepers to manage clients, financial records, reports, account settings, and audit information. It also has a separate administrative area for approving and managing bookkeeper accounts.

## Technology

- Python and Django 6
- Django templates with vanilla JavaScript and CSS
- SQLite for local development; PostgreSQL is supported through environment configuration
- Django session authentication, CSRF protection, email verification, optional Google OAuth, and two-factor authentication flows
- `statsmodels` for forecasting features

## Main structure

| Location | Responsibility |
| --- | --- |
| `safebooks/urls.py` | Page and JSON API routes |
| `safebooks/views.py` | Request boundaries: authentication, authorization, request parsing, and responses |
| `safebooks/services/` | Business logic for clients, financial records, security, settings, reporting, dashboards, and administration |
| `safebooks/models/` | Django data models and database relationships |
| `safebooks/validators/` | Input validation helpers |
| `templates/` | Django page templates and reusable partials |
| `static/css/` | Page styling |
| `static/js/` | Shared browser-side behavior |
| `safebooks/tests/` | API, security, reporting, dashboard, and forecasting tests |

## Roles and access

- **Bookkeeper**: signs up or signs in, manages only their own clients and financial records, and can change their profile and settings.
- **Administrator**: approves, rejects, deactivates, reactivates, and audits bookkeeper accounts through `/admin/` pages and `/api/admin/` endpoints.

All client and financial-record operations must preserve bookkeeper ownership. Do not expose, update, or delete another bookkeeper's data.

## Core data and workflows

### Clients

The `Client` model stores client identity, contact and business details, location, account-access details, remarks, and custom fields. Client operations flow through `safebooks/services/client_service.py` and are exposed through:

- `/api/clients/`
- `/api/clients/<client_id>/`
- `/api/clients/<client_id>/reopen/`

The create and edit modals are in `templates/base/clients.html`; the detailed client edit modal is in `templates/base/client_details.html`. Their submitted JSON payload must retain the existing field names, especially `location`.

The location selector is shared through `templates/base/partials/client_location_selector_script.html`. It uses the public PSGC API only for Davao Region XI and stores a completed location as `Province, City/Municipality, Barangay`. Existing saved location text must not be silently rewritten when a client is edited.

### Financial records

Financial records belong to a client and are handled through `safebooks/services/financial_record_service.py`. The related API routes are under `/api/financial-records/`. Record lines, periods, and totals must remain consistent; changes to calculations require focused tests.

### Authentication and security

Authentication routes are under `/api/auth/`. Security features include email verification, password reset, account approval, session policies, two-factor authentication, client-details access preferences, and audit logging. Treat credentials, recovery codes, client passwords, and environment variables as sensitive data.

### Reporting and dashboards

Dashboard, analytics, forecasting, reports, and print-layout functionality are provided by their corresponding services and API routes. Report output and financial calculations should be treated as high-impact behavior and verified carefully after changes.

## Configuration

Copy `.env.example` to `.env` for local configuration. Real secrets must stay in `.env` or deployment secret storage and must never be committed.

- Default development database: `db.sqlite3`
- PostgreSQL: enable with `SAFEBOOKS_USE_POSTGRESQL=1` and provide the database variables
- Email, Google OAuth, session-cookie security, and notification settings are environment-driven
- Use HTTPS production values for `SAFEBOOKS_SESSION_COOKIE_SECURE` and `SAFEBOOKS_CSRF_COOKIE_SECURE`

## Development checks

Use the project virtual environment on Windows:

```powershell
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test
```

Run focused tests when changing a specific feature, for example:

```powershell
& .\.venv\Scripts\python.exe manage.py test safebooks.tests.test_clients_api
```

## Safe change rules

1. Read the relevant view, service, model, template, JavaScript, and test before changing a feature.
2. Keep API request and response contracts compatible unless a deliberate coordinated change is required.
3. Do not modify database models, authentication, authorization, financial calculations, or audit behavior as a side effect of a UI-only task.
4. Preserve existing client data when adding validation or external data sources.
5. Keep unrelated user changes intact in a dirty working tree.
6. Verify Django checks and the relevant focused tests before reporting a change complete.
