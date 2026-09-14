# SafeBooks Phase 11 Admin Approvals Workflow Plan (Registration + Pending + Approval)

## 1) Objective
Implement a full approval workflow so new bookkeeper registrations start as Pending, appear in Admin Approvals, and can be Approved/Rejected by Admin. Approved users can log in and see a welcome message; pending/rejected/suspended users are blocked from the main app.

## 2) Current State Summary (Verified)
- Bookkeeper accounts have no status fields; new registrations are immediately active.
- Login accepts any valid bookkeeper credentials; no status gating.
- Admin Approvals UI exists but is UI-only.
- No admin approvals API or audit trail yet.

## 3) Proposed Workflow (End-to-End)
1) **User registers** -> account created with status = Pending.
2) **System response** -> user is auto-logged-in to a Pending Approval screen (no access to dashboard/clients/records).
3) **Admin sees request** in Approvals page and can Approve or Reject.
4) **If Approved** -> status set to Approved; user can log in to Bookkeeper dashboard; show welcome banner on first login after approval.
5) **If Rejected** -> status set to Rejected; user cannot log in and sees a clear rejection message.
6) **If Suspended** (admin action later) -> login blocked with suspension message.

## 4) Data Model Changes
### 4.1 BookkeeperAccount fields
- status: enum string (pending | approved | rejected | suspended), default pending
- approved_at: datetime (nullable)
- approved_by_admin_id: FK to AdminAccount (nullable)
- rejected_at: datetime (nullable)
- rejection_reason: short text (nullable)
- last_login: datetime (nullable) for admin visibility (optional but recommended)

### 4.2 Admin audit trail (recommended)
New table: AdminAuditLog
- admin_id, action, target_bookkeeper_id, status_before, status_after, notes, created_at

## 5) API Design (Admin + Auth)
### 5.1 Registration
- POST /api/auth/register
  - Create pending account
  - Return payload: ok, user_id, status, message
  - If auto-login: issue session and redirect to pending page

### 5.2 Login
- POST /api/auth/login
  - Validate password
  - If status != approved -> deny login with status-specific message
  - If approved -> proceed as today
  - Update last_login on successful login

### 5.3 Admin Approvals
- GET /api/admin/approvals
  - Supports search, status filters, pagination
  - Returns pending/approved/rejected counts for KPI
- POST /api/admin/approvals/{bookkeeper_id}/approve
  - Transition: pending -> approved
  - Optional note
- POST /api/admin/approvals/{bookkeeper_id}/reject
  - Transition: pending -> rejected
  - Optional rejection reason

### 5.4 Admin Bookkeepers (later, but aligned)
- GET /api/admin/bookkeepers
  - List with status + last_login + client_count
- POST /api/admin/bookkeepers/{id}/suspend
- POST /api/admin/bookkeepers/{id}/reactivate

## 6) UI/UX Updates
### 6.1 Signup (Bookkeeper)
- After successful register, show "Pending approval" message and route to Pending Approval screen (auto-login requirement).

### 6.2 Pending Approval Screen (new)
- Page that explains approval status, expected time, and a logout button.
- No access to dashboard or other bookkeeper routes.

### 6.3 Login (Bookkeeper)
- If pending/rejected/suspended: show clear status message and do not set session.
- If approved: continue to dashboard and show welcome banner.

### 6.4 Admin Approvals page
- Wire queue with real data, enable Approve/Reject buttons.
- Approval details panel should populate from selection.

## 7) Security + Data Boundaries
- Admin endpoints require admin auth guard.
- Admin views show bookkeeper-only data; never client data.
- Pending users are restricted to the Pending Approval screen.

## 8) Implementation Steps (Incremental)
1) Add BookkeeperAccount status fields + migration (backfill existing accounts as approved).
2) Add Pending Approval page (template + route + access guard).
3) Update registration flow to create pending and auto-login to pending page.
4) Update login flow to block non-approved accounts with clear messages.
5) Add Admin Approvals API (list + approve + reject).
6) Wire Admin Approvals page JS to new API.
7) Add audit log entries for admin actions (if approved).
8) Add tests for registration status, login gating, approval transitions.

## 9) Open Questions (Need Your Confirmation)
Confirmed decisions:
1) Auto-login pending users to a dedicated Pending Approval page.
2) Rejection reason is not shown to users; show a general rejection message.
3) Admin can re-open (reject -> approve) if needed.
4) In-app messages only for this phase; email notifications later.

## 10) Acceptance Criteria
- New registrations are pending by default.
- Pending users cannot access dashboard/clients/records.
- Admin Approvals page lists pending registrations and can approve/reject.
- Approved users can log in and see a welcome message.
- Rejected/suspended users cannot log in and receive a clear message.

## 11) Collaboration Checkpoint (You Do / I Do)
- You: Confirm the open questions and the pending auto-login experience.
- I do: Implement the plan in small, validated steps.
