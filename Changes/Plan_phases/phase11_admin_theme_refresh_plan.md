# SafeBooks Phase 11 Admin Theme Refresh Plan (UI-first, distinct from Bookkeeper)

## 1) Objective
Create a visually distinct Admin console theme that emphasizes governance, security, and oversight while preserving the Phase 11 admin scope (bookkeeper-only data, no client or financial exposure). This plan is additive and does not replace the existing Phase 11 Admin Panel Plan.

## 2) Design Direction (Governance Console)
- Tone: Calm, authoritative, operational, less decorative than the Bookkeeper UI.
- Visual separation: New palette, typography, and surface treatments to reduce role confusion.
- Efficiency: Denser information layout for admin scanning and oversight.

## 3) Typography
- Headings: Space Grotesk (600-700)
- Body: IBM Plex Sans (400-600)
- Numbers: IBM Plex Sans or tabular figures where available

## 4) Color System (No purple bias)
- Base: Graphite (#0f172a), Slate (#1f2937), Mist (#e5e7eb)
- Accents: Steel Blue (#2563eb), Teal (#0f766e)
- Alerts: Amber (#f59e0b), Red (#ef4444)
- Background: layered gradient wash + subtle grid texture

## 5) Layout + Density
- Sidebar: slightly narrower than bookkeeper (240px), clearer iconography.
- Topbar: compact status strip, session status, last login.
- Cards: reduced padding, consistent data density, more tabular styling.
- Tables: high contrast headers, status chips, compact rows.

## 6) Component Updates (Admin-only)
- KPI cards: smaller height, numeric emphasis, thin progress lines.
- Status chips: Pending/Approved/Suspended/Inactive with clear color codes.
- Admin queue table: compact layout with Approve/Reject actions (UI-only).
- Activity feed: last login + status, no client data.
- Notes module: optional, minimized footprint.

## 7) Motion + States
- Page load: slow fade-in with staggered list items.
- Hover: subtle lift, no heavy shadows.
- Empty states: calm, instructional copy with one primary action.
- Planned features: consistent toast for placeholder actions.

## 8) Accessibility
- All actions keyboard reachable.
- Focus rings visible on dark + light surfaces.
- Contrast tested for text + status chips.
- ARIA labels for icon-only actions.

## 9) Privacy + Security (Non-negotiable)
- No client names or financial records anywhere.
- No nav links to bookkeeper operational pages.
- Only bookkeeper counts, statuses, and admin actions.

## 10) Implementation Plan
- Step 1: Add Admin theme tokens (CSS variables) and base admin body class.
- Step 2: Update Admin dashboard layout to use new tokens.
- Step 3: Swap typography, apply grid background, revise cards + tables.
- Step 4: Implement admin-specific UI components (queue, status summary, notes).
- Step 5: Verify accessibility and planned-feature behavior.

## 11) Acceptance Criteria
1. Admin UI looks and feels clearly distinct from Bookkeeper UI.
2. Admin UI remains within Phase 11 privacy scope.
3. All actions remain UI-only placeholders where needed.
4. Keyboard + screen reader navigation works across the page.
5. No regression in admin login flow.

## 12) Collaboration Checkpoint (You Do / I Do)
- You: Confirm the Admin theme direction and typography choices.
- I do: Implement theme tokens and update Admin UI template.

## 13) Status
- Draft (ready for implementation after confirmation)
