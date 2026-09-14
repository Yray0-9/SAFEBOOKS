# SafeBooks Phase 11 Admin System Settings Plan (UI-first)

## 1) Objective
Provide an Admin System Settings page focused on operational controls and account governance, without exposing any client data.

## 2) Requirements Alignment
- Supports admin-only controls tied to bookkeeper management and approvals.
- Avoids client details, financial records, or transactional data.

## 3) Scope And Priority
- UI-only changes.
- Admin-only access.
- Settings are descriptive and safe (no real writes yet).

## 4) Page Structure

### 4.1 Header
- Title: "System Settings"
- Subtitle (commented by default)
- Utility chips: role label, last login, access verified

### 4.2 Approval Governance
- Default approval mode: Manual (radio UI-only)
- Auto-approve threshold: disabled
- Approval SLA target: dropdown (24h / 48h / 72h)

### 4.3 Bookkeeper Account Controls
- Account status policy: Suspend after inactivity (toggle UI-only)
- Inactivity window: 30 / 60 / 90 days
- Client load warning threshold: 15 / 25 / 40

### 4.4 Notification Preferences
- Notify on approval: toggle
- Notify on rejection: toggle
- Notification channel: Email / In-app (checkbox UI-only)

### 4.5 Security & Access
- Admin session timeout: 30 / 60 / 120 minutes
- Require re-auth for high-risk actions: toggle
- IP allowlist (placeholder input, UI-only)

### 4.6 Data Retention (Admin Logs)
- Audit log retention: 90 / 180 / 365 days
- Export availability: disabled

### 4.7 Save and Reset
- Primary button: "Save settings" (planned feature)
- Secondary: "Reset to defaults" (planned feature)

## 5) UI Behavior And States
- Planned-feature toast for all controls
- Disable inputs that should not be adjustable yet
- Helper text commented by default to keep UI clean

## 6) Privacy And Security (Non-negotiable)
- No client data displayed or configured
- Admin-only access
- Settings only affect bookkeeper governance and approvals

## 7) Acceptance Criteria
1. Settings page is admin-only and clearly scoped.
2. No client data appears.
3. Settings align with approval and bookkeeper governance.
4. UI matches admin theme and is easy to scan.

## 8) Collaboration Checkpoint (You Do / I Do)
- You: Confirm sections and labels align with expectations.
- I do: Implement the UI-only page after approval.

## 9) Status
- Draft (ready for review)
