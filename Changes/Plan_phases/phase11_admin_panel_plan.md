# SafeBooks Phase 11 Admin Panel Plan (UI-first + minimal auth scaffolding)

## 1) Objective
Deliver a secure Admin login path and a clean Admin Dashboard focused on bookkeeper account management only. No client or financial data is exposed in this phase.

## 2) Scope And Priority
- Priority: Admin UI only (90%)
- Minimal backend scaffolding (10%) for Admin login and role routing
- No Admin access to client names, financial records, or transactions
- No public Admin registration

## 3) Admin Access Model (Decision)
### 3.1 Separate Admin Entity
- Use a dedicated ADMINS table (already defined in the ERD).
- Admin is a system manager, not a bookkeeper.

### 3.2 Shared Login Form (No New UI)
- Keep the current login page.
- On submit, backend resolves role:
  - If credentials match ADMINS -> set admin session and redirect to /admin/dashboard.
  - Else fall back to Bookkeeper login flow.

### 3.3 Admin Account Creation
- No Admin self-register.
- Create Admin accounts via:
  - One-time management command, or
  - Data migration / seed script.

## 4) Admin Dashboard UI (Only Page In This Phase)
### 4.1 Header
- Admin name, role label ("System Manager"), last login.

### 4.2 KPI Cards (High-level Only)
- Total bookkeepers
- Pending approvals
- Approved accounts
- Suspended accounts

### 4.3 Pending Approval Queue
- Table: Bookkeeper name, email, registration date, status
- Actions: Approve / Reject (UI-only for now)

### 4.4 Account Status Summary
- Compact list of counts by status (Pending, Approved, Suspended, Inactive)
- No client details

### 4.5 Workload Snapshot (Counts Only)
- Bookkeeper name + total client count only
- No client names or financial data

### 4.6 Activity Feed
- Recent bookkeeper activity: last login date and status

### 4.7 Admin Notes (Optional UI Placeholder)
- Notes list and add-note button (UI-only)

### 4.8 Quick Actions
- Refresh, Export list (disabled/placeholder), View audit log (placeholder)

## 5) UI Behavior And States
- Buttons show planned-feature toast until backend is wired
- Empty states for queue and activity list
- Skeleton loader pattern consistent with existing pages
- Keyboard focus and aria-labels on all actions

## 6) Privacy And Security Rules (Non-negotiable)
- Admin cannot view client names or financial records
- Only bookkeeper-level counts and statuses are shown
- No navigation links to bookkeeper operational pages

## 7) Minimal Backend Scaffolding (Required For Login Only)
- Admin model/table if not already present
- Seed initial Admin account (management command or migration)
- Login service checks Admin table before Bookkeeper
- Separate session key (example: safebooks_admin_id)
- Admin dashboard route protected by admin-only guard

## 8) Collaboration Checkpoints (You Do / I Do)
- You: Confirm how Admin accounts are seeded (management command vs migration seed).
- I do: Draft the Admin Dashboard UI plan and implement the UI-only template/CSS/JS.

## 9) Acceptance Criteria
1. Admin can log in using the existing login form and land on Admin Dashboard.
2. Admin Dashboard shows only bookkeeper-level counts and statuses.
3. No client names or financial records are visible anywhere.
4. UI is consistent with SafeBooks styling and fully keyboard-accessible.
5. No changes to Bookkeeper UI flow are required in this phase.

## 10) Execution Status
- Not started (plan only)
