# SAFEBOOKS FINANCIAL RECORDS (FLEXIBLE ENTRY SYSTEM) UI PROMPT

## Project Context

You are redesigning the **Financial Records Entry System UI** for SafeBooks.

The previous design used **fixed columns**, which does not match real bookkeeping workflows.

This updated design must support:

* Dynamic transaction types (e.g., BIR tax codes)
* Multiple entries per period
* Multiple line items per entry

This is **UI ONLY**.

---

## Core Concept (VERY IMPORTANT)

Each financial entry must allow:

* Multiple transaction rows
* Each row representing:

  * Tax Type / Code
  * Description
  * Amount

---

## 1. Entry Structure (NEW)

Instead of fixed fields, use:

### Financial Entry:

* Date
* Notes (optional)

### Inside Entry:

👉 Dynamic Line Items Table

---

## 2. Add Entry Modal (REDESIGNED)

### Modal Title:

"Add Financial Entry"

---

### Top Fields:

* Date
* Notes (optional)

---

### Dynamic Line Items Section

This is the **core feature**

---

### Table Columns:

* Type / Code (Dropdown or Input)
* Description
* Amount
* Action (Remove row)

---

### Behavior:

* Start with 1 row by default
* User can click:

👉 "+ Add Line Item"

* Adds new row dynamically

---

## 3. Type / Code Input (IMPORTANT)

Allow:

* Dropdown (preset common types)
* OR manual input (for flexibility)

Examples:

* 1701
* 2550M
* Sales
* Expenses

---

## 4. Add Entry Buttons

* Save Entry
* Cancel

---

## 5. Entries Display Table (UPDATED)

Instead of showing fixed columns:

### Show:

* Date
* Total Amount
* Number of Line Items
* Actions

---

### Expandable Row (IMPORTANT)

Each entry row should be expandable:

👉 On click:

Show:

* List of line items inside

Example:

Type | Description | Amount

---

## 6. Period View (UNCHANGED STRUCTURE)

* Still grouped by month
* Entries listed under each period

---

## 7. Period Summary (UPDATED)

Instead of fixed totals:

Show:

* Total Amount
* Optional breakdown per type (visual only)

---

## 8. UI Design Rules

* Keep layout clean
* Avoid clutter
* Use spacing properly
* Use collapsible sections

---

## 9. UX SIMPLIFICATION (VERY IMPORTANT)

To help non-technical users:

* Label clearly:
  "Add Tax Type or Category"
* Provide placeholder examples
* Keep buttons visible and clear

---

## 10. Animations

* Smooth add/remove row
* Expand/collapse entry
* Modal transitions

---

## 11. Empty State

"No entries for this period"

Button:
"Add Entry"

---

## 12. Design Consistency

* Keep same blue theme
* Use same buttons, cards, spacing
* Do NOT redesign layout

---

## 13. Goal

This redesign must:

* Match real bookkeeping workflow
* Allow flexible data entry
* Support multiple tax types
* Be easy for non-technical users
* Prepare for real backend logic

---

END OF PROMPT
