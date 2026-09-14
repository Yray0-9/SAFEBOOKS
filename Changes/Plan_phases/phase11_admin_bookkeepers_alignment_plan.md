# SafeBooks Phase 11 Admin Bookkeepers Alignment Plan (Adviser/User Requirements)

## 1) Objective
Align the Admin Bookkeepers page to the core requirement: manage bookkeeper accounts, view each bookkeeper's status, and see client counts without exposing client details.

## 2) Requirements Mapping (Must Support)
- Admin can manage bookkeeper accounts.
- Admin can view the status/condition of each bookkeeper.
- Admin can see the number of clients per bookkeeper (counts only).
- Admin can approve/reject bookkeepers (handled primarily in Approvals; optional inline actions are UI-only).
- No client details or financial records shown.

## 3) Scope And Priority
- UI-first changes only.
- Admin-only access.
- Streamline content: keep only what supports account management and visibility.

## 4) Bookkeepers Page Content Structure (Updated)

### 4.1 Header
- Title: "Bookkeepers"
- Subtitle (commented by default)
- Utility chips: role label, last login, access verified

### 4.2 KPI Summary (Counts Only)
- Total bookkeepers
- Active accounts
- Pending approvals
- Suspended accounts

### 4.3 Bookkeeper Directory (Core Section)
- Search by name/email
- Status filter chips (All, Pending, Approved, Suspended, Inactive)
- Optional client-load filter chips (0-5, 6-15, 16+)
- Sort dropdown (Most recent, Alphabetical, Most clients)
- Table columns:
	- Bookkeeper name
	- Email
	- Status
	- Client count (number only)
	- Last login
	- Actions (Approve/Reject for Pending, Suspend/Reactivate for Approved) UI-only

### 4.4 Status Summary (Compact)
- Count chips by status
- Mirrors key distribution without repeating the directory

### 4.5 Client Load Summary (Compact)
- Count chips by client-load band (0-5, 6-15, 16+)
- Highlights workload balance without exposing client details

### 4.6 Approvals Shortcut (Small Card)
- Pending approvals count + CTA to Approvals page
- Keeps approvals workflow discoverable without duplicating the queue

### 4.7 Quick Actions
- Refresh list
- View approvals (link to Approvals page)
- Export list (disabled)

## 5) Remove/Relocate From Bookkeepers Page
- Approval queue table or review details (belongs to Approvals page)
- System readiness or admin system health blocks (belongs to Dashboard)
- Operational notes (optional; remove if not needed for admin tasks)

## 6) UI Behavior And States
- Planned-feature toast for UI-only actions
- Empty states for directory and summaries
- Disabled export button
- Keep helper text commented to reduce visual noise
- Keyboard focus and ARIA labels on actions

## 7) Privacy And Security (Non-negotiable)
- No client names or financial data
- Only show client counts per bookkeeper
- Admin-only guard on the route

## 8) Acceptance Criteria
1. Bookkeepers page reflects bookkeeper status and client counts only.
2. Approvals workflow is discoverable without duplicating the approvals queue.
3. No client details appear anywhere.
4. UI is clean, efficient, and consistent with admin theme.

## 9) Collaboration Checkpoint (You Do / I Do)
- You: Confirm the updated sections and labels.
- I do: Implement the UI-only updates after approval.

## 10) Status
- Draft (ready for review)
