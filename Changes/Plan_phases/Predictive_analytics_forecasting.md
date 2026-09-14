# Predictive Analytics Forecasting (Rule-Based)

## Purpose
Provide a rule-based, non-ML projection of the next reporting period for sales, expenses, and BIR-related tax amounts to support bookkeeping planning and review.

## Data Sources
- Uses encoded financial line items from `FinancialRecordLine`.
- BIR tax amounts include:
  - Explicit tax codes (e.g., 1701, 2550Q, 0619E, etc.).
  - Any type code starting with "BIR Form".
- Sales and expenses are identified by keywords and known patterns in line item type/description.

## Forecast Scope
- **Client view:** Forecast uses only that client’s records.
- **All clients view:** Forecast is an aggregate overview and uses a monthly window across all clients.

## Frequency Selection (Client View)
- The forecast frequency is taken from the **most recent record** of the selected client.
- Only records with the **same frequency** (monthly/quarterly/annually) are used for that forecast window.
- This avoids mixing monthly and quarterly data in one projection.

## Forecast Window
- Uses the **last 6 periods** aligned to the selected frequency:
  - Monthly: last 6 months
  - Quarterly: last 6 quarters (18 months)
  - Annually: last 6 years
- If there are gaps, the window still uses the correct period steps and counts only periods with data.

## Prediction Method
- Rule-based **weighted average** over the most recent **recorded periods**:
  - Most recent period has the highest weight.
  - Older periods have lower weights.
- Optional client uplift percent multiplies the expected values (e.g., 20% uplift uses $\times 1.20$).
- Outputs:
  - Expected Sales
  - Expected Expenses
  - Expected Tax
- The forecast sparkline uses $\text{net} = \text{sales} - \text{expenses} - \text{tax}$ for consistency with Net Value.

## Confidence Logic
Confidence is based on how many periods have recorded data:
- **High:** 5+ periods
- **Medium:** 3–4 periods
- **Low:** 1–2 periods

## New or Sparse Clients
- If only **one period** exists, the forecast mirrors that period with **Low** confidence.
- If **no history** exists, forecasting is withheld and the UI shows an “insufficient data” state.

## Next Period Label
- Monthly: `Jun 2026`
- Quarterly: `Jul 2026 (Q3)`
- Annual: `Jan 2027 (Annual)`

## Limitations (For Defense)
- This is **rule-based forecasting**, not machine learning.
- It is an **indicator**, not a guarantee.
- Accuracy depends on the consistency of recorded transactions and chosen frequency.

## Defense-Ready Answer (Why Predict?)
**Short answer:** The forecast gives bookkeepers a **forward-looking indicator** so they can plan upcoming filings, cash needs, and workloads. It is not a promise of exact amounts; it is a **decision support cue** based on actual recorded patterns.

**How it helps bookkeepers:**
- **Planning:** Shows the likely next period (month/quarter/year) and estimated sales/expenses/tax to prepare documents and cash allocation.
- **Compliance readiness:** Flags the expected BIR-related tax amount ahead of the next filing period.
- **Work prioritization:** Low/Medium/High confidence tells them when to double-check records.
- **Consistency check:** If the forecast diverges from what they expect, it highlights possible missing or unusual entries.

**If asked “Predicting then what?”**
Use: *"It helps them prepare the next period’s filing and manage cash and workload earlier. It is a rule-based indicator, not a guarantee, and it complements the descriptive analytics."*

## Recommendation (Best Move)
- **Keep it** because it matches the objective and adds forward-looking value beyond descriptive analytics.
- **Frame it clearly** as a **rule-based indicator** for planning and compliance, not an exact prediction.
- If the panel insists on strict accuracy, emphasize the **confidence labels** and the **non-ML scope**.
- **Remove only if** you decide to drop predictive forecasting from the objectives entirely. Otherwise, keeping it with clear limitations is the safer defense.

## Panel Question: Mixed Frequencies (Monthly vs Quarterly)
**Question:** "Clients often have mixed frequencies (monthly sales/expenses, quarterly tax). How does the predictive forecast work?"

**Answer:** The forecast **uses one frequency per client**, chosen from the **most recent record**. This prevents mixing monthly and quarterly periods in one projection. For example, if the latest record is quarterly, the forecast uses the last 6 quarterly periods and predicts the next quarterly period. Monthly sales or expenses are still visible in descriptive analytics, but they are **not mixed into the quarterly forecast** to avoid inaccurate averages.

**Why this is acceptable:**
- It keeps the forecast **consistent and defensible** (apples‑to‑apples periods).
- It avoids inflating or diluting quarterly tax by mixing monthly entries.
- Descriptive analytics still covers monthly patterns, while forecasting focuses on the **active filing cadence**.

**If needed:** We can later extend the feature to show **separate forecasts per frequency** (Monthly / Quarterly / Annual), but the current rule keeps the logic clear and explainable for defense.
