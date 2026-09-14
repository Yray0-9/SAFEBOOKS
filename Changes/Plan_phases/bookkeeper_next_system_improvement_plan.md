# SafeBooks Next System Improvement Plan

Date: 2026-06-18

## Purpose

This plan defines the next careful improvement path for SafeBooks after the first cleanup passes on Financial Records, Clients, Dashboard, and client-specific analytics/reporting.

The goal is to keep improving the system for bookkeepers without making the interface feel technical, crowded, or confusing. Changes should continue to be done page by page, with visual clarity first and function changes only when needed.

## Current Direction

SafeBooks should now focus on selected-client workflows:

- Dashboard gives a calm overview and quick access.
- Clients page works as a clean directory.
- Client Details is the main place for selected-client analytics, forecasting, and report preview.
- Financial Records is the main place for encoding and reviewing client transactions.
- Standalone Reports and standalone Analytics should stay hidden or deferred unless a clear use case is approved.

## Quick System Scan Findings

### 1. Navigation Is Simpler, But Hidden Pages Still Exist

The sidebar now focuses on:

- Dashboard
- Clients
- Financial Records
- Settings

The broad Reports page route still exists, and the standalone Analytics template still exists. This is acceptable for now because we are avoiding destructive removals, but the future decision should be:

- keep only selected-client report/analytics workflows, or
- fully remove broad pages in one focused cleanup pass.

### 2. Profile Page Is The Best Next UI Target

Profile is lower risk than forecasting or financial calculations, but it still affects trust because it shows the bookkeeper's own account information.

Observed improvement areas:

- It still has several planned/placeholder-like items.
- Some activity entries appear static and may look fake if shown to the panel.
- There are inline style delays and progress width styles that should eventually move into CSS.
- The page can be simplified to focus on account identity and security status.

### 3. Settings Page Should Follow Profile

Settings contains useful controls, but it may still feel technical if too many options are presented at once.

Observed improvement areas:

- Workspace defaults still reference report settings even though broad Reports is deferred.
- Security controls should be clear and practical.
- Any planned or preview-only behavior should be worded carefully so users do not expect unfinished functions.

### 4. Financial Records List Page Still Has Planned-Feature Toasts

The client-level Financial Records page has already been improved, but the main Financial Records list still has planned-feature messaging in JavaScript.

Future cleanup should:

- Remove or hide actions that are not actually usable.
- Keep the page focused on selecting a client and entering records.
- Avoid showing planned buttons that may make the system look unfinished.

### 5. Template Maintenance Is Becoming Important

Several templates still have large inline JavaScript blocks:

- `templates/base/client_details.html`
- `templates/base/clients.html`
- `templates/base/financial_records_client.html`
- `templates/base/dashboard.html`
- `templates/base/settings.html`
- `templates/base/profile.html`

This does not need to be fixed immediately, but after UI decisions stabilize, scripts should be moved into `static/js` page files one at a time.

## Recommended Next Work Order

### Step 1. Profile Page UI Cleanup

Priority: High

Reason:
This is the lowest-risk next page and improves trust in the account area.

Scope:

- Simplify the profile header and subtitle.
- Remove or soften static activity items that look fake.
- Keep only practical account information.
- Keep Save Profile clear.
- Move obvious inline page styles into `profile.css` where safe.
- Do not change authentication behavior.

Checks:

- Template compile check for `base/profile.html`.
- `python manage.py check`.
- Run profile/auth tests if available.

### Step 2. Settings Page Usability Review

Priority: High

Reason:
Settings affects account behavior and should not feel technical or unfinished.

Scope:

- Review whether report defaults still make sense while standalone Reports is hidden.
- Keep settings grouped by practical user need.
- Remove or reword preview/planned controls if they make the page look unfinished.
- Keep password/security functions intact.

Checks:

- Template compile check for `base/settings.html`.
- `python manage.py check`.
- Run settings/security tests if available.

### Step 3. Financial Records Main Page Cleanup

Priority: Medium

Reason:
The client-specific record page is strong now, but the main Financial Records page should also feel direct and simple.

Scope:

- Make it clear that users first choose a client.
- Remove planned-feature buttons or placeholder toasts.
- Keep search and client selection compact.
- Keep navigation to client records reliable.

Checks:

- Template compile check for `base/financial_records.html`.
- `python manage.py check`.
- Run financial records API tests.

### Step 4. Reports And Analytics Final Decision

Priority: Medium

Reason:
The system already moved toward selected-client analytics and reports. The hidden broad pages should not remain in an unclear state forever.

Decision options:

1. Keep routes but no navigation.
2. Redirect broad pages to Clients page.
3. Remove templates/routes/tests in a focused cleanup pass.

Recommended:
Do not delete yet. First confirm that Client Details fully covers panel expectations for analytics, forecast, and client report preview.

Checks:

- Client Details report preview still works.
- Forecasting still uses Weighted Moving Average labels.
- No user-facing Linear Regression wording appears.

### Step 5. Template JavaScript Extraction

Priority: Later

Reason:
This is a maintainability improvement, not an urgent user-facing change.

Suggested order:

1. `profile.html` JavaScript to `static/js/profile_page.js`
2. `settings.html` JavaScript to `static/js/settings_page.js`
3. `clients.html` JavaScript to `static/js/clients_page.js`
4. `financial_records_client.html` JavaScript to `static/js/financial_records_client_page.js`
5. `client_details.html` analytics/report JavaScript to a dedicated file

Rule:
Extract only one page at a time and run checks after each extraction.

## Work Rules For The Next Phase

- Do not redesign multiple pages in one pass.
- Do not delete hidden pages until the replacement workflow is confirmed.
- Do not change financial calculations or forecasting unless specifically requested.
- Keep all wording practical for bookkeepers.
- Prefer removing confusing unfinished UI over explaining it with more text.
- Run checks after every page change.

## Immediate Recommendation

Start with:

Profile Page UI Cleanup

Why:
It is the next safest improvement, it removes unfinished-looking account UI, and it does not risk breaking core financial record or forecasting behavior.

