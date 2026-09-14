# Admin Status Summary Page UI Plan

## 1. Purpose and Goals
- Provide a single, admin-only view of system health, data freshness, and operational risks.
- Keep it distinct from Dashboard (overview), Bookkeepers (directory), and Approvals (queue).
- Favor fast scanning: short labels, compact cards, and clear status chips.

## 2. Page Identity (Unique to Status Summary)
- Theme: "Operational Health & Compliance" (no queue lists or directory tables).
- Primary emphasis: system services, data pipelines, SLA compliance, and alerts.
- Visual focus: status chips, progress meters, and readiness checks.

## 3. Layout Structure
- Reuse admin layout: sidebar + topbar + content grid.
- Topbar:
  - Title: "Status Summary"
  - Optional subtitle (keep commented by default)
  - Utility strip: role, last login, access verified (same as other admin pages)
- Content sections in a 2-column grid on desktop; stacked on mobile.

## 4. Section Breakdown

### A) Status Snapshot (KPI Row)
Four compact KPI tiles:
- Services healthy
- Pipelines on schedule
- Alerts open
- Compliance checks passed

State values:
- Default: N/A or 0 with short labels
- Chip colors: Success, Warning, Danger, Neutral

### B) Service Health Grid
Card with service list (not a large table):
- API Gateway
- Auth Service
- Approvals Service
- Reporting Service
- Backups

Each row:
- Status chip (Healthy, Degraded, Offline)
- Last check time
- Optional latency badge

### C) Data Freshness & Pipelines
Card showing latest data refresh times:
- Bookkeeper Directory Sync
- Approval Queue Sync
- Audit Log Ingestion
- Reports Cache

Include a mini progress bar per pipeline (UI-only).

### D) Compliance and SLA
Card with simple checklist blocks:
- Approval SLA
- Access policy review
- Backup verification
- Security audit lock

Display as "Pass / Due / Overdue" chips.

### E) Risk & Alert Timeline
Vertical timeline list of recent alerts (UI-only):
- "Access policy review overdue"
- "Backups pending verification"
- "Audit log ingestion delayed"

Each item:
- Severity chip (Low/Med/High)
- Timestamp placeholder

### F) Action Center
Short list of admin actions:
- "Run health check"
- "Review failed services"
- "Open audit log"
- "Download status report" (disabled)

## 5. Visual Components and Consistency
- Reuse existing classes: `dashboard-card`, `admin-card`, `admin-status-chip`, `dashboard-action-btn`.
- Maintain the admin console palette and typography.
- Keep helper text minimal; if needed, comment out hint lines to avoid clutter.

## 6. Interactions (UI-only)
- Filter chips for Services (All / Healthy / Degraded / Offline).
- Toggle for "Show only issues" (disabled by default).
- Buttons trigger the standard planned-feature toast.

## 7. Empty and Loading States
- Show placeholder rows for services and pipelines when no data is available.
- Use the existing skeleton loader class.

## 8. Accessibility
- Use semantic headings per card.
- Add `aria-label` on filters and action buttons.
- Ensure status chips have text labels, not color-only meaning.

## 9. Notes on Guidance Text
- Keep instruction-like hints commented out by default in the template.
- Preserve the text so it can be re-enabled later without rework.

## 10. Future Data Mapping (Optional)
- Services and pipelines can map to real health checks when backend endpoints exist.
- SLA and compliance fields can connect to audit and approvals metrics.
