# SafeBooks Admin Console Improvement Roadmap

## Current Admin Scope

The admin side is currently focused on system-level account control, not client bookkeeping work. That is the right security direction. The admin should manage bookkeeper access, approval status, system safety, and audit accountability without exposing every client's financial records.

Current admin pages:

- Admin Dashboard: high-level bookkeeper and approval counts.
- Bookkeepers: approved/deactivated/inactive account directory with deactivate, reactivate, and delete actions.
- Approvals: pending/approved/rejected account review workflow.
- System Settings: mostly preview-only policy controls and hidden from the sidebar.
- Admin Profile: mostly preview-only identity/security controls.

Current backend support:

- Admin dashboard summary API.
- Approval list, approve, and reject APIs.
- Bookkeeper list, deactivate, reactivate, and delete APIs.
- Admin authentication/session separation from bookkeeper sessions.

## Main Problem

The admin console has useful foundations, but it still feels limited because several areas are only visual or operationally shallow:

- System Settings and Admin Profile contain many preview-only controls.
- Critical admin actions do not yet have an audit log.
- Deleting bookkeepers is too dangerous compared with archive/deactivate flows.
- Admin security is weaker than bookkeeper security in some areas.
- The dashboard reports counts, but does not yet guide the admin toward the next important action.
- There is no dedicated activity or audit history for approvals, deactivations, reactivations, and login events.

## Admin Design Principle

The admin should be a control center, not a data-exposure page.

The admin should see:

- Who needs approval.
- Which bookkeeper accounts need attention.
- Which accounts are inactive, deactivated, rejected, or high load.
- What critical actions were performed and by whom.
- Whether system policies are configured correctly.

The admin should not casually see:

- All client records from all bookkeepers.
- Full client financial details unless a future emergency/support workflow explicitly requires it.
- Bookkeeper passwords or client credentials.

## Recommended Implementation Order

### 1. Admin Dashboard as Action Center

Priority: UI first, then small functional improvements.

Status: Implemented initial action-center version.

Goal:
Make the dashboard tell the admin what needs attention today.

Improvements:

- Replace passive KPI wording with action-oriented labels.
- Add a compact "Needs Review" panel for pending approvals, overdue approvals, and inactive accounts.
- Add a "Recent Admin Activity" panel once audit logging exists.
- Keep client information aggregate-only: counts and workload, not client details.
- Make quick actions more useful: Review approvals, Manage bookkeepers, View audit log.

Why first:
This page is the admin's landing screen. Improving it makes the admin role feel intentional without touching sensitive business logic first.

Implemented:

- Reworked the admin dashboard into a clearer action center.
- Added a Needs Review panel for pending approvals, high-load bookkeepers, and inactive/deactivated accounts.
- Added quick action tiles for approvals, bookkeeper management, and dashboard refresh.
- Kept client information aggregate-only.
- Extended the dashboard summary API with compact review data.
- Added focused admin dashboard API tests.

### 2. Approval Workflow Cleanup

Priority: UI first, then function.

Status: Implemented initial cleanup and safety pass.

Goal:
Make approval decisions easier, safer, and more accountable.

Improvements:

- Add a cleaner detail panel for selected bookkeeper request.
- Show email, username, request date, verification status, Google-linked status if available, and current status.
- Require a rejection reason instead of optional reason.
- Add a confirmation step for approve/reject.
- Send or prepare a clearer notification message for approved/rejected accounts.
- Record approve/reject actions in an audit log.

Important:
Approval should remain manual. Auto-approval is not recommended for this project because the admin is responsible for access control.

Implemented:

- Reworked the selected request panel into a clearer account review card.
- Added visible account signals for email verification, Google-linked status, current status, last login, reviewer, and rejection reason.
- Updated the decision confirmation modal with clearer approval/rejection copy.
- Made rejection reason required before a pending account can be rejected.
- Added a small `AdminAuditLog` foundation and now records approve/reject decisions.
- Added focused approval API tests for required rejection reasons and audit log creation.

### 3. Bookkeeper Management Safety

Priority: function and safety before extra UI.

Status: Implemented initial safety pass.

Goal:
Avoid dangerous actions and protect bookkeeper/client continuity.

Improvements:

- Replace "Delete" as the normal action with "Archive" or "Deactivate".
- Keep permanent delete only for a protected danger-zone action if truly needed.
- Require admin password confirmation before deactivate/reactivate/archive/delete.
- Show safe summary data: account status, last login, client count, created date.
- Add warning when deactivating a bookkeeper who still owns clients.
- Plan future reassignment workflow before deactivation if client continuity becomes required.

Why:
Deleting accounts can destroy ownership links and confuse records. Deactivation/archive is safer and more professional.

Implemented:

- Removed permanent delete from the normal Bookkeepers table actions.
- Kept deactivate/reactivate as the main access-control actions.
- Added admin password confirmation before deactivate, reactivate, or protected delete API actions.
- Added safe summary data to the Bookkeepers table, including created date, last login, status, and client count.
- Added a deactivation warning when the bookkeeper still owns clients.
- Blocked permanent delete when the bookkeeper still owns clients.
- Recorded deactivate, reactivate, and protected delete actions in `AdminAuditLog`.
- Added focused admin bookkeeper API tests for access rules, password confirmation, audit logging, and delete protection.

### 4. Admin Audit Log

Priority: new backend model and simple page.

Status: Implemented initial read-only audit trail.

Goal:
Make every critical admin action traceable.

Track:

- Admin login/logout.
- Approve/reject bookkeeper.
- Deactivate/reactivate/archive/delete bookkeeper.
- System settings changes.
- Admin password/profile changes.

Fields:

- Admin account.
- Action type.
- Target model and target id.
- Short human-readable message.
- Timestamp.
- Optional metadata.

UI:

- Add an "Audit Log" page or panel.
- Search/filter by action, admin, target, and date.
- Keep the table compact and readable.

Implemented:

- Added a visible Admin Audit Log page in the admin sidebar.
- Added a read-only audit log API with search, action-group filters, newest/oldest sorting, and compact counts.
- Added dashboard quick access to the audit log.
- Shows date/time, admin, action, target account, and message.
- Keeps the audit log focused on account/admin metadata and does not expose client financial records.
- Added focused audit log API tests for authentication, bookkeeper blocking, page rendering, filtering, search, sorting, and serialized counts.

### 5. Admin Security Hardening

Priority: after audit log foundation.

Status: Implemented initial profile/password hardening pass.

Goal:
Admin accounts should have stronger protection than regular users.

Improvements:

- Admin password change should be real, not preview-only.
- Admin profile save should be real, not preview-only.
- Add optional or required admin 2FA.
- Require password re-authentication for critical actions.
- Add session timeout policy.
- Add login alert emails for admin sign-ins.

Note:
This should reuse existing security patterns where possible to avoid building duplicate logic.

Implemented:

- Replaced the preview-only admin profile controls with real profile save behavior.
- Added real admin password change with current-password verification and the same password rules used elsewhere.
- Added admin profile and password APIs protected by admin-only session access.
- Added audit logs for admin profile updates and password changes.
- Replaced fake admin profile activity with recent audit activity.
- Added focused tests for admin profile access, validation, duplicate email protection, password validation, password updates, and audit creation.

### 6. System Settings Decision

Priority: simplify before expanding.

Status: Implemented as read-only System Rules page.

Goal:
Avoid preview-only pages that make the system look unfinished.

Recommended options:

- Option A: Keep System Settings hidden until at least one section is functional.
- Option B: Make only one small section real first, such as approval policy or security policy.
- Option C: Replace the full settings page with a simple "System Rules" read-only page until real configuration is needed.

Best near-term move:
Keep it hidden from normal navigation and implement real admin profile/security first.

Implemented:

- Replaced the preview-only System Settings form controls with an honest read-only System Rules page.
- Removed fake save/reset controls from the admin system settings page.
- Documented the active rules for approvals, bookkeeper access control, audit logging, and admin security.
- Added direct links from each rules section to the real operational page.
- Kept the page hidden from normal sidebar navigation while preserving the route for admin review.
- Added focused tests to confirm admin-only access and that preview-only controls are no longer rendered.

### 7. Admin Profile Completion

Priority: moderate.

Status: Implemented through Phase 5 and finalized with page-level polish.

Goal:
Make profile controls honest and useful.

Improvements:

- Save admin full name and email.
- Add real password change.
- Remove fake activity entries and replace with audit log data once available.
- Keep the page simple: identity, password/security, latest admin actions.

Implemented:

- Kept the admin profile as a simple identity, password security, and recent activity page.
- Confirmed profile save and password update are real API-backed actions.
- Confirmed recent activity comes from the admin audit log instead of fake preview entries.
- Added clearer page subtitle copy so the page purpose is visible in the admin header.
- Added page-level tests for admin-only access and to prevent preview-only wording from returning.

## Suggested Next Work

Start with Phase 1: Admin Dashboard as Action Center.

Reason:
It is the least risky and immediately improves how the admin console feels. It can be done mostly as UI cleanup first, then connected to existing summary data. After that, move to Phase 2 approvals and Phase 4 audit logging, because those give the admin side real purpose.

## Implementation Rules

- Work page-by-page, not all admin pages at once.
- Do UI cleanup first when the page is confusing.
- Do function changes only after the page direction is clear.
- Do not expose all client financial data to admin.
- Prefer deactivate/archive over delete.
- Add tests for every admin action that changes account state.
- Keep admin pages concise, because the admin's job is review and control, not daily bookkeeping.
