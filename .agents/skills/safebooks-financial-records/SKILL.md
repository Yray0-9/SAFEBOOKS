---
name: safebooks-financial-records
description: Plan, implement, or review SafeBooks financial-record changes involving record lines, periods, totals, transactions, reports, analytics, forecasting inputs, or their API and UI flows. Do not use for client-profile-only or general settings changes.
---

# SafeBooks Financial Records

Read the repository-root `knowledge.md` and `AGENTS.md` before acting.

## Trace the financial flow

Inspect the relevant route and view, `safebooks/services/financial_record_service.py`, the `FinancialRecord`, `FinancialRecordLine`, and `Period` models, the affected financial templates/scripts, and the focused tests. If output feeds dashboards, reports, analytics, or forecasts, inspect those consumers before changing the data shape or meaning.

## Preserve financial invariants

- Resolve the client through the authenticated bookkeeper and scope every record operation to both the bookkeeper and client.
- Keep record and line-item writes atomic when they must succeed or fail together.
- Use `Decimal` for money, preserve two-decimal quantization, and do not introduce floating-point arithmetic into stored calculations.
- Keep `total_amount` consistent with normalized line items and retain their stable order.
- Preserve period resolution, entry-date behavior, frequency values, deadline fields, and existing serialization unless the task explicitly changes them.
- Account for downstream client-status promotion and notification behavior after record creation.
- Treat deletion, historical changes, report totals, analytics, and forecasting inputs as high-impact operations.

## Implement narrowly

Keep request parsing and authorization in the view layer and financial rules in `financial_record_service.py`. Coordinate frontend and backend changes when a payload or response changes. Do not change models or create migrations unless the requested behavior requires persistent schema changes.

## Verify

Run:

```powershell
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test safebooks.tests.test_financial_records_api
```

Run the relevant dashboard, analytics, reports, or forecasting tests when the change can affect those consumers. Verify success, validation failure, cross-bookkeeper access denial, totals, and create/update/delete behavior as applicable.
