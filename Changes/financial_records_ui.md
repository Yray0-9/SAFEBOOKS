# SAFEBOOKS FINANCIAL RECORDS PAGE UI PROMPT

## Project Context

You are designing the **Financial Records Page UI** for SafeBooks.

This page is responsible for handling **client financial transactions**, including:

* Period-based records (monthly)
* Multiple entries per period
* Financial tracking and summaries

This is the **core working page** of the system.

This is **UI ONLY**. No backend functionality yet.

---

## Design Goals

* Clean and structured layout
* Easy to understand for non-technical users
* Organized per client and per period
* Avoid overwhelming the user
* Maintain consistency with dashboard and clients page

---

## Layout Structure

Follow existing layout:

* Sidebar (unchanged)
* Top Navbar (unchanged)
* Main Content Area (Financial Records content)

---

## 1. Page Header Section

### Content:

* Title: "Financial Records"
* Subtitle:
  "Manage client transactions and track financial data by period"

---

## 2. Client Context Section (VERY IMPORTANT)

This must always be visible.

### Display:

* Client Name
* TIN
* Trade Name (optional)

---

### Layout:

* Card container
* Clean and highlighted
* Include:

Button:
👉 "Back to Clients"

---

## 3. Top Action Bar

### Left Side:

* Period Selector (Dropdown)

  * January to December

### Right Side:

* Button:
  "Add Entry"

---

## 4. Period-Based Section (MAIN CONTENT)

### Structure:

Display selected period clearly:

Example:
"January Records"

---

## 5. Financial Entries Table

### Purpose:

Show all entries for selected period

---

### Table Columns (Based on Manual Record):

* Date (optional)
* Sales
* Expenses
* Cost of Service
* Tax Amount
* Notes (optional)
* Actions

---

### Design:

* Clean table layout
* Use Bootstrap
* Row hover effect
* Clear spacing

---

### Actions Column:

* Edit Entry
* Delete Entry

---

## 6. Add Entry Modal (IMPORTANT)

### Trigger:

"Add Entry" button

---

### Modal Title:

"Add Financial Entry"

---

### Fields:

* Date
* Sales
* Expenses
* Cost of Service
* Tax Amount
* Notes

---

### Layout:

* Organized form
* 2-column layout where possible
* Clear labels

---

### Buttons:

* Save Entry (Primary)
* Cancel

---

## 7. Edit Entry Modal

Same as Add Entry:

* Pre-filled values
* Save changes

---

## 8. Delete Confirmation

Simple modal:

Text:
"Are you sure you want to delete this entry?"

Buttons:

* Delete
* Cancel

---

## 9. Period Summary Section

Place below the table.

### Display:

* Total Sales
* Total Expenses
* Total Cost of Service
* Total Tax

---

### Design:

* Card layout
* Clean numbers display
* Highlight totals

---

## 10. Empty State

If no entries:

Display:
"No financial records for this period"

Include:
Button:
"Add your first entry"

---

## 11. Navigation Flow (UI ONLY)

* Accessed from Clients Page
* Shows selected client automatically (UI simulation)
* "Back to Clients" returns to Clients Page

---

## 12. UI Components

### Cards

* White background
* Rounded corners
* Soft shadow

### Inputs

* Clean borders
* Blue focus state

### Buttons

* Blue primary
* Smooth hover

---

## 13. Animations

Use animations.css:

* Fade-in page load
* Modal transitions
* Table hover effects

---

## 14. Responsive Design

* Table scrollable on smaller screens
* Forms stack vertically
* Buttons remain visible

---

## 15. UX Rules (VERY IMPORTANT)

* Keep layout simple
* Avoid clutter
* Focus on readability
* Make actions obvious
* Guide the user clearly

---

## 16. Design Consistency Rules

* Do NOT change:

  * Sidebar
  * Dashboard layout
  * Theme colors
  * Typography

* Only extend existing design

---

## 17. Goal

This page must:

* Reflect real bookkeeping workflow
* Allow users to manage financial entries easily
* Be simple and intuitive
* Support multiple entries per period
* Integrate seamlessly with Clients Page

---

END OF PROMPT
