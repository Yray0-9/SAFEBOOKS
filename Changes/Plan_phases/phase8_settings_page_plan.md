# SafeBooks Phase 8 Settings Page Plan (UI-first)

## 1) Objective
Deliver a Settings page UI that is consistent with existing SafeBooks pages, is easy to scan, and clearly communicates what is available now vs planned. The first defense requires 100% UI, so this plan focuses on visible layout, labels, states, and user interactions. A separate functionality plan is included in this same file for later use only.

## 2) Defense Scope And Priority
- Priority: UI only (100%)
- Functionality: plan only (30% later)
- No backend changes, no database changes, no new APIs in this phase

## 3) UI Scope (What Users Will See)
### 3.1 Page Shell (Consistent With Other Pages)
- Sidebar and topbar match Dashboard/Analytics/Reports behavior
- Page title: "Settings"
- Subtitle: "Manage your account preferences and workspace experience"
- Top-right profile dropdown and logout
- Toast container for feedback

### 3.2 Settings Navigation (Left rail or top tabs inside the page)
Visible sections (click scroll or tab switch):
1. Account Profile
2. Workspace Defaults
3. Appearance (Dark Mode)
4. Notifications
5. Data And Export
6. Security
7. Danger Zone

### 3.3 Account Profile Card (User-facing fields)
- Full Name (text input)
- Username (text input)
- Email Address (text input)
- Profile Initials (auto-generated preview)
- Profile Photo (planned label + placeholder button)
- Primary action: "Save Profile"
- Helper text: "Updates your display details across SafeBooks"

### 3.4 Workspace Defaults Card
- Default Client Scope (select: All clients, Last used client)
- Default Report Type (select: Financial Summary, Compliance Snapshot, Client Risk Overview)
- Default Report Date Range (select: Year-to-date, Last 30 days, Last 90 days, Custom)
- Currency Display (read-only tag: PHP)
- Primary action: "Save Defaults"

### 3.5 Appearance Card (Dark Mode)
- Theme toggle: Light / Dark
- Follow System toggle: On / Off
- Theme preview swatches (light and dark chips with labels)
- Helper text: "Dark mode reduces glare during long sessions"
- Primary action: "Apply Theme"

### 3.6 Notifications Card
- Email Summary (toggle)
- Compliance Alerts (toggle)
- High Risk Client Alerts (toggle)
- Report Ready Notifications (toggle)
- Helper text: "Adjust alerts to match your workflow"
- Primary action: "Save Notifications"

### 3.7 Data And Export Card
- Default Export Format (select: CSV)
- Download Location Hint (read-only text)
- Report History Retention (select: This session only, 7 days, 30 days)
- Primary action: "Save Data Preferences"

### 3.8 Security Card
- Change Password (button, planned label)
- Active Sessions (planned list placeholder)
- Two-factor Authentication (planned toggle placeholder)
- Helper text: "Security settings will be available soon"

### 3.9 Danger Zone Card
- Delete Account (button, planned label)
- Helper text: "This action will be available after defense"

## 4) UI Behavior And States
- Save buttons show disabled state until changes are made
- Inline validation for required fields (name, username, email)
- Toast feedback:
  - Success: "Settings saved"
  - Error: "Unable to save settings"
- Loading state for settings page: skeleton overlay consistent with other pages
- Planned features show a "Planned" tag and short explanatory hint

## 5) Dark Mode UI Plan (Detailed)
- Add a visible theme toggle in Appearance card
- Add a body class switch: theme-light / theme-dark
- Use CSS variables for colors (background, surface, text, border, accent)
- Provide contrast-safe tokens for tables, cards, and buttons
- Store UI theme in localStorage (key: safebooks.ui.theme)
- If Follow System is on, use prefers-color-scheme and override localStorage only when user explicitly selects a theme

## 6) Accessibility And Consistency
- All inputs have labels and aria-describedby hints
- Toggles use buttons with aria-pressed or checkbox inputs
- Keyboard navigation supported for tabs/sections
- All colors meet contrast requirements in light and dark themes

## 7) Functionality Plan (Deferred - 30% Later)
### 7.1 Backend Endpoints (Future)
- GET /api/settings/ (load preferences)
- PUT /api/settings/ (update preferences)
- POST /api/settings/password/ (change password)

### 7.2 Data Contract (Future)
- profile: full_name, username, email
- defaults: report_type, report_range, client_scope
- appearance: theme, follow_system
- notifications: email_summary, compliance_alerts, risk_alerts, report_ready
- data: export_format, history_retention

### 7.3 Storage Rules (Future)
- Preferences stored per bookkeeper account
- Validate email format and non-empty name/username
- Protect change password with current password verification

### 7.4 Tests (Future)
- Auth required for all settings endpoints
- Update validation errors
- Isolation between bookkeepers
- Regression checks for existing pages

## 8) Acceptance Criteria (UI)
1. Settings page matches current dashboard visual language and navigation
2. All sections listed in this plan are visible and styled
3. Dark mode toggle and preview are present and consistent with UI tokens
4. Planned features are clearly labeled and non-breaking
5. Page loads without regressions to existing flows

## 9) Execution Status
- Not started (UI-first plan only)
