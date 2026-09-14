# SafeBooks Phase 11 Admin Dashboard Alignment Plan (Adviser/User Requirements)

## 1) Objective
Align the Admin Dashboard with the adviser and user requirements so it supports bookkeeper management, approval visibility, and high-level status tracking without exposing confidential client data.

## 2) Requirements Mapping (Must Support)
- Admin manages bookkeeper accounts.
- Admin can view each bookkeeper's status/condition.
- Admin can see the number of clients per bookkeeper (counts only).
- Admin can approve or reject new bookkeepers (approval system exists on Approvals page, dashboard shows summary + routing).
- Bookkeeper accounts can be "Pending" until approved.
- Admin-triggered approvals/rejections should send notifications.

## 3) Scope And Priority
- UI-first changes; no backend wiring in this step.
- Admin-only access; no client names or financial data.
- Dashboard should be an overview hub that routes to Bookkeepers/Approvals for actions.

## 4) Dashboard Content Structure (Updated)

### 4.1 Header
- Title: "Admin Overview"
- Subtitle (commented by default): Admin oversight copy
- Utility chips: role label, last login, access verified

### 4.2 KPI Summary (High-level)
- Total bookkeepers
- Pending approvals
- Active vs. suspended accounts
- Bookkeepers with high client load (count)

### 4.3 Bookkeeper Status Overview (Key Requirement)
- Compact status distribution (Pending / Approved / Suspended / Inactive)
- Each status is a chip + count

### 4.4 Bookkeeper Load Snapshot (Counts Only)
- Small list of 3-5 bookkeepers with client counts
- Columns: Bookkeeper, Status, Client count (no client details)
- Purpose: quick visibility, not a full directory

### 4.5 Approval Readiness Summary
- Short list of pending approvals (count + age bands like "<24h", "2-7d", ">7d")
- CTA button: "Go to Approvals"

### 4.6 Notifications Center (Requirement Support)
- Summary of last 3 admin-triggered notifications
- Copy indicates that approvals/rejections notify bookkeepers
- CTA: "View notification log" (planned)

### 4.7 Admin Priorities
- Daily focus list (UI-only placeholders):
	- Review pending approvals
	- Follow up on suspended accounts
	- Check bookkeepers with high client counts

### 4.8 Quick Actions
- View Bookkeepers (primary)
- View Approvals
- Refresh dashboard (planned-feature)
- Export overview (disabled)

## 5) What Belongs Elsewhere (Do Not Add)
- Full approval queue table (belongs to Approvals page)
- Bookkeeper directory with filters (belongs to Bookkeepers page)
- Client details or financial records (never shown to admin)

## 6) Notification System Recommendation (Best Fit)
- Use a dual-channel approach:
	- In-app notifications for bookkeepers (fast + visible after login)
	- Transactional email on approval/rejection (reliable delivery)
- Admin UI shows a minimal log of recent notifications.
- Data fields: action (approved/rejected), bookkeeper name, timestamp, status (sent/queued).

## 7) UI Behavior And States
- Planned-feature toast for disabled actions
- Empty states for lists (no approvals, no notifications)
- Keep helper text commented (as per preference)
- Consistent admin theme and spacing

## 8) Privacy And Security (Non-negotiable)
- No client names, records, or financial details
- Only show client counts per bookkeeper
- Admin-only guard on the route

## 9) Acceptance Criteria
1. Dashboard supports admin oversight without exposing client data.
2. Bookkeeper status + client counts are visible at a glance.
3. Approval visibility is clear with a direct path to Approvals page.
4. Notifications concept is represented and consistent with requirements.
5. Dashboard remains distinct from Bookkeepers/Approvals pages.

## 10) Collaboration Checkpoint (You Do / I Do)
- You: Confirm sections and labels align with adviser/user expectations.
- I do: Update the Admin Dashboard UI after approval.

## 11) Status
- Draft (ready for review)
