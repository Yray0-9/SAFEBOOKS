# SAFEBOOKS USER GUIDANCE APPLICATION CHECKLIST

## Purpose

This checklist ensures that the **User Guidance System** is applied consistently across all pages while maintaining a **clean, simple, and non-overwhelming interface**.

Use this as a **final review tool** after designing each page.

---

## Core Rule

✔ Guide the user
✔ Do not overwhelm the user

If a page feels crowded → reduce guidance
If a page feels confusing → add guidance

---

## 1. PAGE HEADER CHECK

For every page:

* [ ] Does the page have a clear title?
* [ ] Is there a short helper text below the title?

### Rule:

* Keep it to **1 sentence only**
* Must explain what the page is for

### SafeBooks Baseline:

* Dashboard: "Overview of your clients and recent financial activity"
* Clients: "Manage your clients and access their financial records"
* Financial Records List: "Select a client to view and manage financial transactions"
* Financial Records Detail: "Add and manage financial entries for this client by period"

---

## 2. MAIN ACTION CLARITY

* [ ] Is the main action of the page obvious?
* [ ] Is there a primary button visible?

### Examples:

* Clients → "Add Client"
* Financial Records List → "View Financial Records"
* Financial Records Detail → "Add Financial Entry"

---

## 3. TABLE / CONTENT GUIDANCE

For every table or main section:

* [ ] Is there a short instruction above the table?

### Rule:

* Use only **1 short sentence**
* Example:
  "Click a client to view details or manage records"

---

## 4. EMPTY STATE CHECK (VERY IMPORTANT)

If no data exists:

* [ ] Is there a message explaining the situation?
* [ ] Is there a clear action button?

### Rule:

* Message must:

  * Explain what is missing
  * Suggest what to do next

---

### SafeBooks Empty-State Baseline:

* Clients Page:
  * Message: "No clients added yet"
  * Button: "Add Your First Client"

* Financial Records List:
  * Message: "No clients with financial records yet"
  * Button: "Add Client"

* Financial Records Detail:
  * Message: "No entries for this period"
  * Button: "Add First Entry"

---

## 5. BUTTON LABEL CHECK

* [ ] Are all buttons clearly labeled?

---

### Use:

✔ "Add Client"
✔ "Add Financial Entry"
✔ "View Financial Records"
✔ "Edit Client"
✔ "Delete Client"
✔ "Delete Entry"
✔ "Save Client Details"
✔ "Update Financial Entry"

---

### Avoid:

❌ "Add"
❌ "Submit"
❌ "Save" (without context)

---

## 6. FORM GUIDANCE CHECK

For every form:

* [ ] Are labels clear and understandable?
* [ ] Are placeholders helpful?

---

### Example:

✔ "Enter or select tax code (e.g., 1701, 2550M)"
✔ "Enter amount here"

---

### Rule:

* Do NOT add long instructions inside forms
* Keep guidance minimal

---

## 7. NAVIGATION CLARITY

* [ ] Can users easily go back?
* [ ] Is the next step obvious?

---

### Must include:

* Back button where needed
* Clear navigation path
* Clients → Financial Records List → Financial Records Detail flow stays consistent

---

## 8. VISUAL CLEANLINESS CHECK (VERY IMPORTANT)

* [ ] Is the page free from clutter?
* [ ] Is spacing consistent?
* [ ] Is guidance not excessive?

---

### Rule:

If you see:

* Too many texts ❌
* Too many buttons ❌

👉 Reduce immediately

---

## 9. CONSISTENCY CHECK

Across all pages:

* [ ] Same tone of text
* [ ] Same placement of helper text
* [ ] Same button styles
* [ ] Same spacing
* [ ] Static labels and JS-rendered labels are identical

---

## 10. USER SIMPLICITY TEST (CRITICAL)

Ask yourself:

* [ ] Can a first-time user understand this page in 5 seconds?
* [ ] Is it obvious what to do next?

---

If NO:
👉 Simplify the page

---

## 11. DO NOT OVER-ADD FEATURES

* [ ] Are only necessary elements present?
* [ ] Is there any unnecessary feature?

---

### Rule:

If a feature does not help the user complete a task → REMOVE it

---

## 12. FINAL EXPERIENCE CHECK

* [ ] Does the page feel easy?
* [ ] Does it feel guided but not forced?
* [ ] Would a non-technical user feel comfortable?

---

## 13. IMPLEMENTATION READINESS MAP (FOR FUTURE FUNCTIONS)

Use this to keep UI labels aligned with backend function naming.

| UI Label / Action | Current UI Flow | Future Endpoint (Proposed) | Method |
|---|---|---|---|
| Add Client | Opens add-client modal in Clients page | /api/clients/ | POST |
| Save Client Details | Submits add-client form | /api/clients/ | POST |
| Edit Client | Opens edit-client modal from row | /api/clients/{client_id}/ | PATCH |
| Update Client Details | Submits edit-client form | /api/clients/{client_id}/ | PATCH |
| Delete Client | Confirms client deletion | /api/clients/{client_id}/ | DELETE |
| View Financial Records | Opens client detail records view | /api/clients/{client_id}/financial-records/ | GET |
| Add Financial Entry | Opens add-entry modal in detail page | /api/clients/{client_id}/financial-records/entries/ | POST |
| Save Financial Entry | Submits add-entry form | /api/clients/{client_id}/financial-records/entries/ | POST |
| Add First Entry | Same action as Add Financial Entry | /api/clients/{client_id}/financial-records/entries/ | POST |
| Update Financial Entry | Submits edit-entry form | /api/financial-entries/{entry_id}/ | PATCH |
| Delete Entry | Confirms entry deletion | /api/financial-entries/{entry_id}/ | DELETE |
| Search by client name or TIN | Filters client lists (currently UI-side) | /api/clients/?search={query} | GET |
| Dashboard summary and activity | Loads metrics and recent data | /api/dashboard/overview/ | GET |

Current page routes to preserve in navigation:

* /dashboard/
* /clients/
* /financial-records/
* /financial-records/client/

---

## FINAL GOAL

Every page must feel:

✔ Clear
✔ Simple
✔ Guided
✔ Not overwhelming
✔ Professional

---

END OF CHECKLIST
