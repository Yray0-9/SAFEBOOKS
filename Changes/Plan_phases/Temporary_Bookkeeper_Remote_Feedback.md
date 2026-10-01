# Implementation Plan: Temporary Bookkeeper Feedback to Developer

> **Status:** Implemented locally; automated checks passed; manual browser and SMTP delivery testing remains
>
> **Audience:** Approved SafeBooks bookkeeper beta users
>
> **Delivery:** Direct email to the configured SafeBooks developer address
>
> **Storage:** Email-only; no feedback database table or local server backup
>
> **Risk:** Low to moderate when the controls and tests in this plan are implemented

## 1. Purpose

SafeBooks will temporarily provide an obvious, easy-to-use feedback control on every authenticated bookkeeper page during remote beta testing. It will let bookkeepers send suggestions, questions, confusing experiences, and bug reports directly to the SafeBooks developer without leaving the page they are testing.

This is a temporary beta-support feature, not a permanent support ticket system. It does not guarantee durable storage when email delivery is unavailable. Failed submissions remain visible in the modal so the user can retry without retyping the message.

## 2. User-facing experience

### Floating control

Show a clearly labeled control in the bottom-right corner of bookkeeper pages:

```text
[ message icon ] Send Feedback
```

The desktop label must remain visible so users do not have to guess what an icon means. On very small screens it may use a compact label, but it must retain an accessible name such as `Send feedback to the SafeBooks developer`.

The control must:

- Match the existing SafeBooks design and dark theme.
- Remain visible without covering page actions, tables, mobile navigation, or toast messages.
- Be keyboard accessible and have a clear focus style.
- Be shown only when the feature flag is enabled.

### Feedback modal

Use the following clear content:

**Title:** `Send Feedback to the Developer`

**Introduction:**

> Found something confusing, have an idea, or noticed a problem? Send a message directly to the SafeBooks developer.

**Categories:**

- Suggestion or feature idea
- Something is confusing
- Bug or unexpected behavior
- General comment or compliment

**Message field:**

```text
Tell us what happened, what you expected, or what would make SafeBooks easier to use.
```

**Privacy notice:**

> Your SafeBooks account name, registered email, and current page will be included so the developer can understand and follow up on your feedback.

Do not include the bookkeeper's saved physical location. It is not necessary for ordinary product feedback.

### Submission behavior

- Disable the submit button and show a spinner while one request is in progress.
- Prevent double submission.
- On confirmed email delivery, close and reset the modal and show:

  `Thank you - your feedback was sent to the SafeBooks developer.`

- On validation failure, keep the modal open and show the relevant field message.
- On network or email failure, keep the user's message and show:

  `We could not send your feedback right now. Your message is still here - please try again.`

- Restore focus to the floating control after the modal closes.
- Warn before discarding a message when the user closes a modal containing unsent text.

## 3. Information included in the email

The server must obtain identity from the authenticated session, never from browser-supplied identity fields.

Include:

- Bookkeeper full name
- Bookkeeper username
- Registered email address
- Philippine local submission time using the configured `Asia/Manila` timezone
- Selected feedback category
- Sanitized SafeBooks page title
- Sanitized same-site page path, without query parameters or URL fragments
- The submitted message

Do not include:

- Passwords, credentials, session values, cookies, CSRF tokens, or recovery codes
- Bookkeeper physical location
- Query-string values or arbitrary external URLs
- Client financial data unless the user deliberately writes it in the feedback message

### Example email

```text
Subject: [SafeBooks Beta Feedback] Suggestion from Juan Dela Cruz

SafeBooks Remote Beta Feedback

Submitted by: Juan Dela Cruz
Username: jdelacruz
Registered email: juan.delacruz@example.com
Submitted at: September 24, 2026, 2:45 PM (Asia/Manila)

Category: Suggestion or feature idea
Page: Client Details
Path: /clients/14/

Message:
It would help if I could sort financial line items before saving.
```

The message should be sent as plain text, or user content must be escaped if an HTML email is added later.

## 4. Delivery and configuration

Use the existing Django email configuration. Add these environment-backed settings:

```text
SAFEBOOKS_FEEDBACK_ENABLED=0
SAFEBOOKS_FEEDBACK_RECIPIENT_EMAIL=developer@example.com
SAFEBOOKS_FEEDBACK_EMAIL_TIMEOUT_SECONDS=10
```

Rules:

- Keep the real destination address in the private `.env`, not hard-coded in Python, templates, JavaScript, tests, or `.env.example`.
- The feature is unavailable when disabled or when no recipient is configured.
- The backend must use `settings.DEFAULT_FROM_EMAIL` as the sender.
- A successful API response is returned only when the email backend confirms at least one message was sent.
- Development's console email backend does not prove that a real email arrived. End-to-end delivery must be tested separately with the configured SMTP environment.

## 5. Failure handling and storage decision

Do not write feedback to `scratch/feedbacks_backup.json` or another local server file. A deployed filesystem may be temporary, unavailable, shared by multiple processes, or lost during restart. A JSON append can also be corrupted by concurrent requests and would create an unmanaged file containing personal information.

For this temporary version:

- Email delivery is the only server-side delivery mechanism.
- If delivery fails, return a temporary-service error and preserve the message in the open modal for retry.
- Log only a delivery failure identifier and technical exception through normal server logging. Do not log the feedback message or account credentials.

If guaranteed storage becomes a requirement, replace this temporary design with a database-backed feedback model or a reliable external queue. That would be a separate, explicitly approved design requiring retention, access, and deletion rules.

## 6. Backend design

### Route

Add a named route in `safebooks/urls.py`:

```text
POST /api/feedback/submit/
```

### View boundary

Add a thin endpoint in `safebooks/views.py` using:

```python
@require_POST
@require_bookkeeper_auth
```

The view must:

- Decode the existing JSON request format.
- Use `request.bookkeeper_account` as the submitting identity.
- Pass the authenticated account and proposed feedback fields to the service.
- Return a stable JSON envelope and appropriate HTTP status.

### Service

Create `safebooks/services/feedback_service.py` to:

- Enforce the feature flag and configured recipient.
- Validate and normalize category, message, page title, and page path.
- Build the fixed email subject and plain-text body.
- Convert the submission time to `Asia/Manila` through Django timezone utilities.
- Send the email with a finite timeout.
- Return a structured success or failure result without exposing SMTP details.

### Validation and abuse controls

- Allow only the four documented category values.
- Require a trimmed message between 10 and 2,000 characters.
- Limit page-title and page-path lengths.
- Accept only a relative same-site path beginning with `/`.
- Remove query parameters and fragments from page context.
- Apply a small cache-based rate limit per authenticated bookkeeper, such as five submissions per ten minutes.
- Return `429` with a helpful retry message when the limit is reached.
- Keep CSRF protection enabled and use the existing same-origin CSRF header pattern.

### Response behavior

```text
200  Feedback email delivery confirmed
400  Invalid category, message, or page context
401  No authenticated session
403  Account not approved or feature unavailable
429  Submission rate limit reached
503  Email delivery temporarily unavailable
```

## 7. Frontend integration

Create separate files that follow the existing project structure:

```text
templates/base/partials/feedback_widget.html
static/css/feedback_widget.css
static/js/feedback_widget.js
```

Update `templates/base/bookkeeper_base.html` to:

- Load the feedback stylesheet when the feature is enabled.
- Include the widget once for all bookkeeper pages when enabled.
- Load the feedback script after `app_shared.js` when enabled.

Reuse existing SafeBooks functionality where appropriate:

- `window.SafeBooksShared.getCookieValue` for the CSRF token
- `window.SafeBooksShared.parseJsonSafe` for API responses
- `window.SafeBooksShared.showToast` for success messages
- Existing Bootstrap modal behavior and SafeBooks visual conventions

Do not copy account identity from `localStorage` into the submission. The backend session is authoritative.

## 8. Expected file changes

### New files

```text
templates/base/partials/feedback_widget.html
static/css/feedback_widget.css
static/js/feedback_widget.js
safebooks/services/feedback_service.py
safebooks/tests/test_feedback_api.py
```

### Existing files with narrow changes

```text
templates/base/bookkeeper_base.html
safebooks/urls.py
safebooks/views.py
safebooks/settings.py
.env.example
```

No model or migration is required for the approved email-only version.

## 9. Verification plan

### Automated checks

Run:

```powershell
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test safebooks.tests.test_feedback_api
```

Tests must cover:

- Confirmed delivery by an approved authenticated bookkeeper
- Anonymous, pending, rejected, and suspended access rejection
- Identity coming from the authenticated session rather than the request payload
- Empty, short, oversized, and whitespace-only messages
- Invalid categories and invalid page context
- Query strings and fragments removed from page context
- Configured recipient and sender use
- Disabled feature and missing recipient behavior
- Email exception and zero-message delivery behavior
- Rate-limit response
- No feedback message or credential leakage in API errors

### Manual browser verification

- The purpose is immediately understandable from the `Send Feedback` label and modal copy.
- The widget appears on all intended bookkeeper pages and never on authentication or admin pages.
- Desktop, mobile, light-theme, and dark-theme layouts remain usable.
- Keyboard focus, Escape, close, cancel, and unsent-message warning work correctly.
- The floating control does not cover important page controls.
- Double clicks produce only one request.
- A failed request preserves the message.
- A successful request resets the form and displays the correct toast.
- With real SMTP enabled, the configured developer inbox receives the expected email.

## 10. Temporary-operation and removal plan

### Immediate disable

Set:

```text
SAFEBOOKS_FEEDBACK_ENABLED=0
```

After the application restarts, the widget should no longer appear and the endpoint should reject submissions. This provides a safe way to stop beta feedback without rushing to delete code.

### Full removal after beta testing

1. Remove the feedback include and static asset references from `bookkeeper_base.html`.
2. Remove the route and thin view.
3. Delete the feedback template, CSS, JavaScript, service, and focused tests.
4. Remove the feedback settings and `.env.example` entries.
5. Run `manage.py check` and the relevant bookkeeper test suite.

There is no database cleanup for this email-only design.

## 11. Readiness verdict

**Implemented and ready for owner testing.**

The feature will be easy for beta users to recognize because it explicitly says `Send Feedback`, the modal says the message goes to the SafeBooks developer, and the success message confirms delivery. The design remains temporary and isolated while avoiding unreliable local backup files, hidden personal-data collection, hard-coded recipient addresses, and misleading delivery guarantees.
