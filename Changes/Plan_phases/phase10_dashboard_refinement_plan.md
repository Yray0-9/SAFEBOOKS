# SafeBooks Phase 10 Dashboard Refinement Plan (UI-first)

## 1) Objective
Refine the Dashboard UI to be more efficient and easier to scan while preserving the existing layout and behavior. This plan is UI-first only with no backend or data changes.

## 2) Defense Scope And Priority
- Priority: UI only (100%)
- Functionality: plan only (30% later)
- No backend changes, no database changes, no new APIs in this phase

## 3) UI Scope (What Users Will See)
### 3.1 Header Utility Strip (Small, Non-invasive)
- Add a compact strip under the page title with:
  - Current period label (static placeholder for now)
  - "Last updated" timestamp (static placeholder)
  - Link button: "Open Reports"
- Purpose: give context without changing the page structure

### 3.2 Stat Cards (Visual Clarity Only)
- Add a small trend chip under each metric (e.g., "vs last month"), styled as neutral placeholder
- Keep the same card size and layout; only add a subtle sub-row

### 3.3 Recent Client Activity Controls (Efficiency)
- Replace the status dropdown with compact filter chips:
  - All, Updated, No Entries, Needs Attention
- Show an "Active filter" line with result count (UI-only label)
- Keep existing search input and "View All" action

### 3.4 Recent Entries Table (Scan Boost)
- Add a "Last 5 entries" label above the table
- Add a tiny summary row under the header (Total amount label, UI-only placeholder)
- Keep table columns and empty state unchanged

### 3.5 Right Rail Cards (Minor polish)
- Add consistent card footers for Risk and Compliance cards with a single "View Details" link (UI-only)
- Keep existing content and ordering

## 4) UI Behavior And States
- Filter chips update active state styling only (no data changes yet)
- Active filter label updates to match selected chip (UI-only)
- Empty states remain unchanged
- Skeleton loader remains intact

## 5) Accessibility And Consistency
- Chips are keyboard reachable and use aria-pressed states
- Utility strip actions use aria-labels
- Table header remains sticky focus target for screen readers

## 6) Functionality Plan (Deferred - 30% Later)
- Populate period label and last updated from real data
- Persist the last-selected filter in localStorage
- Compute and display actual trend deltas on stat cards
- Compute and display real totals for recent entries

## 7) Acceptance Criteria (UI)
1. Dashboard layout remains visually consistent with current SafeBooks pages
2. New utility strip, chips, and labels are visible and styled
3. No backend changes are required for this phase
4. Interaction remains keyboard accessible
5. No regressions to existing dashboard behaviors

## 8) Execution Status
- Not started (UI-first plan only)
