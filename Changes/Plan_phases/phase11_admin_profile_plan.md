# SafeBooks Phase 11 Admin Profile Plan (UI-first)

## 1) Objective
Deliver an Admin Profile page that lets system administrators review and adjust their own identity and security preferences, without exposing any client data.

## 2) Requirements Alignment
- Matches the Admin dropdown entry "Admin profile" and "Security preferences".
- Focused on admin identity, access scope, and security controls.
- No client names, records, or financial details.

## 3) Scope And Priority
- UI-only changes.
- Admin-only access.
- No real writes yet; all actions are planned-feature or placeholder state.

## 4) Page Structure

### 4.1 Header
- Title: "Admin Profile"
- Subtitle (commented by default)
- Utility chips: role label, last login, access verified

### 4.2 Profile Overview (Hero Card)
- Admin avatar, name, role, email
- Status pill: "Active"
- Actions:
  - "Edit profile" (scrolls to Identity Details)
  - "Security preferences" (scrolls to Security section)
  - "View audit log" (links to Audit Log page)
  - "System settings" (links to System Settings page)

### 4.3 Identity Details (Editable Form)
- Full name
- Username
- Email address
- Phone number
- Time zone
- Location
- Role label (read-only pill)
- Save button (planned)

### 4.4 Security Preferences (Admin-owned)
- Multi-factor authentication (toggle, planned)
- Session timeout (dropdown: 30 / 60 / 120 minutes)
- Require re-auth for high-risk actions (toggle)
- Trusted devices list (UI-only list with device label, last active, location)
- "Sign out all sessions" (planned)

### 4.5 Access Scope Summary (Read-only)
- Permission chips: Approvals, Bookkeepers, Audit Log, System Settings
- Note: "Scope controlled by system policy"

### 4.6 Activity And Audit Snapshot
- Recent admin actions list (UI-only)
- "View full audit log" link

### 4.7 Save And Reset
- Primary: "Save profile"
- Secondary: "Reset changes"

## 5) UI Behavior And States
- Planned-feature toast for all non-functional controls.
- Basic form validation (required fields) without persistence.
- Empty-state rows for activity and trusted devices.

## 6) Privacy And Security (Non-negotiable)
- No client data, financial records, or client identifiers.
- Admin-only route guard.
- Activity list references only admin actions and bookkeeper account targets.

## 7) Routes And Files
- Template: templates/admin_panel/admin_profile.html
- Optional styles: static/css/admin_profile.css (or reuse profile.css)
- Optional script: static/js/admin_profile_page.js
- Route: /admin/profile/ (name: admin_profile)
- View: admin_profile_page_view
- Update admin dropdown links to route and section anchors.

## 8) Acceptance Criteria
1. Admin Profile page is admin-only and aligned with admin console styling.
2. Dropdown item "Admin profile" navigates to the page; "Security preferences" jumps to its section.
3. No client data appears anywhere on the page.
4. Sections are scannable and actions are clearly marked as planned.

## 9) Collaboration Checkpoint (You Do / I Do)
- You: Confirm section labels, fields, and actions.
- I do: Implement the UI-only page after approval.

## 10) Status
- Draft (ready for review)
