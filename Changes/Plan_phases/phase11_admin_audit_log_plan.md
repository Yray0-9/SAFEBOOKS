# SafeBooks Phase 11 Admin Audit Log Plan (UI-first)

## 1) Objective
Provide a dedicated Admin Audit Log page that tracks admin actions affecting bookkeeper accounts and approvals, without exposing client data.

## 2) Requirements Alignment
- Supports admin accountability and oversight.
- Complements Approvals and Bookkeepers pages without duplicating them.
- No client names, records, or financial data.

## 3) Scope And Priority
- UI-only changes.
- Admin-only access.
- Focus on admin actions: approvals, rejections, suspensions, reactivations, profile edits.

## 4) Page Structure

### 4.1 Header
- Title: "Audit Log"
- Subtitle (commented by default)
- Utility chips: role label, last login, access verified

### 4.2 KPI Summary (Optional)
- Total actions (30 days)
- Approvals logged
- Rejections logged
- Account status changes

### 4.3 Audit Log Table (Core)
- Search by admin name or action type
- Filter chips: All, Approvals, Rejections, Status Changes, Logins
- Date range selector (UI-only)
- Table columns:
  - Timestamp
  - Admin
  - Action
  - Bookkeeper
  - Outcome/Status
  - Notes (short)

### 4.4 Action Detail Panel (UI-only)
- Selected log entry summary
- Fields: Admin name, action, target bookkeeper, timestamp, outcome
- Empty state when no selection

### 4.5 Export And Retention
- Export log (disabled)
- Retention policy note (commented by default)

## 5) UI Behavior And States
- Planned-feature toast for UI-only controls
- Empty state rows if no logs
- Keyboard focus and ARIA labels for filters

## 6) Privacy And Security (Non-negotiable)
- No client data, names, or financial records
- Admin-only route guard
- Log entries should reference only bookkeeper and admin identities

## 7) Acceptance Criteria
1. Audit Log page is clearly distinct and admin-focused.
2. No client data is visible.
3. UI provides search, filters, and log details (UI-only).
4. Layout is consistent with the admin theme.

## 8) Collaboration Checkpoint (You Do / I Do)
- You: Confirm sections and labels align with expectations.
- I do: Implement the UI-only page after approval.

## 9) Status
- Draft (ready for review)
