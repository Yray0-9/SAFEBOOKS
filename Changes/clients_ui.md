# SAFEBOOKS CLIENTS PAGE UI PROMPT

## Project Context

You are designing the **Clients Page UI** for SafeBooks.

This page is responsible for managing **client information (master data)** and serves as the entry point for all financial records.

This is **UI ONLY**. No backend functionality yet.

The design must remain consistent with:

* Dashboard layout
* Sidebar navigation
* Blue theme
* Modern, clean, professional style

---

## Design Goals

* Simple and easy to use (for non-technical users)
* Clean and organized layout
* Clear separation of sections
* Minimal but functional UI
* Consistent with existing system design

---

## Layout Structure

Follow the existing dashboard layout:

* Sidebar (unchanged)
* Top Navbar (unchanged)
* Main Content Area (Clients Page content)

---

## 1. Page Header Section

### Content:

* Title: "Clients"
* Subtitle:
  "Manage client information and access financial records"

---

## 2. Top Action Bar

Place this below the header.

### Left Side:

* Search Bar:
  Placeholder:
  "Search by client name or TIN"

### Right Side:

* Primary Button:
  "Add New Client"

---

## 3. Clients Table (Main Section)

### Purpose:

Display all registered clients in a clean, readable format.

---

### Table Columns:

* Client Name
* TIN
* Trade Name
* Location
* Actions

---

### Sample Data:

Use realistic placeholders only.

---

### Actions Column:

Include buttons/icons:

* View
* Edit
* Delete
* Add Record (IMPORTANT)

---

### Design:

* Use Bootstrap table
* Clean spacing
* Row hover effect
* Clickable rows (optional highlight only)

---

## 4. Add New Client Modal

### Trigger:

"Add New Client" button

---

### Modal Title:

"Add Client"

---

### Form Fields (Based on Manual Record):

* Client Name
* TIN
* Trade Name
* Location
* Permit Number
* Birthday (optional)
* Email Address (optional)

---

### Layout:

* Group fields properly
* 2-column layout if space allows
* Clear labels

---

### Buttons:

* Save Client (Primary)
* Cancel

---

## 5. Client Details Modal / View

### Trigger:

Click "View" or row

---

### Content:

Display clearly:

* Client Name
* TIN
* Trade Name
* Location
* Permit Number
* Email

---

### Include Button:

👉 "View Financial Records"

(This will later redirect to Financial Records page)

---

## 6. Edit Client Modal

Same layout as Add Client

* Pre-filled fields
* Save changes button

---

## 7. Delete Confirmation

Simple modal:

Text:
"Are you sure you want to delete this client?"

Buttons:

* Delete
* Cancel

---

## 8. Add Financial Record Button (IMPORTANT)

Inside table row or details modal:

👉 Button:
"Add Financial Record"

### Purpose:

* This prepares connection to Financial Records page

---

## 9. UI Components

### Cards

* White background
* Soft shadow
* Rounded corners

### Inputs

* Clean borders
* Focus highlight (blue)

### Buttons

* Blue primary
* Smooth hover
* Consistent sizing

---

## 10. Animations

Use existing animations.css:

* Fade-in for page
* Modal transitions
* Button hover effects

---

## 11. Empty State

If no clients:

Display message:
"No clients available"

Optional:
Show button:
"Add your first client"

---

## 12. Responsive Design

* Table becomes scrollable
* Forms stack vertically
* Buttons remain accessible

---

## 13. UX Rules (VERY IMPORTANT)

* Keep form simple
* Avoid too many fields at once
* Maintain spacing
* Make actions obvious
* Avoid clutter

---

## 14. Design Consistency Rules

* Do NOT change:

  * Sidebar
  * Dashboard layout
  * Color theme
  * Typography

* Only extend existing design

---

## 15. Goal

This page must:

* Allow users to easily manage clients
* Match real bookkeeping workflow
* Be easy for non-technical users
* Prepare for Financial Records integration
* Feel like part of a complete system

---

END OF PROMPT
