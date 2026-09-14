# SafeBooks Phase 11 Admin Approvals Alignment Plan (Adviser/User Requirements)

## 1) Objective
Align the Admin Approvals page to the core approval workflow so the admin can approve/reject bookkeepers and trigger notifications without exposing any client details.

## 2) Requirements Mapping (Must Support)
- Admin approves or rejects new bookkeepers.
- Bookkeeper status remains "Pending" until approved.
- Admin can review request metadata (bookkeeper-only fields).
- Approvals/rejections trigger notifications to the bookkeeper.
- No client data is shown.

## 3) Scope And Priority
- UI-first changes only.
- Admin-only access.
- Approvals page focuses strictly on approval workflow.

## 4) Approvals Page Content Structure (Updated)

### 4.1 Header
- Title: "Approvals"
- Subtitle (commented by default)
- Utility chips: role label, last login, access verified

### 4.2 KPI Summary (Counts Only)
- Pending approvals
- Approved today
- Rejected today
- Total approvals (30 days)

### 4.3 Approval Queue (Core Section)
- Search by name/email
- Status filter chips: All, Pending, Approved, Rejected
- Sort dropdown: Newest, Oldest, Status
- Table columns:
	- Bookkeeper name
	- Email
	- Request date
	- Status
	- Actions (Approve/Reject/View details) UI-only

### 4.4 Approval Details Panel (UI-only)
- Selected request overview:
	- Bookkeeper name
	- Email
	- Request date
	- Status
- Empty state when no request is selected

### 4.5 Review Notes (UI-only)
- Short notes area for approval reasoning
- Save note button (planned)

### 4.6 Notification Preview (Requirement Support)
- Small panel noting that approvals/rejections notify bookkeepers
- Show recent notification status (sent/queued) UI-only

### 4.7 Quick Actions
- Refresh queue
- View audit log (planned)
- Export approvals (disabled)

## 5) Remove/Relocate From Approvals Page
- Bookkeeper directory data (belongs to Bookkeepers page)
- System readiness blocks (belongs to Dashboard)
- Client-load summaries (belongs to Bookkeepers page)

## 6) Notification System Recommendation (Best Fit)
- Dual-channel:
	- In-app notifications for bookkeepers after login
	- Transactional email on approval/rejection
- Admin UI should expose minimal delivery status only (sent/queued/failed) UI-only.

## 7) UI Behavior And States
- Planned-feature toast for UI-only actions
- Empty states for queue/details/notes
- Keyboard focus and ARIA labels preserved
- Keep helper text commented for clean UI

## 8) Privacy And Security (Non-negotiable)
- No client names or financial data
- Admin-only guard on the route

## 9) Acceptance Criteria
1. Approvals page supports a clear approval workflow.
2. Only bookkeeper-level fields are shown.
3. Notification concept is visible without exposing sensitive data.
4. No overlap with Bookkeepers or Dashboard content.

## 10) Collaboration Checkpoint (You Do / I Do)
- You: Confirm sections and labels align with adviser/user expectations.
- I do: Implement the UI-only updates after approval.

## 11) Status
- Draft (ready for review)
