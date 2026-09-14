# SafeBooks Phase 7 Reports Page Plan

## 1) Objective
Design and implement a Reports page that is clear, efficient, and usable for bookkeepers while preserving consistency with existing system behavior.

This plan assumes Reports is a new feature page and must not degrade existing modules.

## 2) Dependency Gate (Must Pass Before Build)
Reports implementation can begin only after:
1. `CODEBASE_CLEANING_PLAN.md` Phase 1 is completed (artifact archival).
2. Shared frontend utility extraction has started/completed for duplicated logic (sidebar/toast/session/helpers).
3. Validation Gate passes:
   - `python manage.py check`
   - Core API suite passing

Planning can continue in parallel while dependency work is in progress.

Current gate status (2026-04-27):
- Gate 1: Passed (Phase 1 artifact archival completed).
- Gate 3: Passed (`manage.py check` and core API suite are green).
- Gate 2: Passed (shared utility extraction completed for current core pages, including shared sidebar-state handling via `static/js/app_shared.js`).

## 3) Functional Scope (Phase 7)
Included:
- Reports list page with date/scope filters.
- Report generation actions for current supported domains:
  - Financial summary report
  - Compliance status snapshot
  - Client risk overview
- Download-ready export endpoints (initially CSV; optional PDF in Phase 7.2).
- Clear empty states and generation status feedback.

Excluded (for initial release):
- Full scheduled/automated emailing.
- Complex custom report builders.
- Multi-tenant analytics beyond current bookkeeper scope model.

## 4) UX Requirements
1. Keep same navigation, profile/logout behavior, and visual language as existing core pages.
2. Fast filter controls:
   - Date range
   - Client scope (all or one client)
   - Report type
3. Action clarity:
   - Generate
   - Preview
   - Download
4. User-safe feedback:
   - Loading state
   - Empty state
   - Error state with actionable text
5. Accessibility basics:
   - Keyboard operable controls
   - Labels and aria attributes aligned with existing pages

## 5) Backend Plan
### Phase 7.1 - Core APIs
1. Add reports service module (for aggregation and report payload shaping).
2. Add API endpoints (auth-protected):
   - `GET /api/reports/options/` (report types, defaults, available clients)
   - `POST /api/reports/generate/` (creates in-memory report result metadata)
   - `GET /api/reports/export/` (CSV download by generated query payload)
3. Reuse existing ownership boundaries (bookkeeper-scoped data only).
4. Reuse existing validation patterns for dates, client_id, and payload shape.

### Phase 7.2 - Optional Enhancements
1. Add persisted generated reports table only if history/download audit is required.
2. Add PDF export if CSV-only is insufficient.

## 6) Frontend Plan
### Phase 7.1 - New Page
1. Add route and template for Reports page.
2. Use shared layout components and shared JS utilities (not duplicated inline logic).
3. Build page-specific JS module for report orchestration.
4. Add filter state synchronization and safe request handling (debounce/latest-request-wins where needed).

### Phase 7.2 - Usability Polish
1. Add result cards/table preview.
2. Add report generation history panel if backend persistence exists.

## 7) Data Contract (Initial)
Request payload for generate:
- `report_type`
- `client_id` (nullable for all)
- `date_from`
- `date_to`

Response payload:
- `ok`
- `report_type`
- `scope`
- `generated_at`
- `summary`
- `rows`
- `download_url` (if immediately exportable)

## 8) Testing Strategy
Add dedicated tests:
1. Auth required for all reports APIs.
2. Ownership isolation for scoped client reports.
3. Validation errors:
   - invalid date ranges
   - invalid client
   - missing report_type
4. Success behavior:
   - all-clients report
   - client-scoped report
   - CSV export response
5. Regression checks to ensure existing suites remain green.

## 9) Rollout Sequence
1. Implement API options + generate endpoints.
2. Implement Reports page UI with filters and preview.
3. Implement CSV export endpoint and download action.
4. Add and run report API tests.
5. Run full project validation gate.

## 10) Acceptance Criteria
1. Reports page is accessible from sidebar and behaves consistently with existing pages.
2. Users can generate at least three report types with clear scope/date filters.
3. Export works reliably for supported report formats.
4. No regressions in auth, clients, financial records, dashboard, and analytics flows.
5. Core suite remains fully green after merge.

## 11) Risk Controls
1. Keep API and UI contracts simple in Phase 7.1.
2. Avoid introducing large new inline scripts; keep modules separated.
3. Use latest-request-wins handling for interactive filters.
4. Require passing validation gate before marking Phase 7 complete.

## 12) Execution Status Update (2026-04-27)
Completed in this pass (UI-first scope):
1. Added authenticated Reports page route and view:
   - `/reports/`
   - `views.reports_page_view`
2. Implemented full Reports UI page:
   - Consistent dashboard shell, sidebar/topbar/profile/logout behavior
   - Filter controls for report type, client scope, and date range
   - Actions: Generate, Preview, Download CSV, Reset
   - Loading, empty, and error states
   - Preview cards/table plus session-level generated-report history
3. Implemented page-specific modules:
   - `static/css/reports.css`
   - `static/js/reports_page.js`
4. Activated Reports in sidebar navigation across core pages (replacing planned placeholder button).
5. Validation gate after implementation:
   - `python manage.py check` passed
   - Full test suite passed (28 tests)
