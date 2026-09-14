# SAFEBOOKS DASHBOARD UI PROMPT

## Project Context

You are designing the **Dashboard Page** for SafeBooks, a web-based system for:

* Financial Records Monitoring
* Tax Compliance Tracking
* Predictive Risk Analytics

The dashboard is the **main working interface** for bookkeepers managing multiple client businesses.

This is **UI ONLY**. No backend functionality yet.

After login, users should be redirected directly to this dashboard for UI preview.

---

## Design Goals

* Clean and modern layout
* Professional and data-focused
* Easy to scan and understand
* Not crowded
* Consistent with landing page and authentication pages
* Blue-themed interface

---

## Theme and Style

### Colors:

* Primary: Blue
* Background: Light gray or very light blue
* Cards: White
* Text: Dark gray

### Style:

* Soft shadows
* Rounded corners
* Clean spacing
* Minimalist design

---

## Layout Structure

### Main Layout:

* Sidebar (left)
* Top Navbar (top)
* Main Content Area (right)

---

## 1. Sidebar (Navigation)

### Content:

* Logo: SafeBooks
* Menu Items:

  * Dashboard
  * Clients
  * Financial Records
  * Analytics
  * Reports
  * Settings

### Design:

* Fixed sidebar
* Blue accent highlight for active item
* Icons for each menu item
* Collapsible (optional UI only)

---

## 2. Top Navbar

### Content:

* Page Title: "Dashboard"
* Search bar (placeholder only)
* User Profile (top right)

  * Avatar circle
  * Dropdown placeholder

---

## 3. Dashboard Overview (Top Section)

### Cards (4 Summary Cards)

Create 4 key metric cards:

1. Total Clients
2. Active Records
3. Pending Compliance
4. High Risk Clients

### Design:

* Card layout (grid)
* Icon + number + label
* Subtle hover effect

---

## 4. Main Dashboard Content

Split into 2 sections:

---

### LEFT SIDE (Main Data Area)

#### A. Client Overview Table

This is the **core feature preview**.

### Table Columns:

* Client Name
* TIN
* Revenue
* Compliance Status
* Risk Level

### Design:

* Clean Bootstrap table

* Hover effect

* Badges:

  * Low → Blue/Green
  * Medium → Orange
  * High → Red

* Include 5 sample rows only

---

#### B. Financial Trends Section (Preview)

* Simple chart placeholder (no real data)
* Label:
  "Monthly Financial Trends"

Design:

* Card container
* Placeholder graph or bars

---

### RIGHT SIDE (Insights Panel)

---

#### A. Risk Classification Summary

Display:

* Low Risk count
* Medium Risk count
* High Risk count

Use:

* Colored indicators
* Small cards or list style

---

#### B. Compliance Status Overview

Show:

* Filed
* Pending
* Late

Use:

* Progress bars or small indicators

---

#### C. Quick Actions

Buttons:

* Add New Client
* Add Financial Record
* Generate Report

Design:

* Small button group
* Blue theme

---

## 5. Recent Activity Section

### Content:

Show sample logs:

* "Client ABC Trading record updated"
* "JMN Store marked as Pending"
* "Report generated for KRL Services"

### Design:

* Simple list
* Time label (optional)
* Clean spacing

---

## 6. UI Components

### Cards

* White background
* Rounded corners
* Soft shadow

### Tables

* Clean lines
* Hover effect
* Compact spacing

### Buttons

* Blue primary
* Outline secondary
* Smooth hover

---

## 7. Animations

Use animations.css:

* Fade-in for dashboard load
* Card hover effect
* Table row hover
* Smooth transitions

---

## 8. Responsive Design

* Sidebar collapses on mobile
* Cards stack vertically
* Table scrollable

---

## 9. Navigation Behavior (UI ONLY)

* Login button redirects to dashboard page
* Sidebar links do not need functionality yet

---

## 10. UX Rules

* Do not overcrowd
* Maintain whitespace
* Prioritize readability
* Keep layout structured
* Avoid unnecessary elements

---

## 11. Goal

The dashboard must:

* Clearly show system capabilities
* Feel like a real working system
* Be easy to navigate
* Impress users immediately
* Match modern SaaS dashboards

---

END OF PROMPT
