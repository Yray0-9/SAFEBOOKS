# Client Entry and Worksheet Implementation Plan

Prepared: October 24, 2026

Status: Planning reference only. The owner wants focused changes to the existing system, feature by feature. Await the next specific instruction; a separate replacement layout is not the chosen direction. Storage, API, period-rule, and financial-calculation changes are not yet approved for implementation.

## 1. Purpose and scope

Make recording a client's financial information familiar to the bookkeeper who currently uses a paper ledger and an Excel worksheet. Sales and Expenses should have their own clearly labelled amount fields and columns, instead of requiring the user to create generic transaction details and describe them. The saved result should be recognizable as the same information the bookkeeper entered.

This plan combines all feedback supplied so far. It does not treat the most recent photograph as a replacement for the earlier Excel example. Extra headings in Excel remain part of the requirements review even when they do not appear on the narrower paper ledger.

The immediate scope is entry usability, the corresponding ledger and Preview Report, and client VAT-registration identification. It is not a tax-computation engine, automatic BIR filing service, accounting-system replacement, or a new forecasting method. Do not extend unrelated account, notification, deployment, or client-profile features.

Only this plan is being written. No application implementation, database migration, record correction, or historical conversion is authorized by preparing it.

## 2. Evidence and requirements register

### 2.1 Confirmed feedback

| ID | Feedback supplied | Requirement to preserve |
|---|---|---|
| R1 | The present Add Record Entry workflow is confusing. | Reduce the need to understand generic line items before recording ordinary Sales and Expenses. |
| R2 | Sales and Expenses need their own columns and should not need individual descriptions. | Provide dedicated numeric controls; do not require the bookkeeper to type a description for these standard amounts. |
| R3 | Columns should remain present even when a client has no value for them. | Use a stable, agreed worksheet column set. Column visibility must not create financial observations. |
| R4 | Clients need to be identifiable as VAT or Non-VAT. | Add an explicit client registration attribute and display it in the directory and client context. |
| R5 | The bookkeeper recommended removing Frequency. | Review the visible control and replace confusing terminology only after covered-period information remains reliable. Do not replace frequency data with VAT registration. |
| R6 | The expected output resembles the existing Preview Report. | Evolve the existing entry/result/report flow rather than building an unrelated reporting module. |
| R7 | The user wants a clean interface suitable for less technical users. | Prefer clear labels, consistent placement, readable amounts, and short explanations over repeated technical text. |
| R8 | Existing forecasting must remain trustworthy. | Preserve the current SARIMA requirements, category/frequency boundaries, same-period Net Value, and existing stored history. |

### 2.2 What the examples establish, and what they do not

- Current modal: the user encounters Record Date, Record Frequency, Notes, and repeatable Type/Code, Description, and Amount details.
- Earlier Excel example: Type/Code and Description appear beside Year Ended, Month, Quarter, Sales, Expenses, supporting amounts, tax figures, and Remarks. Its rows appear to represent individual form-related entries. This interpretation is not yet confirmed.
- New paper example: client-profile information is above a ledger with a Period column, month labels, separate Sales/Expenses/Net Value columns, and additional tax-related columns. This strongly supports a monthly summary presentation, but does not establish that every saved entry must become one monthly summary record.
- Payment markings and crossed-out or amended handwriting are visible. They are evidence that status and corrections matter, not permission to infer amounts, payment history, or correction rules from the photograph.
- Some handwritten tax headings are not sufficiently clear to transcribe confidently. Obtain their exact names rather than inventing form codes from handwriting.
- The new photograph includes identifying details and credentials. Do not reproduce the photograph, names, contact information, identifiers, credentials, or handwritten financial amounts in this plan, fixtures, logs, screenshots, or Git. Use synthetic examples for development.

### 2.3 Main layout: follow the paper book

Use one main client worksheet with a row for each month, following the paper example. Sales, Expenses, Net Value, and the agreed tax/form amounts each have their own column. The owner pointed back to the month rows in the photograph when the earlier layout question was unclear. Use this as the working layout instead of asking the owner to choose between technical descriptions of rows.

Simple layout illustration, with no real client amounts:

| Month | Sales | Expenses | Net Value | Tax/form columns |
|---|---|---|---|---|
| January | | | | |
| February | | | | |
| March | | | | |

The bookkeeper should still be able to open the entries saved for a month to check or edit them. Their placement, such as an expandable section or an existing detail view, can be decided in the visual draft. The earlier form-by-form spreadsheet can be represented through these details without requiring Sales and Expenses to be entered again for every tax form.

One visible monthly row is not the same thing as one database record. Several legitimate source entries may contribute to it. A quarterly amount shown near its quarter-ending month must retain a Quarterly label and its exact coverage; its placement must not turn it into a monthly amount.

This clarifies the main display direction. It does not settle the unclear tax headings, amount definitions, or coverage rules, and it does not authorize implementation or changes to stored records.

## 3. Current implementation findings

Paths below are relative to the SafeBooks repository root.

| Area inspected | Confirmed current behavior | Planning consequence |
|---|---|---|
| `templates/base/financial_records_client.html` | Add and Edit collect generic line items. Both frontend and backend currently require descriptions. Copy Previous, duplicate warnings, save summaries, revisions, dirty-form protection, and error handling use this flow. | Redesign Add and Edit together. Changing only the modal markup is insufficient. |
| `safebooks/models/financial_record_line_model.py` | Each saved line has Type/Code, Description, Amount, and ordering. | Most additional worksheet headings are not currently separate typed fields. |
| `safebooks/models/financial_record_model.py` | Each record has one date, period, frequency, notes, total, revision timestamp, and related lines. | A single record cannot be assumed to express arbitrary independent coverage for each new amount. |
| `safebooks/services/financial_record_service.py` | Period is derived from entry date. The entry total is the sum of normalized line-item amounts. Writes preserve ownership, revisions, and transaction boundaries. | Separate coverage from encoding/payment date only through an explicitly approved rule change. Do not add derived totals or tax bases into the existing line-item sum. |
| `templates/base/client_details.html` | Preview Report currently groups by entry-date month, includes Sales and Expenses, derives Net Value, and generates tax columns from recorded data. | The requested fixed headings and blank-cell behavior require coordinated report changes. |
| `safebooks/services/client_service.py` and `safebooks/models/client_model.py` | There is no dedicated VAT-registration attribute. Directory responses deliberately exclude sensitive profile data. | Registration needs an approved additive field and safe serialization; do not expose private custom fields to supply a directory badge. |
| `safebooks/views.py` and `safebooks/urls.py` | Owned-client boundaries protect financial and report APIs. Full-profile reads/edits also enforce the configured client-details lock. | Retain these boundaries and existing API envelopes during integration. |
| `safebooks/services/analytics_service.py` and forecasting services | Classification, actual totals, frequency-specific histories, workload checks, and forecasts consume the saved financial lines. | New columns cannot automatically be treated as new Sales, Expenses, or Tax observations. |

The existing report uses browser-side classification and aggregation. During implementation, compare every relevant report consumer with the service-layer categories. A field that looks like a BIR payment in the report must not become a different category in analytics because of its description. Any shared classification or output change must be scoped, coordinated, and regression-tested rather than silently changing historical totals.

## 4. Proposed user flow

### 4.1 Client context

1. Open an owned client from the directory or Financial Records.
2. Show client name and TIN using existing authorized summaries, plus a short VAT / Non-VAT / Not set badge.
3. Keep registration editing in the authorized client create/edit flows, not as a replacement for an entry's frequency selector.
4. Keep the selected year and covered period visible while recording and reviewing entries.

### 4.2 Add Entry

Draft the form before connecting new persistence:

- Period covered: an understandable selection of year and month or quarter, subject to the approved coverage rule. Support existing annual entries without implying annual SARIMA support.
- Record date: retain its current meaning until encoding date versus covered period is explicitly resolved. Do not silently repurpose it as payment date.
- Sales: a dedicated amount field, initially blank, with no user-entered description required.
- Expenses: a dedicated amount field, initially blank, with no user-entered description required.
- Net Value: read-only; Sales minus Expenses only for complete, matching coverage. A blank component must not be assumed to be zero.
- Tax/form details: show the agreed codes and amount meanings separately from the main Sales/Expenses fields. A tax-only entry must not require fictitious Sales or Expenses.
- Additional worksheet amounts: include the agreed headings in the visual draft, while marking unresolved definitions in the design notes. Do not release ambiguous production inputs or invented calculations.
- Remarks: preserve relevant free-text notes. Paid/Pending markings do not become an automated payment-status system without agreement about what they mean and what evidence is recorded.

Type/Code and a meaningful form description may remain appropriate for tax details. This does not require separate descriptions for ordinary Sales and Expenses. Do not remove descriptions from historical or custom details merely because the standard controls are simpler.

At first, prefer a save with coherent coverage. Do not combine monthly Sales and quarterly Expenses into one ordinary record solely to fit the form. If a single worksheet save must create components with different coverage, obtain approval for an atomic coordinated write contract first. Several browser requests are not an acceptable substitute if failure could leave a partially saved worksheet.

### 4.3 Saved result and editing

Recommended main ledger structure:

`Period | Sales | Expenses | Net Value | agreed tax/form columns | supporting worksheet columns | Remarks`

- Keep the agreed headers stable for VAT and Non-VAT clients, including empty columns.
- Show individual contributing entries through the existing entry-detail pattern so the user can review dates, codes, amounts, coverage, and remarks before editing.
- Do not replace several source entries with a new monthly total record during a display refresh.
- Editing must open the actual source entry, carry its revision, and preserve details not changed by the user.
- Distinguish adding an additional source amount from replacing an existing summary. Never overwrite a month because the user added another tax form.
- Refresh the result only after confirmed server success. On a conflict or unknown network outcome, preserve the draft and explain how to review the saved records before retrying.

### 4.4 Preview Report and printing

- Use the same approved column definitions and source amounts as the entry/result view.
- Continue defaulting to the current bookkeeping year. Another year or All Years requires explicit selection.
- Keep all agreed columns even when they are empty for the selected client.
- Preserve source coverage. Monthly sums, quarterly values, cumulative values, credits, and payment amounts must not be presented as interchangeable figures.
- Do not display a grand total that adds Sales, Expenses, Net Value, payment bases, and tax credits together.
- For wide worksheets, use controlled horizontal scrolling on screen and an intentionally tested print layout with repeated headings. Do not shrink every column into unreadable text or silently omit required columns to fit the paper.
- Retain privacy exclusions. The paper profile header is not a reason to print passwords, private custom fields, or account credentials.

## 5. Field dictionary and calculation boundaries

This dictionary separates standard terminology from unconfirmed worksheet conventions. Official sources are listed in section 11; they do not establish the bookkeeper's custom formulas.

| Field | Proposed handling | Boundary or unresolved decision |
|---|---|---|
| Period / Year / Month / Quarter | Preserve explicit coverage and display it clearly. | Confirm calendar versus fiscal quarters, the meaning of Year Ended, and date-versus-coverage behavior. Do not copy potentially inconsistent sample quarter numbers automatically. |
| Sales | Dedicated input mapped to the approved Sales category once. | Confirm whether she enters monthly movement, a quarter total, or a cumulative figure. Do not repeat it for every tax-form entry. |
| Expenses | Dedicated input mapped to the approved Expenses category once. | Confirm whether these already include COGS/COS. Do not assume monthly and quarterly entries overlap. |
| Net Value | Existing same-period Sales minus Expenses result, with tax separate. | Do not fit a Net Value SARIMA model. Do not equate a month's Sales with a quarter's Sales base. |
| Type/Code and Description | Preserve meaningful form identifiers and descriptions for relevant details. | Confirm whether TW/PQ are her own shorthand. Do not assume she wants all descriptions removed. |
| MICT | Preserve as an unresolved worksheet heading in design notes. | BIR uses MCIT for Minimum Corporate Income Tax. A spelling correction and applicability need confirmation; VAT alone does not establish either. |
| COGS/COS | Separate supporting field if confirmed in the target worksheet. | Define its relationship to Expenses before it participates in any total. |
| Net Sales | Separate from existing Net Value. | BIR distinguishes Sales after returns/allowances/discounts from profit after expenses. Do not use the existing Net Value formula for this heading. |
| Income payments (2307) | Certificate-related base amount, not automatically another Sales entry. | Identify the certificate/source and avoid recording already-entered income a second time. |
| Tax withheld | Separate amount with an agreed direction and purpose. | Distinguish withholding from the client's income from withholding the client makes on payments to others. Neither is automatically another tax expense. |
| Tax Due | Record an agreed liability measure from the applicable return. | It is not automatically the remaining amount payable or the amount paid. Do not generate statutory tax calculations from Sales without an approved specification. |
| Remittances / credits / amount payable | Keep distinct if these are required by the worksheet. | Earlier payments, a quarter's full liability, and a remaining balance cannot all be summed as fresh Tax observations. |
| Remarks / Paid / Pending | Preserve agreed text without changing numeric records. | A stamp or remark alone does not establish payment date, amount paid, or a settlement workflow. |
| VAT registration | Proposed client-level VAT / Non-VAT / Not set selection. | Do not infer it from a name, a missing column, a single BIR form, or lack of records. Existing clients remain unclassified until confirmed. |

### Blank, zero, and not applicable

- Blank means no amount has been recorded in that field. It must not manufacture a zero line or increase the SARIMA observation count.
- An explicitly entered zero is a genuine recorded value and must survive save, reload, edit, reporting, and forecasting-input preparation.
- Not applicable is an explicit classification if the owner approves that state. Do not assign it automatically from VAT registration.
- Keep a required column visible regardless of these states. Empty visual rows or headers must not create database periods or financial records.
- Do not allow an entirely empty financial entry to masquerade as completed activity. If form-only/no-payment filing tracking is needed, specify its separate purpose and validation before adding it.

## 6. VAT registration and frequency are independent

VAT registration identifies a client attribute; frequency and coverage describe an entry. Non-VAT does not mean the client has no business or tax records. The registration badge must not disable Sales, Expenses, withholding, or supporting fields automatically.

For the requested visible Frequency removal:

1. Show the bookkeeper a clearer covered-period control rather than forcing technical terminology.
2. Preserve the internal frequency and original quarter anchor when saving and editing.
3. Determine frequency only from an approved, unambiguous period/form mapping or explicit covered-period selection. VAT/Non-VAT is never the mapping.
4. Where a generic Sales/Expenses entry is ambiguous, require clarification instead of silently defaulting every new entry to Monthly.
5. Preserve Copy Previous, duplicate warnings, record schedules, historical reports, and existing financial API compatibility.

BIR's guidance distinguishes monthly remittances such as 0619E from quarterly returns such as 1601EQ. In particular, a form that applies to the first two months of a quarter does not imply a missing filing for the third month. Its schedule must not be forced into twelve monthly observations, and a quarterly liability must not be allocated across months to fill a gap.

If the client can change registration, decide whether this release only shows current registration or also needs effective-dated history. Do not retrospectively reclassify old records when a client profile changes.

## 7. Storage and integration approach

### 7.1 Lowest-risk path first

- Dedicated Sales/Expenses controls may map to canonical lines using the current financial services, provided the same approved amount and coverage are stored exactly once. The user need not type an internal standard description.
- New controls must not rewrite existing line descriptions or merge old lines implicitly. Preserve custom and ambiguous historical details through the established editor until a reviewed mapping exists.
- Registration requires an approved additive client field, validation, migration, and coordinated create/edit/list serialization. Do not repurpose activity Remarks or private custom fields.
- Supporting amounts or return metadata may require separate typed storage. Decide this after confirming whether an entry represents a movement, a period total, a filing, a certificate, or a payment. This plan does not authorize a particular new schema.
- Do not place every additional positive amount into `FinancialRecordLine` as a generic financial movement. The present total sums lines, and unknown labels may be classified as Sales by existing consumers.
- Do not change `total_amount`, API envelopes, field meanings, or default period behavior merely to make the new display convenient. Obtain approval for any necessary coordinated contract or calculation change.

### 7.2 Preserve record safety

- Resolve the owned client at the view boundary. Preserve the configured client-details lock for profile editing.
- Validate finite Decimal amounts and model text limits server-side; retain existing two-decimal financial precision and storage bounds. A tax form's own display conventions do not authorize rounding stored application amounts to whole pesos.
- Keep record, details, status effects, and financial audit writes together under the existing owned-client lock.
- Require the received revision for edits/deletes. Never overwrite a newer entry from an old worksheet view.
- Keep notification handling after commit; no automatic retry of a write with an unknown outcome.
- New directory badges and report fields must use directory-safe client metadata, never credentials.

### 7.3 Historical compatibility

- Use additive schema changes only when approved. Preserve all current financial lines, dates, frequencies, amounts, relationships, and audit history.
- Do not backfill missing amounts as zero or assign registration defaults that pretend to be verified facts.
- Do not convert historical descriptions, retag tax lines, deduplicate entries, or reinterpret earlier periods silently.
- Where an old entry cannot be mapped confidently to the new worksheet, expose its existing details rather than guessing a new field value.
- Before rollout, compare synthetic legacy-record snapshots and totals before/after the new code. Any genuine data correction remains an explicit bookkeeper action, separate from UI rollout.

## 8. Forecasting protections

The redesign must not be used to force eligibility or alter the recent forecasting work.

- Keep 24 consecutive monthly or 8 consecutive quarterly observations per relevant client/category/frequency, with annual forecasting unsupported.
- Keep SARIMA settings, fit budgets, owner scoping, selected-year cutoffs, negative/non-finite rejection behavior, and workload limits unchanged.
- Keep Net Value calculated from complete, identical Sales/Expenses coverage and all required additive components; do not fit another model or subtract separately displayed tax.
- A quarter Sales base may use three complete monthly actual/forecast observations where already supported. A quarterly amount is not an additional monthly observation.
- Registration, visible empty columns, Paid remarks, certificates, and derived totals do not create training observations.
- Decide which single financial measure a new tax field represents before mapping it into the existing Tax series. Full liabilities, remittances, credits, and payable balances must not all become additive Tax observations for the same obligation.
- Preserve the existing All Clients distinction between native predictions and quarter comparisons that include monthly amounts. Keep report labels, Net bases, and graph lanes consistent.
- If a newly required tax concept cannot be supported by the unchanged forecast-input contract, leave it outside forecasting until an explicit, separately reviewed mapping is approved. Do not lower the requirements or substitute an undisclosed model.

## 9. Implementation phases and approval checkpoints

| Phase | Work and deliverable | Completion / approval checkpoint |
|---|---|---|
| 1. Confirm the recording contract | Use the paper-style month rows; clarify period coverage; finalize exact headings, input/derived fields, tax measures, and blank handling. Produce a small field-to-source mapping and synthetic monthly/quarterly examples. | Owner/bookkeeper approves the examples. Public BIR definitions do not substitute for custom worksheet decisions. |
| 2. Visual prototype only | Prototype the Add/Edit controls, saved ledger, entry expansion, registration badge/filter, and Preview Report. Use synthetic values only and no new persistence. | Bookkeeper recognizes the result and can explain how to add, review, edit, and cancel an entry. Check mobile, keyboard, loading, blank, error, and zero states. |
| 3. Approved data integration | Implement the smallest approved client/record schema and service changes, payload coordination, period mapping, revision handling, and canonical category rules. Keep old contracts compatible where possible. | Explicit approval precedes any migration, contract, recording-rule, or calculation change. No silent historical conversion. |
| 4. Report and consumer integration | Connect the same approved inputs to ledger summaries, Preview Report, printing, period summaries, and any required analytics mapping. | One synthetic example reconciles across entry details, worksheet, printout, totals, and eligible forecasting inputs without duplicate amounts. |
| 5. Verification and user walkthrough | Run the matrix below and a short bookkeeper walkthrough using synthetic examples before production use. | Report actual pass/fail results and unresolved limitations. Do not declare completion solely because a prototype looks correct. |

No completion dates are invented in this plan. Implementation should be delivered in reviewable stages, not as an uncontrolled rewrite of the complete system.

## 10. Affected surfaces and verification plan

### 10.1 Expected code surfaces

- Client model and any approved additive migration; `safebooks/services/client_service.py`; client views/serialization; `templates/base/clients.html`; the Client Details editor; directory/financial client context.
- Financial models only if the approved field contract needs them; `safebooks/services/financial_record_service.py`; shared validators; financial request boundaries; `templates/base/financial_records_client.html`; relevant financial CSS.
- Preview Report in `templates/base/client_details.html`; shared `static/js/reports_shared.js`; `static/js/reports_page.js` and other consumers only where the same approved report is actually used.
- Analytics/forecast input adapters only if new approved fields require mapping. The SARIMA fitting service is not a target for model changes.
- Existing financial, client, report, privacy, reliability, workload, and forecasting tests; focused new regressions for the worksheet contract.

### 10.2 Required test matrix

| Scenario | Required result |
|---|---|
| Standard Sales and Expenses | Save through dedicated controls without user-entered descriptions; reopen with exact values and no duplicated lines. |
| Sales-only / Expenses-only / Tax-only entry | Preserve missing components as missing. Do not require fabricated values or display a misleading complete Net Value. |
| Blank, explicit zero, Not applicable | Each approved state survives save/reload/edit/print. Empty presentation cells never become financial observations. |
| Additional form for an existing month | Add the correct source detail without recording that month's Sales or Expenses again. |
| Monthly and quarterly coverage | Retain exact periods and quarter anchors. Do not distribute a quarterly figure across months or label it as monthly. |
| Quarter values and earlier remittances | Use the approved liability/payment definition; never count the same obligation again just because it appears on another return. |
| Net Value and Net Sales | Net Value keeps the existing same-coverage formula. A separate Net Sales field never inherits that formula by accident. |
| VAT, Non-VAT, unclassified clients | Badge/filter works through Add Client, Edit Client, and Client Details; no arbitrary field disabling or automatic historical reclassification. |
| Legacy/custom entries | Preserve original values, descriptions, IDs/relationships, frequencies, ordering, and audit history. Ambiguous records remain editable without forced conversion. |
| Conflicts and failed saves | Keep drafts after validation/server/network failure, prevent duplicate submits, reject stale revisions, and avoid partial multi-component saves. |
| Cancel and reset | Warn before discarding changed forms, do not clear while saving, and reopen with a clean new form or the correct saved entry. |
| Ownership and privacy | Reject other bookkeepers' data, enforce profile locks, keep directory responses safe, and exclude credentials from reports and fixtures. |
| Loading and workload failures | Do not show incomplete data as an empty record history; preserve narrowing controls and disable stale printing. |
| Screen and print layout | Fixed headings remain readable on desktop/tablet/mobile; scrolling is contained; keyboard access works; print columns are not silently lost. |
| Forecast regression | Preserve original eligible outputs, history cutoffs, observation counts, native frequencies, Net bases, fit budgets, and rejection gaps. |

Use the project virtual environment for `manage.py check` and the relevant modules, including `test_clients_api`, `test_financial_records_api`, `test_financial_reliability`, `test_reports_print_layout_api`, `test_client_data_security`, `test_forecast_periods`, `test_forecast_year_history`, and `test_sarima_forecasting_service`. Run applicable JavaScript component tests and real-browser UI/print checks after implementation.

Run write-oriented tests only against disposable test databases, with synthetic accounts and financial data. Never use an existing client or the production database as a test fixture. SQLite checks do not replace PostgreSQL locking/query-plan or simultaneous-user checks where those are needed.

### 10.3 Planning-session verification

- Current source flow inspected; no application files or stored records changed for this plan.
- Django system check: passed.
- Existing Financial Reliability, Client Privacy, and Forecast Periods JavaScript checks: passed.
- Baseline Python tests: 101 passed across client APIs, financial-record APIs, report/print behavior, forecast periods/history, SARIMA, and client-data security, using an isolated in-memory test database.
- Affected templates compiled successfully: Financial Records for a client, Clients, and Client Details.
- These checks cover the existing implementation. They do not constitute validation of a redesigned form, new schema, or new tax calculations.

## 11. Research references and limits

Official BIR sources checked on October 24, 2026. Older form versions below are used for terminology and structural distinctions, not as authority to hard-code current rates, deadlines, thresholds, or the obligations of a particular client. This work records and presents the bookkeeper's confirmed figures; automated tax determination is outside scope.

1. [BIR Form 2307](https://bir-cdn.bir.gov.ph/local/pdf/2307%20Jan%202018%20ENCS%20v3.pdf): distinguishes income-payment bases from tax withheld, with monthly breakdown and quarter coverage. It does not make those payment bases additional Sales when the income is already recorded.
2. [BIR Form 1702-RT](https://bir-cdn.bir.gov.ph/local/pdf/1702-RT%20Jan%202018%20ENCS%20Final%20v3.pdf): separates Net Sales, cost of sales/services, other deductions, tax due, credits/payments, and net payable. MCIT is the standard abbreviation; the user's MICT heading remains unconfirmed.
3. [BIR 2551Q guidance](https://bir-cdn.bir.gov.ph/local/pdf/2551Q_%20Jan%202018%20Guide.pdf): includes applicable Non-VAT taxpayers, supporting the distinction between Non-VAT registration and having no financial/tax records. Do not determine a client's obligations from this label alone.
4. [BIR taxpayer guide](https://bir-cdn.bir.gov.ph/BIR/pdf/TAXPAYERS%20GUIDE%20FOR%20ONLINE%20SELLERS.pdf): distinguishes income tax, VAT/percentage tax, and monthly/quarterly withholding schedules. It is general background, not proof of the bookkeeper's custom column meanings.
5. [BIR 1601EQ completion procedure](https://efps.bir.gov.ph/efps-war/EFPSWeb_war/help/proc1601eq.html): identifies earlier first/second-month remittances within the quarter calculation. This is why a return total and amounts already remitted must not automatically become separate additive tax charges.

Research cannot establish the exact meaning of the handwritten columns, whether the user's numbers are incremental or cumulative, or whether her Tax Due heading means a liability, remaining payable, or paid amount. Keep these as recording-contract decisions.

## 12. Layout direction, remaining decisions, and next action

| Decision | What must be established | What can proceed beforehand |
|---|---|---|
| D1. Main layout clarified | Follow the paper book: month rows with separate amount columns. Decide how to open saved entries during visual review. | A non-saving visual draft using this layout. Do not repeat the earlier technical layout question. |
| D2. Coverage and dates | Monthly movement versus quarter total versus year-to-date amount; calendar/fiscal basis; encoding/payment date versus covered period. | Read-only layout work. Do not connect a new save path or silently change date mapping. |
| D3. Exact headings | Clear transcription of the paper tax headings; intended MICT/MCIT; TW/PQ descriptions; treatment of Excel-only columns. | Keep the complete earlier requirement list in the design notes rather than dropping columns absent from paper. |
| D4. Tax and supporting amounts | Which figures are entered, calculated, liability, credit, remittance, or remaining payable? Does Expenses already include COGS/COS? | Show draft fields, but no invented formulas or mapping into financial totals/forecasts. |
| D5. Empty states | Confirm the bookkeeper's intended use of blank, explicit zero, and Not applicable. | Preserve blanks and avoid fabricating zero observations. |
| D6. Registration history | Current client classification only, or effective-dated registration changes? | Prototype badges and filters; existing clients remain Not set until verified. |
| D7. Existing entries | Which legacy records can be mapped confidently and which need the existing detail editor? | Inventory mappings using synthetic examples. No historical rewrites. |

Next action: await the owner's next feature-specific instruction. Improve the existing screens incrementally to address the bookkeeper's feedback. Do not proceed with a separate replacement layout or backend changes based on the earlier proposal.
