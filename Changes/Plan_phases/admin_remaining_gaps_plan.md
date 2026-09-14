# SafeBooks Admin Remaining Gaps Plan

## Purpose

This document is the next-stage plan for the SafeBooks admin console after the original admin roadmap was implemented.

The existing `admin_console_improvement_roadmap.md` should remain as the history of completed work. This document lists only the gaps that still exist in the current codebase.

No feature in this plan should expose client passwords, ORUS credentials, email passwords, or complete client financial records to the admin.

## Audit Method

The current implementation was checked across:

- Admin Home
- Bookkeepers
- Approvals
- Admin Audit Log
- Admin Profile
- Read-only System Rules
- Admin page APIs and service functions
- Admin database models and audit records
- Existing admin automated tests

Baseline verification before this plan:

- `python manage.py check`
- 46 existing admin tests passed

## Current Strengths

The following features already work and should not be rebuilt:

- Separate admin authentication and authorization guards
- Action-focused Admin Home
- Manual approve/reject workflow
- Required rejection reason
- Bookkeeper deactivate/reactivate workflow
- Bookkeeper deactivation-request review
- Admin password confirmation for critical account changes
- Protected permanent deletion when a bookkeeper still owns clients
- Admin audit-log database table and read-only page
- Real Admin Profile updates and password changes
- Read-only System Rules page
- Aggregate client-load information without financial-record exposure

## Remaining Gaps Found

### 1. Dashboard numbers and attention items are not fully aligned

- `Total bookkeepers` currently excludes pending accounts.
- Rejected accounts are sometimes labeled `Inactive`, which is less precise.
- Deactivated and rejected accounts are counted as needing attention even when no admin action is required.
- Pending deactivation requests are not prioritized clearly on Admin Home.
- The hard-coded high-load threshold may not be meaningful for a small deployment.

### 2. Admin audit history is incomplete

- Successful admin login and logout are not recorded.
- Rejection reasons and deactivation review notes are not included in the serialized audit details.
- The Audit Log has no date-range filter or pagination.
- The current API returns only the first 100 matching rows without navigation to older rows.

### 3. Approval notifications are previews only

- The Approval page prepares notification wording but does not send an approval or rejection email.
- The admin cannot see a reliable `Sent`, `Skipped`, or `Failed` delivery result.
- A decision should remain saved even if email delivery fails.

### 4. Critical decisions are transactional but not concurrency-safe

- Approval, rejection, deactivation, reactivation, and deletion read the target before opening the transaction.
- Two admins acting at nearly the same time could make a decision using stale status information.
- Duplicate or contradictory audit records must be prevented.

### 5. Admin security still needs stronger controls

- Admin accounts do not have a two-factor authentication flow.
- Custom session creation does not explicitly rotate the session key after login.
- Session lifetime and idle-expiry behavior are not clearly configured for admin access.
- Admin login/logout security events are not visible in the audit trail.

### 6. Admin lists are not ready for many accounts

- Bookkeepers and Approvals return every matching account.
- Audit Log is capped at 100 records but has no pagination.
- Large account volumes will make responses and tables slower and harder to scan.

### 7. Long-term client continuity is unresolved

- Deactivation safely preserves a bookkeeper's clients, but those clients remain owned by the deactivated account.
- If a bookkeeper leaves permanently, a future ownership-transfer workflow may be needed.
- This should not be implemented until the adviser and users confirm the expected business process.

## Recommended Implementation Order

### Phase 1: Correct Admin Home Signals

Priority: First, low risk.

Status: Implemented and verified on July 12, 2026.

Goal:
Make Admin Home show only accurate and actionable information.

UI changes:

- Use `Rejected` consistently instead of `Inactive` for rejected accounts.
- Show pending deactivation requests as a real Needs Review item.
- Move deactivated/rejected accounts out of Needs Review when no action is pending.
- Keep account distribution in Account Health for reference.
- Keep high client load as monitoring information, not an urgent warning.

Data changes:

- Make `Total bookkeepers` include pending, approved, rejected, and deactivated accounts.
- Keep each status count separate.
- Recalculate the Needs Review total from actionable items only.

Do not change:

- Approval decisions
- Deactivation behavior
- Client ownership
- Audit records

Example:

- If one account is awaiting approval and another has requested deactivation, Admin Home should show `2 items` needing review. A previously rejected account should remain visible in Account Health but should not increase that review count.

Acceptance checks:

- KPI totals match the database statuses.
- Pending deactivation requests link to Bookkeepers.
- Existing dashboard API authentication remains unchanged.
- Add tests for total-account and actionable-review calculations.

Implementation result:

- `Total bookkeepers` now includes every account status.
- Account Health uses the exact labels `Pending approval`, `Approved`, `Deactivated`, and `Rejected`.
- Needs Review now contains only pending access approvals and pending deactivation requests.
- Rejected and deactivated accounts remain available in Account Health and the load snapshot without increasing the actionable review count.
- High client load monitors approved accounts only and does not appear as an urgent review task.
- Approval and deactivation decision endpoints were not changed.

Verification completed:

- Admin Dashboard focused tests: 6 passed.
- Full admin regression suite: 48 passed.
- Django system check: no issues.
- Admin dashboard JavaScript syntax: valid.

### Phase 2: Complete Admin Audit Traceability

Priority: High.

Status: Implemented and verified on July 13, 2026.

Goal:
Make important admin access and decisions explainable later.

Changes:

- Record successful admin login and logout.
- Record the decision reason or review note where appropriate, without storing passwords or request payloads.
- Add date-from and date-to filters.
- Add server-side pagination with a modest default page size.
- Preserve current action filters and search.
- Keep audit records read-only; no edit or delete API should be added.

Privacy rules:

- Do not record passwords, authentication codes, session IDs, OAuth tokens, or client credentials.
- Do not log every page view or search.
- Do not expose bookkeeper client financial data.

Example:

- The log should show that an admin rejected an access request, when it happened, which account was affected, and the saved reason. It must not show the admin password used to confirm the action.

Acceptance checks:

- Login/logout entries are created exactly once per successful event.
- Failed login attempts do not flood the normal audit table.
- Date filtering and pagination return stable results.
- Existing audit action groups continue to work.

Implementation result:

- Successful admin sign-in and sign-out events are recorded once in the existing read-only audit table.
- Failed sign-in attempts remain outside the normal audit history.
- Rejection reasons, deactivation-request reasons, and decline review notes are stored as explicit decision notes.
- Audit metadata remains allowlisted and excludes passwords, confirmation values, sessions, tokens, and request payloads.
- The Audit Log supports inclusive date-from/date-to filtering and server-side pagination with 10 rows per page.
- Search, sorting, and the existing Approvals, Access, Security, and Protected Delete action groups remain available.
- No audit edit or delete endpoint was introduced.

Verification completed:

- Focused audit, decision, and authentication tests: 36 passed.
- Full admin and authentication regression suite: 58 passed.
- Django system check: no issues.
- Migration check: no model changes detected.
- Admin audit JavaScript syntax: valid.
- Automated browser screenshot verification was unavailable in this session; rendered-template assertions and responsive CSS review were completed instead.

Feedback corrections completed:

- Date inputs and the sort control are aligned consistently with the search field.
- Pagination now uses 10 rows per page; 11 matching activities produce a second page with one row.
- Date-range warnings wait until both entered dates contain complete four-digit years.
- Audit API focused tests: 13 passed.
- Segmented-date behavior simulation confirmed no warning for an incomplete year and one warning only after a completed invalid range.

### Phase 3: Protect Decisions From Concurrent Admin Actions

Priority: High, backend safety.

Status: Implemented and verified on July 13, 2026.

Goal:
Prevent stale or contradictory account decisions.

Changes:

- Fetch target accounts and deactivation requests with `select_for_update()` inside `transaction.atomic()`.
- Validate the current status after the row is locked.
- Return a friendly stale-decision message when another admin already completed the action.
- Ensure one successful state change creates one audit entry.
- Keep repeated requests idempotent where appropriate.

UI behavior:

- Refresh the affected row after a stale-decision response.
- Explain that the account was updated by another admin instead of presenting a generic error.

Example:

- If two admins open the same pending request and both click Approve, the first decision succeeds. The second admin is told that the request was already reviewed, and no duplicate approval audit entry is created.

Acceptance checks:

- Approval and access transitions use locked rows.
- Duplicate decisions do not create duplicate audit events.
- Existing single-admin behavior remains unchanged.

Implementation result:

- Approval, rejection, deactivation, deactivation-request review, reactivation, and protected deletion now lock their target rows inside database transactions.
- Deactivation-request actions use a consistent bookkeeper-then-request locking order.
- Status validation occurs after the lock is acquired.
- Completed or conflicting decisions return HTTP `409` with `code: stale_decision` and `refresh_required: true`.
- Approvals and Bookkeepers automatically refresh after a stale-decision response and close the outdated action modal.
- Repeated decisions do not create additional audit entries.
- Existing successful single-admin responses and password confirmation remain unchanged.

Verification completed:

- Focused approval and bookkeeper transition tests: 26 passed.
- Full admin and authentication regression suite: 64 passed.
- A real two-connection PostgreSQL approval test confirmed one successful decision, one stale response, and one audit entry.
- Django system check: no issues.
- Admin approval and bookkeeper JavaScript syntax: valid.

### Phase 4: Send Real Approval Decision Emails

Priority: Medium, after decision safety.

Status: Implemented and verified on July 13, 2026.

Goal:
Inform bookkeepers when their access request is approved or rejected.

Changes:

- Send a concise email to the bookkeeper's registered email after the database decision commits.
- Approval email: explain that workspace access is available.
- Rejection email: include the saved rejection reason and a safe next step.
- Return and display `Sent`, `Skipped`, or `Failed` delivery status.
- Record the delivery outcome in safe audit metadata.
- Provide a retry action only for a failed decision email, not for every row.

Reliability rule:

- Email failure must not undo a valid approval or rejection decision.

Example:

- An approval succeeds even if SMTP is temporarily unavailable. The admin sees `Decision saved, email failed` and can retry later without approving the account a second time.

Acceptance checks:

- Use Django's configured email backend.
- Test email content with the local-memory backend.
- Never include passwords or verification codes.
- Repeated retry does not change account status.

Implementation result:

- Approval and rejection decisions now send concise messages through Django's configured email backend after the decision transaction completes.
- Approval messages explain that workspace access is available; rejection messages include the saved reason and a safe contact step.
- Passwords, password hashes, and verification codes are excluded from message content and delivery metadata.
- Each decision audit entry records a safe `sent`, `skipped`, or `failed` delivery result, attempt time, reason, and retry count.
- The Approvals details modal displays the delivery result and shows `Retry Email` only after a failed delivery.
- Email failure does not roll back or repeat the approval/rejection decision.
- A retry updates the original decision audit metadata without creating another decision audit or changing account status.
- `SAFEBOOKS_APPROVAL_DECISION_EMAILS_ENABLED` can disable delivery cleanly, producing a visible `skipped` result.

Verification completed:

- Focused approval decision and notification tests: 17 passed.
- Wider admin and authentication regression tests: 52 passed.
- Complete SafeBooks automated suite: 136 passed.
- Django system check: no issues.
- Migration drift check: no changes detected.
- Browser automation was unavailable in this workspace; template IDs, event bindings, endpoint paths, and JavaScript control flow were reviewed directly.

### Phase 5: Admin Security Hardening

Priority: Medium to high.

Goal:
Give system-manager accounts stronger protection than ordinary accounts.

Changes:

- Rotate the session key after successful admin and bookkeeper login.
- Define an explicit admin session lifetime and idle-expiry policy.
- Add admin two-factor authentication using the established authenticator-code pattern.
- Add setup, confirmation, disable, and recovery behavior in Admin Profile.
- Require recent re-authentication for especially sensitive operations if the current password confirmation becomes too repetitive.
- Audit successful 2FA enable/disable and session-security changes.

Important caution:

- Do not enable mandatory 2FA until a recovery method is designed; otherwise the only admin could be locked out.
- Do not reuse or expose a bookkeeper's 2FA secret.

Example:

- After entering the correct admin password, the admin confirms an authenticator code before 2FA is enabled. A saved recovery method is required before making it mandatory.

Acceptance checks:

- Session fixation tests confirm the session key changes after login.
- Admin-only 2FA endpoints reject bookkeeper sessions.
- Authenticator secrets are never returned after setup completion. Plaintext
  recovery codes are returned only once by successful setup or regeneration;
  profile and audit APIs expose only the number remaining.

Implementation status:

- Step 1 complete: successful admin and bookkeeper authentication rotates the
  session key; admin sessions now enforce an eight-hour absolute lifetime and
  a thirty-minute inactivity limit by default.
- Step 2 complete: authenticator 2FA is disabled by default and can be enabled
  or disabled from Admin Profile after password and authenticator-code
  verification. The setup secret is held in the server session for five
  minutes and is never returned by the profile endpoint after confirmation.
  Enrollment now presents a scannable QR code for authenticator apps, with the
  manual setup key kept as a fallback when scanning is unavailable.
- Step 3 complete: enabling 2FA creates eight one-time recovery codes. They are
  displayed once with copy and print controls, while only keyed hashes are
  saved. Replacement requires the current password and a live authenticator
  code, immediately invalidates the old set, and creates an audit entry without
  storing or exposing any code value.
- Step 4 remains intentionally pending: admin login enforcement has not been
  activated, so current admin login remains password-only until the recovery
  workflow has been reviewed separately from enrollment.

### Phase 6: Paginate Admin Directories

Priority: Medium, before deployment growth.

Goal:
Keep admin pages fast and readable as account counts grow.

Changes:

- Add server-side pagination to Approvals, Bookkeepers, and Audit Log.
- Use a conservative default such as 20 or 25 rows per page.
- Return `page`, `page_size`, `total_count`, and `total_pages`.
- Preserve search, status filters, action filters, and sorting when changing pages.
- Reset to page 1 when a filter changes.
- Avoid horizontal table scrolling on normal desktop widths.

Example:

- With 300 bookkeepers, the admin sees the first 25 accounts and can move through pages without downloading and rendering all 300 rows at once.

Acceptance checks:

- Invalid page values fall back safely.
- Empty last pages recover to a valid page after a status-changing action.
- Existing filtering and ordering tests remain valid.

### Phase 7: Conditional Client Ownership Transfer

Priority: Future; requires adviser and user confirmation.

Goal:
Preserve client continuity if a bookkeeper permanently leaves.

Possible direction:

- Let an admin transfer all or selected client ownership to another approved bookkeeper.
- Show client names and counts only as needed for reassignment; do not expose credentials or financial details.
- Require admin password confirmation.
- Record previous owner, new owner, affected client IDs, and count in the audit log.
- Keep deactivation available without forcing immediate transfer.

Do not implement yet if:

- The organization expects each bookkeeper's client portfolio to remain permanently separate.
- There is no approved business rule for who may receive transferred clients.

## Features Not Recommended

Do not add these merely to make the admin console look larger:

- All-client financial analytics
- Direct viewing of client passwords or ORUS credentials
- Editable tax or forecasting values from the admin side
- Automatic account approval
- Permanent delete as a normal table action
- Decorative charts that repeat existing counts
- Logging every click, search, or page view
- A large editable System Settings form without real policy requirements

## Page-by-Page Working Rule

For every phase:

1. Confirm the current page and API behavior.
2. Implement one page or one safety boundary at a time.
3. Preserve existing account and client ownership rules unless the phase explicitly changes them.
4. Add focused tests before moving to the next phase.
5. Explain the result with a simple admin scenario.
6. Stop for review before beginning the next phase.

## Recommended Next Move

Start with **Phase 1: Correct Admin Home Signals**.

Reason:

- It fixes misleading information without changing sensitive decisions.
- It is easy to verify visually and through API tests.
- It gives the admin a trustworthy starting page before adding deeper audit, email, or security behavior.

No admin implementation should begin until this plan is reviewed and Phase 1 is explicitly approved.
