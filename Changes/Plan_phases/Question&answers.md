# SafeBooks Capstone / Thesis Defense Q&A Guide

---

## Part 1: Priority Panel Questions (Your Core Questions)

### 1. "What is the purpose of your system—what is the whole purpose of SafeBooks?"

> **Defense Answer Script:**
> "The main purpose of **SafeBooks** is to provide freelance and independent bookkeepers with a secure, centralized web-based financial management and forecasting platform tailored to Philippine bookkeeping workflows.
>
> Instead of tracking multiple taxpayers across scattered spreadsheets and paper folders, SafeBooks helps bookkeepers:
> 1. **Organize Client Profiles & Credentials Securely:** Manage each client's TIN, VAT/Non-VAT registration, business permits, and sensitive login credentials behind ownership rules and an optional password lock.
> 2. **Record Period-Based Financial & BIR Tax Entries Accurately:** Log monthly, quarterly, and annual Sales, Expenses, and specific BIR tax forms (`0605`, `1701Q`, `2550Q`, `2551Q`, etc.) with built-in period coverage validation so entries are never misclassified.
> 3. **Generate Client-Ready Worksheets & Management Reports:** Produce both a detailed client tax worksheet for taxpayer handover and customizable summary reports with CSV export.
> 4. **Support Proactive Decision-Making with SARIMA Forecasting:** Use historical financial records to project future monthly and quarterly Sales, Expenses, Tax, and Net Value, while tracking filing schedules so bookkeepers never miss a client's recording period."

---

### 2. "Why are there two different printable Financial Summary Report formats—one inside the Selected Client's Financial Records page, and another on the main Reports page?"

> **Defense Answer Script:**
> "They serve **two different bookkeeping workflows**—one is a **client-facing yearly tax worksheet**, and the other is a **flexible date-range management report**:
>
> 1. **Client Financial Records Page (`Preview Report` — A4 Landscape Tax Worksheet):**
>    - This format is built specifically for **one selected taxpayer** and mirrors the actual physical monitoring sheet Philippine bookkeepers hand over to a client for a bookkeeping year.
>    - It uses an **A4 Landscape** layout because it expands every transaction into detailed tax worksheet columns—including Quarters (`Q1`–`Q4`), Percentage Tax (`2551Q`), Income Tax (`1701Q` / `1701`), Annual Registration (`0605`), supporting figures (`MICT`, `COGS/COS`, `2307`, `Tax Withheld`), and any custom BIR forms.
>
> 2. **Main Reports Page (`Reports` — A4 Portrait Summary & Multi-Client Generator):**
>    - The Reports page is designed for **custom date-range filtering (`Date From` to `Date To`)**, **CSV exporting**, and **portfolio-wide analysis** across either **All Clients** or a **Single Client**, as well as switching between Financial Summary, Tax Compliance, and Forecast reports.
>    - When printing for a single client from the Reports page, it produces a compact **A4 Portrait period summary** (`Period`, `Sales`, `Expenses`, `Tax`, and `Net Value`) for the exact custom date range selected, rather than a full-year tax-form worksheet."

---

## Part 2: 5 Easy Questions (System Overview, Users & Daily Workflow)

### Easy Q1: "Who are the target users of SafeBooks, and what are the user roles in the system?"
> **Answer Script:**
> "SafeBooks has two distinct roles:
> 1. **Bookkeepers (Primary Users):** Independent or firm bookkeepers who manage their own clients, record monthly/quarterly/annual financial transactions and BIR tax forms, generate reports, and view analytics and forecasts.
> 2. **System Administrators (`Admin`):** Administrators who verify and approve or reject new bookkeeper registrations after reviewing their submitted bookkeeping proof, manage active or deactivated bookkeeper accounts, and monitor system-wide audit logs. Crucially, Admins oversee account governance and cannot view or alter a bookkeeper's private client financial records."

### Easy Q2: "Why can't a newly registered bookkeeper access the workspace right away?"
> **Answer Script:**
> "Because SafeBooks handles sensitive taxpayer information, new bookkeeper accounts start in a **Pending Approval** state. After verifying their email or signing up with Google, the applicant submits a **Proof of Bookkeeping** document—such as a Business Permit, TESDA Certificate, or other qualification document (`JPG`, `PNG`, or `PDF` up to `5 MB`). An administrator must download, inspect, and acknowledge that proof before approving the account, and the bookkeeper receives an automated decision email."

### Easy Q3: "How does the system help bookkeepers quickly identify whether a client is VAT or Non-VAT?"
> **Answer Script:**
> "When adding or editing a client, the system requires an explicit **VAT** or **Non-VAT** tax registration selection. Across the Clients directory, Client Details, and Financial Records pages, SafeBooks displays high-contrast, color-coded pill badges (**Blue for VAT**, **Emerald Green for Non-VAT**, and **Amber if not yet set** for legacy records) so bookkeepers—including older users—can identify a taxpayer's registration status at a glance."

### Easy Q4: "How are client statuses (`New`, `Active`, `Closed`) determined in SafeBooks?"
> **Answer Script:**
> "Client status is resolved automatically from actual recorded bookkeeping activity rather than manual guesswork:
> - A newly added client starts as **New**.
> - Once a client has **at least two recorded non-future periods**, the system automatically promotes their status to **Active**.
> - If a business stops operations or leaves, the bookkeeper can mark the client as **Closed** (with a recorded closure reason and notes), which moves them to the Closed archive tab until explicitly reopened."

### Easy Q5: "What happens if a bookkeeper has recurring monthly entries—do they have to retype everything from scratch each month?"
> **Answer Script:**
> "No. In the Add Entry modal on the Financial Records page, SafeBooks includes a **Reuse Last Period** feature. With one click, it loads the client's most recent recorded line items and BIR form codes into the draft form so the bookkeeper only needs to update the current period's date and peso amounts before saving."

---

## Part 3: 5 Medium Questions (Validation, Privacy, Reports & Business Rules)

### Medium Q1: "How does SafeBooks protect sensitive client credentials like ORUS logins and email passwords?"
> **Answer Script:**
> "We enforce defense-in-depth at both the API and UI levels:
> 1. **Directory-Safe Redaction:** General client lists, financial record pages, and report previews use a redacted summary serializer that never returns saved passwords or private custom fields in JSON responses.
> 2. **Client Details Password Lock:** Bookkeepers can enable a password lock in Settings. Viewing or editing a client's full profile requires re-entering the bookkeeper's password to obtain a short-lived, single-client session grant that automatically clears when returning to the client directory.
> 3. **Print & Preview Exclusion:** Even if a bookkeeper has unlocked a client's profile, our report builder explicitly strips password fields so credentials can never be accidentally printed."

### Medium Q2: "How does the system prevent bookkeepers from recording a Quarterly entry on the wrong date?"
> **Answer Script:**
> "SafeBooks validates **Coverage Frequency (`Covers`)** against the **Record Date**. While monthly entries can be recorded in any calendar month, if a bookkeeper tags Sales, Expenses, or a BIR form as **Quarterly**, the system enforces the quarter-ending month rule (March for Q1, June for Q2, September for Q3, or December for Q4). If the date doesn't match, SafeBooks blocks the save, explains which line item caused the mismatch in plain language, and offers a one-click inline date correction without losing the user's draft amounts."

### Medium Q3: "How does SafeBooks classify BIR tax forms into Monthly, Quarterly, or Annual schedules?"
> **Answer Script:**
> "We maintain a dedicated metadata registry (`tax_form_frequency_service.py`) based on official BIR form schedules and versions:
> - Forms like `0619E`, `1601C`, `2550M`, and `2551M` resolve to **Monthly**.
> - Forms like `1601EQ`, `1701Q`, `1702Q`, `2550Q`, and `2551Q` resolve to **Quarterly**.
> - Forms like `1604C`, `1604E`, `1700`, `1701`, `1701A`, and `1702` resolve to **Annually**.
> - One-time or transaction-based forms like `0605` do not force a recurring schedule.
> Because classification uses the exact BIR form code and version rather than free-text descriptions, editing a form's description never corrupts schedule tracking or forecasting."

### Medium Q4: "How does the Record Schedule Status card on the Analytics page work when a specific year is selected?"
> **Answer Script:**
> "When a bookkeeper selects a specific year in Analytics, **Record Schedule Status** scopes strictly to owned records saved in that year:
> - Past years are evaluated as of December of that year, the current year is evaluated as of today, and future years never make false overdue claims.
> - Furthermore, the **Monthly entries** card checks whether any entry exists in each calendar month (even if a March entry only contains quarterly forms), while **Quarterly** and **Annual** cards track their native filing schedules and highlight any missing periods."

### Medium Q5: "How does SafeBooks ensure that a bookkeeper is notified or that clients receive updates when records are saved?"
> **Answer Script:**
> "When a bookkeeper creates or updates a financial record for a client with an email address (and has Client Record Email Notifications enabled in Settings), SafeBooks commits the database transaction first and then dispatches a notification email (`transaction.on_commit`). Similarly, when an admin approves or rejects a bookkeeper, the system tracks the exact delivery status (`Sent`, `Not sent`, `Skipped`, or `Failed`) and provides a **Retry Email** button if the mail server was temporarily unreachable."

---

## Part 4: 5 Hard Questions (SARIMA Forecasting, Concurrency, Security & Architecture)

### Hard Q1: "Why did you choose SARIMA for financial forecasting, and what are its exact model parameters and data requirements in SafeBooks?"
> **Answer Script:**
> "We chose **SARIMA (Seasonal Autoregressive Integrated Moving Average)** via `statsmodels` (`SARIMAX`) because bookkeeping cash flows and tax filings exhibit strong calendar seasonality (monthly cycles every 12 months and quarterly cycles every 4 quarters).
> - **Parameters:** We use `SARIMA(0, 1, 0)(0, 1, 0)[s]` with first-order non-seasonal and seasonal differencing (`d=1, D=1`) and Powell optimization (`maxiter=250`), where `s = 12` for Monthly series and `s = 4` for Quarterly series.
> - **Strict Data Readiness:** To prevent fabricated or unstable forecasts on sparse data, SafeBooks requires at least **24 consecutive monthly observations** (2 full seasonal cycles) for Monthly SARIMA and **8 consecutive quarterly observations** (2 full years) for Quarterly SARIMA, with no missing gaps in the sequence."

### Hard Q2: "What happens if the SARIMA model fails to converge or predicts a negative peso amount for a future period?"
> **Answer Script:**
> "SafeBooks never fabricates numbers or silently replaces invalid predictions with zero:
> - If `SARIMAX` optimization fails to converge or emits a `ConvergenceWarning`, the fit is rejected and marked as unavailable with a clear explanation.
> - If a converged model produces a **negative or non-finite value** for a specific future period, that individual period's prediction is rejected (annotated as `Negative SARIMA prediction`) without suppressing valid positive predictions in later periods of the same horizon, and the Projection Graph never bridges or interpolates across rejected periods."

### Hard Q3: "How does the Forecast Report compute projected Net Value when Sales and Expenses have different frequencies (e.g., Monthly Sales vs. Quarterly Expenses)?"
> **Answer Script:**
> "We enforce **strict coverage alignment** so a quarterly amount is never subtracted from a single month's sales:
> - Net Value is always `Sales minus Expenses` (excluding tax, which is displayed separately) over the **exact same coverage period**.
> - If a client has Monthly Sales and Quarterly Expenses, SafeBooks only computes a Quarterly Net Value on the scheduled quarter-ending month (March, June, September, or December) when **all three constituent months of Sales** (actual or valid forecast) and the **matching Quarterly Expense** are complete and reliable. It also displays the exact two-decimal Sales and Expense bases inline in the table cell so the calculation is 100% transparent."

### Hard Q4: "What happens if a bookkeeper has the same client or proof open in two browser tabs and tries to edit or delete a record at the same time?"
> **Answer Script:**
> "SafeBooks prevents lost updates and race conditions using **database row locking (`select_for_update`) combined with optimistic concurrency revisions**:
> - Every financial record and bookkeeping proof carries a revision identifier (`updated_at` timestamp token or `UUID` revision).
> - When a write request arrives, the backend locks the owned client row inside an atomic transaction (`transaction.atomic()`) and verifies that the submitted revision matches the current database revision.
> - If another tab already modified the record, the stale request is rejected with HTTP `409 Conflict`, preserving the user's draft in the UI instead of silently overwriting newer financial data."

### Hard Q5: "How does SafeBooks defend against brute-force login attacks, session hijacking, and unauthorized cross-account access?"
> **Answer Script:**
> "We implemented four layers of authentication and session security:
> 1. **Atomic Rate-Limiting Budgets:** Password login enforces shared 5-minute attempt budgets (`10` per identifier+IP pair, `30` per identifier, and `60` per IP) using HMAC-hashed cache keys, and performs dummy password hashing on unknown accounts to prevent timing attacks.
> 2. **Session Version & Credential Binding:** Every authenticated session stores a cryptographic proof bound to the user's current `password_hash`, `two_factor_secret`, and durable `session_version`. Changing a password, toggling 2FA, regenerating recovery codes, or deactivating an account increments `session_version` and immediately invalidates all other active sessions.
> 3. **Private Binary Proof Storage:** Bookkeeper verification documents are validated (magic bytes, image dimensions, unencrypted PDFs up to 20 pages without active scripts) and stored in a private database `BinaryField` with deferred loading (`defer('content')`), served only through authenticated views with `Content-Disposition: attachment`, `no-store`, `nosniff`, and CSP sandbox headers.
> 4. **Strict Ownership Scoping:** Every client, financial record, analytics, and report query filters by the authenticated `bookkeeper_id` at the view and service boundaries."


---

## Part 5: Situational / "What-If" Panel Questions

### Situational Q1: "If an admin deactivates a bookkeeper account, does that bookkeeper lose all of their client data and financial records?"
> **Answer Script:**
> "**No—none of their client data or financial records are lost.**
> - When an admin deactivates a bookkeeper (after confirming the admin password), the system sets the bookkeeper's status to `Suspended` (`Deactivated`) and increments their `session_version`, which immediately revokes any active login sessions and blocks workspace access.
> - All owned clients, periods, financial records, and audit logs remain safely stored in the database. If the admin later **reactivates** the account, the bookkeeper immediately regains access to all of their clients and historical records.
> - Furthermore, SafeBooks has a built-in safety guard in `delete_bookkeeper_account`: **an admin is strictly blocked from permanently deleting a bookkeeper account if that bookkeeper still owns any clients (`client_count > 0`)**, ensuring taxpayer financial records can never be accidentally wiped out."

### Situational Q2: "What if a bookkeeper closes a client's business in the system—are that client's past financial records deleted, and what happens if the client reopens later?"
> **Answer Script:**
> "**No records are deleted.** Closing a client (which requires selecting a closure reason) simply changes the client's status to `Closed`, records the closure timestamp and notes, and moves the client from the Active Directory tab to the **Closed** archive tab. All historical financial records and reports remain intact, and if the client resumes business, the bookkeeper can click **Reopen Client** to restore their active status."

### Situational Q3: "What if a bookkeeper uploaded the wrong image or PDF as their Proof of Bookkeeping while their account is still Pending Approval?"
> **Answer Script:**
> "While the account is still in `Pending Approval`, the bookkeeper can upload a replacement document at any time on the Pending Approval page. Replacing the proof generates a **new UUID revision and SHA-256 hash** under an atomic database lock, which automatically invalidates any previous download receipt so the admin is required to download and review the newly replaced document before approving the account."

### Situational Q4: "What if a bookkeeper loses their phone after enabling Two-Factor Authentication (2FA)—how can they log back in?"
> **Answer Script:**
> "When a bookkeeper or admin enables TOTP 2FA, SafeBooks generates a set of **one-time Recovery Codes**. If they lose access to their authenticator app, they can sign in using one of their unused recovery codes, which is atomically consumed upon verification so it cannot be reused."

### Situational Q5: "What if the internet drops or the server returns an error while a bookkeeper is filling out a long financial entry or client form—do they lose what they typed?"
> **Answer Script:**
> "**No.** SafeBooks is designed to **preserve form drafts on failed or uncertain requests**. The modal remains open with all typed line items, amounts, and selections intact, displays the specific error message, and never automatically retries a write whose outcome is uncertain, preventing duplicate financial entries."

### Situational Q6: "What if a client is brand new and only has 3 months of recorded sales—what happens when the bookkeeper opens the Forecast tab on the Analytics page?"
> **Answer Script:**
> "SafeBooks will **not** crash or invent a fake forecast. Instead, the descriptive analytics (Monthly Trend and Tax Breakdown) still load normally for those 3 months, while the Forecast section clearly displays the readiness status (e.g., `3 of 24 consecutive monthly periods recorded`) and explains that at least 24 consecutive monthly periods (or 8 consecutive quarterly periods) are required before SARIMA projections are generated."

### Situational Q7: "What if a bookkeeper logs out, or changes their password on one computer while still logged in on another computer?"
> **Answer Script:**
> "- On logout, SafeBooks waits for the server to confirm session removal before redirecting to the login screen, so a failed network request never falsely claims the user is logged out.
> - When a bookkeeper changes their password, toggles 2FA, or resets their password, the backend increments their account's `session_version`. Only the current browser that proved the change has its session renewed—every other open browser or device is immediately logged out on its next request."

---

## Part 6: 3-Algorithm Comparison & Forecasting Metrics (Google Colab Defense Guide)

### 1. Direct Answer: "What metrics should be taken from a forecasting method, and why did you use four metrics (MAE, RMSE, MAPE, and WAPE)?"

> **English Defense Script:**
> "To evaluate a financial forecasting method properly, we cannot rely on just one metric because bookkeeping data combines large peso categories (like Monthly Sales) with much smaller peso categories (like Quarterly Taxes). That is why we took **four complementary error metrics** across our 20 forecasted test periods in 2025 (12 Monthly Sales, 4 Quarterly Expenses, and 4 Quarterly Taxes):
> 1. **MAE (Mean Absolute Error — `₱7,286.00`):** Measures the **average miss in pesos** across all 20 predictions (`₱145,720 total error ÷ 20 periods`). It tells the bookkeeper how many pesos off a typical prediction is.
> 2. **RMSE (Root Mean Square Error — `₱10,275.43`):** Squares each peso error before averaging and taking the square root. Because squaring penalizes large outliers, RMSE tells us **whether the model makes dangerous, huge single-period mistakes**.
> 3. **MAPE (Mean Absolute Percentage Error — `31.33%`):** Measures the **unweighted average percentage miss** per period. However, MAPE gets distorted when actual tax values are small—for example, our Sales MAPE was only `3.54%` and Expenses was `1.97%`, but small actual Tax figures produced `144.07%`, pulling the unweighted average to `31.33%`.
> 4. **WAPE (Weighted Absolute Percentage Error — `6.06%`):** Divides the **total peso error (`₱145,720`) by the total actual peso volume (`₱2,404,422`)**. Because WAPE weights errors by actual peso size, small tax rows do not distort the overall accuracy. SARIMA achieved the lowest WAPE at **6.06%** (or **93.94% overall accuracy**, calculated as `100% - 6.06%`), which is why we selected SARIMA for SafeBooks."

> **Bisaya / Taglish Defense Script (Natural Flow for Presentation):**
> "Para ma-evaluate namo og tarong ang forecasting methods, nagkuha mi og **upat ka metrics—MAE, RMSE, MAPE, ug WAPE**—kay sa bookkeeping, lahi-lahi og kadak-on ang kantidad sa Sales, Expenses, ug Taxes:
> - **MAE (`₱7,286.00`):** Mao ni ang **average peso error** sa tanang 20 ka predictions (`₱145,720 ÷ 20`). Simple siya sabton kay peso mismo ang gawas.
> - **RMSE (`₱10,275.43`):** I-square una niya ang kada peso error bago i-average ug kuhaan og square root. Ang purpose ani kay **mas dakog silot (weight) kung naay dako kaayo nga sipyat** sa usa ka period.
> - **MAPE (`31.33%`):** Mao ni ang **average percentage error** kada period. Pero sa financial data, dali ma-distort ang MAPE kung gamay ang actual amount—sama sa among Taxes nga gamay ra og base mao niabot og `144.07%`, bisan pa og ang Sales kay `3.54%` ra ug ang Expenses kay `1.97%` ra.
> - **WAPE (`6.06%`):** Mao ni ang among **primary basis sa pagpili sa SARIMA**. Gi-total niya ang tanang absolute error (`₱145,720`) ug gi-divide sa total actual peso amount (`₱2,404,422`). Tungod kay `6.06%` ra ang overall error sa SARIMA—or **93.94% accuracy** (`100% - 6.06%`)—siya ang pinaka-accurate sa tulo ka algorithms."

---

### 2. Step-by-Step Guide to Explaining Your 3-Algorithm Comparison Notes

#### Section 2: Dataset & Setup (2023–2025)
- **What it means:** You used 3 years of client financial records (`2023` to `2025`), where **Sales** are recorded **Monthly** (12 periods/year) and **Expenses & Taxes** are recorded **Quarterly** (4 quarters/year each).
- **What to say:**
  > *"Mag-open ko karon sa among Google Colab notebook para ipakita giunsa namo pag-compare ang tulo ka forecasting algorithms, giunsa pag-measure ang ilang errors, ug nganong SARIMA among napili. Ang among dataset kay gikan 2023 hangtod 2025—Monthly para sa Sales, ug Quarterly para sa Expenses ug Taxes."*

#### Section 3: The 4 Error Metrics (Quick Definition)
- **What to say:**
  > *"Nag-gamit mi og upat ka standard forecasting metrics:*
  > 1. *Una, **MAE (Mean Absolute Error)** — pila ka pesos ang average nga sipyat.*
  > 2. *Ikaduha, **RMSE (Root Mean Square Error)** — parehas sa MAE nga in pesos, pero mas bug-at ang epekto kung naay dagko nga sipyat (outliers).*
  > 3. *Ikatulo, **MAPE (Mean Absolute Percentage Error)** — average nga porsyento sa sipyat kada period.*
  > 4. *Ikaupat, **WAPE (Weighted Absolute Percentage Error)** — ang total nga sipyat sa pesos tandi sa kinatibuk-ang actual peso amount."*

#### Section 4: The 3 Algorithms Compared
- **1. Weighted Moving Average (WMA):**
  - *Concept:* Gives heavier weight to the most recent periods and averages them, but cannot model seasonal spikes.
  - *What to say:* *"Ang una namong gi-test kay **Weighted Moving Average (WMA)**—mas dako iyang hatag nga weight sa pinaka-bag-o nga records para i-forecast ang sunod nga period, pero dili siya kabalo mo-basa og seasonal pattern."*
- **2. Holt-Winters (Triple Exponential Smoothing):**
  - *Concept:* Smooths level, trend, and seasonality (e.g., overall rising sales plus a regular December peak).
  - *What to say:* *"Ikaduha kay **Holt-Winters**—gina-tan-aw niya ang overall trend ug ang seasonal pattern, pananglitan kung ga-saka ang Sales kada tuig ug mas kusog gyud kada December."*
- **3. SARIMA (`SARIMA(0,1,0)(0,1,0)[s]`):**
  - *Concept:* Uses both period-to-period differencing ($d=1$) and year-over-year seasonal differencing ($D=1$, with $s=12$ for monthly and $s=4$ for quarterly) so it adapts tightly to changes over time and repeating annual cycles.
  - *What to say:* *"Ikatulo kay **SARIMA**—gina-gamit niya ang actual changes from period to period ug ang exact seasonal pattern gikan sa niaging tuig (`s=12` sa monthly ug `s=4` sa quarterly)."*

#### Section 5: Train vs. Test Split (`2023–2024` Train $\rightarrow$ `2025` Test)
- **What it means:** You trained each algorithm on **2023–2024** (24 months of Sales, 8 quarters of Expenses, 8 quarters of Tax—matching SafeBooks' exact `24` monthly / `8` quarterly minimum rule!) and held out **2025** (12 Monthly Sales + 4 Quarterly Expenses + 4 Quarterly Taxes = **20 test predictions**) to compare the predictions against actual 2025 numbers.
- **What to say:**
  > *"Gi-train namo ang tulo ka models gamit ang **2023 to 2024** historical data (2 full years), dayon among gi-forecast ang **2025 periods** (12 ka months sa Sales, 4 ka quarters sa Expenses, ug 4 ka quarters sa Taxes = 20 predictions tanan) ug gi-compare sa actual 2025 records."*

#### Section 6 & 7: Explaining the Exact Numbers for SARIMA (Why SARIMA Won)
If a panelist asks how each number in your SARIMA summary row was calculated, here is the exact breakdown:

| Metric | Formula | Exact Calculation on the 20 Test Predictions (2025) | Result |
| :--- | :--- | :--- | :--- |
| **WAPE** *(Primary)* | $\frac{\sum \|\text{Actual} - \text{Forecast}\|}{\sum \text{Actual}} \times 100$ | $\frac{\text{₱145,720}}{\text{₱2,404,422}} \times 100$ | **6.06%** |
| **Overall Accuracy** | $100\% - \text{WAPE}$ | $100\% - 6.06\%$ | **93.94%** |
| **MAE** | $\frac{\sum \|\text{Actual} - \text{Forecast}\|}{N}$ | $\frac{\text{₱145,720}}{20\text{ periods}}$ | **₱7,286.00** |
| **MAPE** | $\frac{12(\text{Sales \%}) + 4(\text{Exp \%}) + 4(\text{Tax \%})}{20}$ | $\frac{(12 \times 3.54\%) + (4 \times 1.97\%) + (4 \times 144.07\%)}{20}$ | **31.33%** |
| **RMSE** | $\sqrt{\frac{1}{N}\sum (\text{Actual} - \text{Forecast})^2}$ | Square all 20 peso errors $\rightarrow$ average $\rightarrow$ square root | **₱10,275.43** |
