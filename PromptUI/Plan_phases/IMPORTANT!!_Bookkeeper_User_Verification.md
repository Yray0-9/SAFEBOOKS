# Bookkeeper User Verification — Signup Identity Validation Plan

> **Status:** Pending Decision (as of September 2, 2026)
> **Purpose:** Ensure that only real, licensed bookkeepers/CPAs can register and gain access to the SafeBooks platform.
> **Context:** SafeBooks is built for bookkeepers based in the Philippines.

---

## 1. Problem Statement

Currently, when a new user signs up on the bookkeeper side, the admin has no way to verify whether the applicant is an actual licensed bookkeeper or just someone trying to gain access. The existing approval workflow only shows the user's name and email — not enough information for the admin to make an informed trust decision.

### Risks Without Verification
- Unauthorized users could access the system and view/manage sensitive financial data.
- Fake accounts could clutter the system and waste admin review time.
- No accountability trail if a non-professional gains access.

---

## 2. Recommended Solution: Professional Verification Documents at Signup

### Overview
Require the new user to submit **professional proof** during signup that the admin can review in the existing **Approvals Queue** before approving. This builds on top of the current mandatory admin approval workflow — it gives the admin the evidence they need to verify the applicant.

### What the Signup Form Would Collect (New Fields)

| Field | Type | Required | Purpose |
|---|---|---|---|
| **PRC License Number** | Text input | ✅ Yes | Professional Regulation Commission ID — verifies they are a licensed bookkeeper/CPA in the Philippines |
| **Valid Government ID Upload** | File upload (image) | ✅ Yes | Photo of a government-issued ID (e.g., PhilSys, Driver's License, Passport) to confirm identity |
| **Professional Document Upload** | File upload (image) | ✅ Yes | Photo of their PRC License / Board Certificate to confirm credentials |

### How It Works (Step-by-Step Flow)

1. **New user fills out the signup form** with their name, email, password — **plus** their PRC License Number and uploads their Government ID & PRC credential documents.
2. The signup goes to the **Pending Approval** state (which already exists in the system).
3. The admin opens the **Approvals Queue**, sees the applicant's submitted details, and can **view/download** the uploaded documents.
4. The admin **cross-checks the PRC License Number** on the official PRC Online Verification Portal to confirm the license is real and the name matches.
5. If everything checks out → **Approve**. If not → **Reject with reason**.

---

## 3. Addressing the Fake Document Concern (AI-Generated Fakes)

### The Problem
AI tools can now generate realistic-looking fake PRC cards and government IDs by replacing names and faces. This means relying **only** on uploaded document images is not secure enough.

### The Solution: PRC License Number Is the Real Verification, Not the Image

Even if someone creates a fake PRC card image with AI, they **cannot fake a record in the actual PRC database**. The Philippines' Professional Regulation Commission has a publicly accessible online verification portal.

### PRC Online Verification Portal

| Detail | Info |
|---|---|
| **URL** | [https://online.prc.gov.ph/Verification](https://online.prc.gov.ph/Verification) |
| **Requires PRC License to access?** | ❌ No — open to the **general public** |
| **Requires account/login?** | ❌ No — no login needed |
| **Cost** | ✅ Free |
| **Who can use it?** | Anyone — employers, clients, or ordinary people who want to verify a professional |

### What the Admin Can Search By
- **License Number** — type in the PRC number the applicant submitted
- **Name** — search by first name / last name
- **Profession** — filter by profession (e.g., "Certified Public Accountant")

### What the PRC Portal Shows
- ✅ Full Name of the license holder
- ✅ Profession (CPA, Bookkeeper, etc.)
- ✅ License Number
- ✅ Registration & Expiry Date
- ✅ Status — whether the license is **Valid**, **Expired**, or **Revoked**

### Why This Multi-Layer Approach Is Strong

| Attack Scenario | Result |
|---|---|
| **Fake PRC image + Real license number?** | The name on the PRC database won't match the applicant's name. **Caught.** |
| **Fake PRC image + Fake license number?** | Admin checks PRC portal, number doesn't exist or belongs to someone else. **Caught.** |
| **Real PRC image + Real license number but stolen from someone else?** | The name/photo on the PRC portal won't match the applicant. **Caught.** |
| **The only way to pass?** | Be an actual licensed bookkeeper/CPA. ✅ |

---

## 4. Admin Approvals Page Enhancements

When the admin reviews an applicant, the Approvals page should display:

1. **Applicant's Full Name** and **Email** (already exists)
2. **PRC License Number** — displayed prominently
3. **Uploaded Documents** — viewable/downloadable (Government ID and PRC License photo)
4. **"Verify on PRC Portal" Button** — opens [https://online.prc.gov.ph/Verification](https://online.prc.gov.ph/Verification) in a new tab so the admin can quickly cross-check the license number against the applicant's name
5. **Approve / Reject with Reason** actions (already exists)

---

## 5. Why This Approach Is The Best Fit

- ✅ **Not too hard to implement** — adds fields and file uploads to the existing signup + approval flow
- ✅ **Effective** — the PRC database is the real source of truth, not the uploaded image
- ✅ **Philippines-specific** — PRC License Numbers are standard for licensed bookkeepers/CPAs in the Philippines
- ✅ **Already has foundation** — the approval system already exists, this just enhances the information available to the admin
- ✅ **Free to verify** — the PRC portal is public and free, no paid third-party API needed
- ✅ **AI-fake resistant** — AI can generate fake document images but cannot insert fake records into the PRC database

---

## 6. Other Options Considered (But Less Ideal)

| Option | Why Not Ideal |
|---|---|
| **Invite-Only System** (admin sends invite link) | Too restrictive — blocks organic signups |
| **Automated PRC API Verification** | PRC doesn't have a public API for automated license verification |
| **Video Call Interview** | Too time-consuming for both parties |
| **Reference/Referral Code** | Easy to share/abuse, doesn't actually prove credentials |

---

## 7. Implementation Scope (When Approved)

### Files to Modify
- **Signup Form:** `templates/authentication/signup.html` — add PRC License Number field and document upload fields
- **Signup Backend:** `safebooks/views.py` — handle new fields and file storage
- **User Model:** `safebooks/models/` — add PRC license number and document file fields to the bookkeeper account model
- **Approvals Page:** `templates/admin_panel/approvals.html` — display PRC number, uploaded documents, and "Verify on PRC Portal" button
- **Approvals JS:** `static/js/admin_bookkeepers_page.js` — handle document viewing/downloading
- **CSS:** Update styling as needed for new form fields and document preview in approvals

### New Functionality
- File upload handling for Government ID and PRC License images
- Document storage and retrieval
- PRC License Number validation (format check)
- Document preview/download in admin approvals UI
- "Verify on PRC Portal" external link button

---

> **Next Step:** User to review this plan and decide whether to proceed with implementation.
