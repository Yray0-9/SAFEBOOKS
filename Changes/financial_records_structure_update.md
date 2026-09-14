# SAFEBOOKS FINANCIAL RECORDS STRUCTURE UPDATE PROMPT

## Purpose

Update the Financial Records section to follow a proper **two-level navigation structure**.

Currently, the page directly shows a single client’s records. This must be corrected.

The new structure should allow users to:

1. View a list of all clients
2. Select a client
3. View that client’s financial records

---

## 1. OVERALL STRUCTURE

Financial Records must have:

### A. Financial Records Main Page (Client List View)

### B. Client Financial Records Page (Existing Detail View)

---

## 2. FINANCIAL RECORDS MAIN PAGE (NEW)

### Purpose:

Display all clients with quick access to their financial records

---

### Layout:

Follow Clients Page style for consistency.

---

### Page Header:

Title: "Financial Records"
Subtitle:
"Select a client to view and manage financial transactions"

---

### Top Action Bar:

#### Left:

* Search Bar
  Placeholder:
  "Search by client name or TIN"

#### Optional Right:

* Filter (optional, UI only)

---

### Clients Table

#### Columns:

* Client Name
* TIN
* Trade Name
* Last Activity (optional placeholder)
* Actions

---

### Actions:

* View Records (Primary action)

---

### Interaction:

* Row is clickable
* Clicking opens:
  👉 Client Financial Records Page

---

### Design:

* Same table style as Clients page
* Hover effect
* Clean spacing

---

## 3. CLIENT FINANCIAL RECORDS PAGE (EXISTING)

### IMPORTANT:

DO NOT REMOVE OR REDESIGN THIS PAGE

This is your current working UI:

* Period selection
* Add Entry modal
* Dynamic line items
* Entries table
* Summary

---

### Only Enhancement:

At top, clearly show:

* Client Name
* TIN

---

### Add Navigation Button:

👉 "Back to Financial Records"

---

## 4. NAVIGATION FLOW

### From Sidebar:

* Clicking "Financial Records"
  → Opens **Client List View**

---

### From Client List:

* Clicking client
  → Opens **Client Financial Records Page**

---

### From Detail Page:

* "Back to Financial Records"
  → Returns to list

---

## 5. DESIGN CONSISTENCY RULES

* Use same layout as:

  * Clients Page
  * Dashboard

* Keep:

  * Blue theme
  * Typography
  * Spacing
  * Table design

---

## 6. UX RULES (VERY IMPORTANT)

* Do not overwhelm user
* Keep actions clear
* Use familiar patterns (same as Clients page)
* Ensure easy navigation

---

## 7. EMPTY STATE

If no clients:

Display:
"No financial records available"

Button:
"Add Client"

---

## 8. GOAL

This update must:

* Fix incorrect navigation behavior
* Improve usability
* Match real workflow
* Maintain existing UI
* Keep system clean and scalable

---

END OF PROMPT
