# SafeBooks Phase 11 Admin Bookkeepers Management Plan (UI-first)

## 1) Objective
Create a dedicated Admin-only Bookkeepers Management page that is clear, efficient, and consistent with the refined Admin theme. This page must remain within Phase 11 privacy limits (no client names or financial data).

## 2) Scope And Priority
- UI-only page (no data wiring yet)
- Admin-only access and navigation
- Focus on bookkeeper accounts: status, approvals, and activity
- No client records, no financial data, no operational bookkeeper tools

## 3) Page Structure
### 3.1 Header
- Title: "Bookkeepers"
- Subtitle: admin-only oversight copy
- Utility chips: role label, last login, access verified (reuse admin dashboard pattern)

### 3.2 KPI Summary (Counts Only)
- Total bookkeepers
- Pending approvals
- Approved accounts
- Suspended accounts

### 3.3 Bookkeeper Directory Table
Columns:
- Name
- Email
- Status (Pending/Approved/Suspended/Inactive)
- Last login (date only)
- Actions (UI-only): Approve, Suspend, Reactivate

### 3.4 Filters + Search (UI-only)
- Status filter chips
- Search input (name/email)
- Sort dropdown (Most recent, Alphabetical, Last login)

### 3.5 Activity Snapshot (UI-only)
- Recent logins list (name + last login)
- Empty state message when no data

### 3.6 Admin Notes (Optional Placeholder)
- Notes list + Add note button (UI-only)

### 3.7 Quick Actions (UI-only)
- Refresh list
- Export list (disabled)
- View audit log (placeholder)

## 4) UI Behavior And States
- Planned-feature toast for all actions
- Empty states for table and activity list
- Disabled state for export button
- Keyboard focus and ARIA labels for icon actions

## 5) Privacy And Security (Non-negotiable)
- No client names, financial records, or transactions
- No links to bookkeeper operational pages
- Admin-only route guard required

## 6) Navigation
- Add Admin sidebar link: "Bookkeepers"
- Keep Admin dashboard as the landing page
- Do not add cross-links into bookkeeper pages

## 7) Implementation Notes (UI-only)
- Reuse Admin theme tokens and layout patterns from admin dashboard
- Use existing skeleton loader and planned-feature toast behavior
- Keep copy short, operational, and non-technical

## 8) Acceptance Criteria
1. Admin-only Bookkeepers page loads with the new Admin theme.
2. All content is bookkeeper-level only (no client or financial data).
3. Actions are UI-only with clear disabled/placeholder behavior.
4. Layout is readable, consistent, and keyboard accessible.
5. Navigation clearly separates Admin from Bookkeeper pages.

## 9) Collaboration Checkpoint (You Do / I Do)
- You: Confirm the page structure and action labels.
- I do: Implement the UI-only template and route after approval.

## 10) Status
- Draft (ready for review)
