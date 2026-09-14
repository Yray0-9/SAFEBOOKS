# SAFEBOOKS DASHBOARD INTERACTIONS PROMPT

## Feature: Interactive Table with Filters and Client Modal

## Purpose

Enhance the existing dashboard by adding **interactive behavior** to the Client Overview Table.

This feature should simulate real system usage while maintaining the current UI design.

DO NOT redesign the layout. Only enhance interaction.

---

## 1. TABLE SEARCH FUNCTIONALITY

### Requirement:

Add a search input above the Client Overview Table.

### Behavior:

* User types in search bar
* Table updates in real-time
* Filters based on:

  * Client Name
  * TIN

### Design:

* Use existing input style
* Place above table (aligned with layout)
* Include search icon inside input

---

## 2. FILTER DROPDOWNS

### Add Two Filters:

#### A. Risk Level Filter

Options:

* All
* Low
* Medium
* High

#### B. Compliance Status Filter

Options:

* All
* Filed
* Pending
* Late

---

### Behavior:

* Selecting a filter updates visible rows
* Filters can work together (combined filtering)

---

### Design:

* Use Bootstrap dropdown or select
* Align beside search bar
* Keep spacing clean and balanced

---

## 3. CLICKABLE TABLE ROWS

### Requirement:

* Each row should be clickable

### Behavior:

* On click → open modal
* Cursor changes to pointer
* Add hover highlight effect

---

## 4. CLIENT DETAILS MODAL

### Purpose:

Simulate viewing detailed client information

---

### Modal Content:

Display:

* Client Name
* TIN
* Monthly Revenue
* Compliance Status
* Risk Level

Optional:

* Short note:
  "This is a preview of client financial data"

---

### Design:

* Clean modal layout

* Use badges for:

  * Risk Level
  * Compliance Status

* Include:

  * Close button
  * Smooth animation

---

## 5. HOVER INTERACTIONS

### Add Hover Effects:

#### Table Rows:

* Light background highlight

#### Risk Badges:

* Tooltip:
  Example:
  "High Risk: Late compliance and declining revenue"

#### Compliance Badges:

* Tooltip:
  Example:
  "Pending: Not yet filed"

---

## 6. MICRO ANIMATIONS

Use existing animation system:

* Fade-in for modal
* Smooth transition for filtering
* Button and row hover effects

---

## 7. EMPTY STATE HANDLING

### If no results found:

* Show message:
  "No matching clients found"

* Keep design minimal

---

## 8. UX RULES

* Do NOT overcrowd UI
* Keep spacing consistent
* Maintain current layout structure
* Ensure smooth interaction
* Avoid laggy behavior

---

## 9. TECHNICAL NOTES (UI ONLY)

* Use JavaScript for filtering logic
* No backend required
* Data can remain static for now

---

## 10. GOAL

This feature should:

* Make dashboard feel functional
* Simulate real system behavior
* Improve user engagement
* Maintain clean and professional design
* Prepare for backend integration later

---

END OF PROMPT
