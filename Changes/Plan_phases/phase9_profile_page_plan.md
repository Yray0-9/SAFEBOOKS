# SafeBooks Phase 9 Profile Page Plan (UI-first)

## 1) Objective
Deliver a Profile page UI that feels native to the existing SafeBooks experience and makes it easy for a bookkeeper to view and update their identity details. This plan is UI-first only. A deferred functionality plan is included for later.

## 2) Defense Scope And Priority
- Priority: UI only (100%)
- Functionality: plan only (30% later)
- No backend changes, no database changes, no new APIs in this phase

## 3) UI Scope (What Users Will See)
### 3.1 Page Shell (Consistent With Other Pages)
- Sidebar and topbar match Dashboard/Analytics/Reports behavior
- Page title: "Profile"
- Subtitle: "Manage your account identity and visibility"
- Top-right profile dropdown and logout
- Toast container for feedback

### 3.2 Profile Overview Header (Hero Card)
- Large avatar circle with initials
- Display name and role (Bookkeeper)
- Primary email and status pill (Active)
- Quick actions row:
  - "Edit Profile" (scrolls to Personal Details)
  - "Change Password" (planned label + disabled button)
  - "View Activity" (scrolls to Activity section)

### 3.3 Personal Details Card
- Full Name (text input)
- Username (text input)
- Email Address (text input)
- Phone Number (optional input)
- Time Zone (select)
- Location (text input)
- Primary action: "Save Profile"
- Helper text: "Updates how your name and contact details appear across SafeBooks"

### 3.4 Professional Identity Card
- Title / Signature Line (text input used in reports)
- Company / Practice Name (text input)
- Role (read-only tag: Bookkeeper)
- Default Client Group (select, planned label)
- Primary action: "Save Identity"

### 3.5 Security And Access Card
- Change Password (planned button)
- Two-factor Authentication (planned status row)
- Active Sessions (planned list placeholder)
- "Sign out of all devices" (planned button)
- Helper text: "Security controls will be enabled after defense"

### 3.6 Preferences Snapshot Card
- Read-only chips: Theme, Notifications, Date Format
- Link button: "Manage in Settings"
- Helper text: "Update preferences in the Settings page"

### 3.7 Activity And Audit Card
- Recent activity timeline (placeholder list of 4 to 6 items)
- "Export activity log" (planned button)
- "View full audit log" (planned link)

### 3.8 Connected Devices Card
- List of devices with last active time (placeholder rows)
- "Revoke access" (planned buttons)
- Helper text: "Device management will be available soon"

### 3.9 Danger Zone Card
- "Request account deactivation" (planned button)
- Helper text: "Account removal requires confirmation"

## 4) UI Behavior And States
- Save buttons show disabled state until changes are made
- Inline validation for required fields (name, username, email)
- Toast feedback:
  - Success: "Profile updated"
  - Error: "Unable to update profile"
- Loading state: skeleton overlay consistent with other pages
- Planned features show a "Planned" tag and short explanatory hint

## 5) Dark Mode UI Plan (Details)
- Reuse existing theme tokens (theme-light / theme-dark)
- Ensure card borders, chips, and input backgrounds match current dark theme standards
- Keep all text contrast safe in both themes

## 6) Accessibility And Consistency
- Inputs have labels and aria-describedby hints
- Buttons include accessible focus styles
- Section headings are meaningful and keyboard reachable
- Scroll-to buttons update focus on the target section

## 7) Functionality Plan (Deferred - 30% Later)
### 7.1 Backend Endpoints (Future)
- GET /api/profile/ (load profile data)
- PUT /api/profile/ (update profile data)
- POST /api/profile/avatar/ (upload avatar)
- POST /api/profile/password/ (change password)
- GET /api/profile/activity/ (recent activity)
- GET /api/profile/sessions/ (active sessions)
- POST /api/profile/sessions/revoke/ (revoke session)

### 7.2 Data Contract (Future)
- profile: full_name, username, email, phone, time_zone, location
- identity: title, company, role
- preferences: theme, notifications_summary, date_format
- security: two_factor_enabled, active_sessions
- activity: timestamp, action_label

### 7.3 Storage Rules (Future)
- Validate email format and non-empty name/username
- Limit avatar size and enforce image types
- Track activity log entries per user

### 7.4 Tests (Future)
- Auth required for all profile endpoints
- Update validation errors and file upload limits
- Session revoke behavior
- Regression checks for settings and reports pages

## 8) Acceptance Criteria (UI)
1. Profile page matches current dashboard visual language and navigation
2. All sections listed in this plan are visible and styled
3. Planned features are clearly labeled and non-breaking
4. Page loads without regressions to existing flows
5. CTA buttons and hero actions are wired to UI-only behavior

## 9) Execution Status
- Not started (UI-first plan only)
