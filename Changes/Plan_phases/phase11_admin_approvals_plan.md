# SafeBooks Phase 11 Admin Approvals Plan (UI-first)

## 1) Objective
Provide a dedicated Admin Approvals page for reviewing and approving bookkeeper access requests. This page is UI-only and must not expose any client or financial data.

## 2) Scope And Priority
- UI-only page (no backend wiring)
- Admin-only access and navigation
- Approvals and status review for bookkeepers only
- No client names, no financial records, no operational bookkeeper tools

## 3) Page Structure
### 3.1 Header
- Title: "Approvals"
- Subtitle: concise oversight copy
- Utility chips: role label, last login, access verified (same admin pattern)

### 3.2 KPI Summary (Counts Only)
- Pending approvals
- Approved today
- Rejected today
- Total approvals (30 days)

### 3.3 Approval Queue Table
Columns:
- Bookkeeper name
- Email
- Request date
- Status (Pending/Approved/Rejected)
- Actions (UI-only): Approve, Reject, View details (disabled)

### 3.4 Filters + Search (UI-only)
- Status filter chips
- Search by name/email
- Sort dropdown (Newest, Oldest, Status)

### 3.5 Approval Details Panel (UI-only)
- Right-side or below table: placeholder for selected request
- Shows only bookkeeper-level fields (no client data)

### 3.6 Review Notes (UI-only)
- Reviewer notes textarea + Save note button (placeholder)

### 3.7 Quick Actions (UI-only)
- Refresh queue
- Export approvals (disabled)
- View audit log (placeholder)

## 4) UI Behavior And States
- Planned-feature toast for all actions
- Empty states for table and details panel
- Disabled state for export button and details view
- Keyboard focus and ARIA labels for icon actions

## 5) Privacy And Security (Non-negotiable)
- No client names, financial records, or transactions
- No links to bookkeeper operational pages
- Admin-only route guard required

## 6) Navigation
- Add Admin sidebar link: "Approvals"
- Keep Admin dashboard and Bookkeepers pages intact
- No cross-links to bookkeeper pages

## 7) Implementation Notes (UI-only)
- Reuse Admin theme tokens and layout patterns
- Use existing skeleton loader and planned-feature toast behavior
- Keep copy short, operational, and readable

## 8) Acceptance Criteria
1. Admin Approvals page loads with the Admin theme.
2. All content is bookkeeper-level only (no client or financial data).
3. Actions are UI-only with clear disabled/placeholder behavior.
4. Layout is readable, consistent, and keyboard accessible.
5. Navigation clearly separates Admin from Bookkeeper pages.

## 9) Collaboration Checkpoint (You Do / I Do)
- You: Confirm the approval queue fields and action labels.
- I do: Implement the UI-only template and route after approval.

## 10) Status
- Draft (ready for review)
