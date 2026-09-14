## NEW FEATURE ADDITION: SKELETON LOADING UI

### Purpose

Introduce **skeleton loading screens** to improve perceived performance and create a smoother, more modern user experience.

This should simulate content loading before the actual UI appears, both:

* On the **Landing Page (initial load)**
* During **page navigation (short transition state)**

This is **UI-focused implementation only**, lightweight and non-intrusive.

---

## General Design Rules

* Must match the **existing blue theme**
* Use **light gray placeholders**
* Apply **subtle shimmer animation**
* Keep design **minimal and clean**
* Do NOT block the UI for too long

---

## Skeleton Style

### Colors:

* Base: Light gray
* Highlight: Slightly lighter gray (for shimmer effect)

### Shape Rules:

* Rounded corners
* Mimic real content layout
* Maintain spacing consistency

---

## Animation

Create shimmer effect:

* Smooth left-to-right gradient movement
* Slow and subtle
* Infinite loop until content loads

---

## File Structure

* static/css/skeleton.css (NEW FILE)
* Add animation styles here
* Do NOT mix with main style.css

---

## Landing Page Skeleton

### Apply Before Full Load

Create skeleton version of:

#### Navbar

* Logo placeholder
* Menu item placeholders

#### Hero Section

* Title block
* Subtitle lines
* Button placeholders
* Right-side preview box (table skeleton)

#### Features Section

* Card placeholders (3 columns)

---

## Table Skeleton (IMPORTANT)

Since your landing page includes a preview table:

* Create 3 to 5 skeleton rows
* Columns should match:

  * Client Name
  * TIN
  * Revenue
  * Status
  * Risk

Use:

* Rectangular blocks for text
* Small rounded badges for status

---

## Page Transition Skeleton

### Behavior

When user navigates to another page:

* Show a **quick skeleton flash (300ms to 800ms)**
* Then reveal actual content

### Implementation Idea (UI level)

* Use a **loading overlay or fade transition**
* Keep it very fast
* Avoid annoying delays

---

## Visibility Control

### Initial Load

* Show skeleton first
* Hide when DOM is ready

### After Load

* Smooth fade-out transition
* Reveal real content

---

## Animation and Timing

* Duration: Short and responsive
* Do NOT exceed 1 second for transitions
* No lag feeling

---

## UX Rules

* Skeleton must not feel fake or distracting
* Should enhance perceived speed
* Must not interfere with usability
* Keep it subtle and professional

---

## Integration Rules

* Do NOT modify existing layout structure
* Overlay or replace content temporarily
* Ensure consistency with current UI

---

## Goal

This feature should:

* Improve perceived performance
* Make the system feel modern and responsive
* Enhance user experience without adding complexity
* Maintain clean and professional design

---

END OF ADDITION
