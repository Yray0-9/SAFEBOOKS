# Forecasting Formula (SafeBooks)

## Overview
This document describes the predictive-forecast algorithm implemented in `safebooks/services/analytics_service.py`.

**Key idea:** build expected values using a weighted average of recent recorded periods (older -> newer), then apply an optional per-client uplift (`forecast_growth_percent`) multiplicatively. Net = Sales - Expenses.

---

## Steps and formulas

- Monthly/net per period:

  For each period p (period = month/quarter/year depending on frequency), the service computes:

  $$\text{net}_p = \text{sales}_p - \text{expenses}_p$$

- Active series selection:

  Periods with non-zero activity are kept. Let the active series (chronological, oldest first) be:

  $$\{s_1, s_2, \dots, s_n\} \quad\text{(sales)}$$
  $$\{e_1, e_2, \dots, e_n\} \quad\text{(expenses)}$$
  $$\{t_1, t_2, \dots, t_n\} \quad\text{(tax)}$$
  $$\{m_1, m_2, \dots, m_n\} \quad\text{(net = }s_i-e_i\text{)}$$

- Weighted average (linear increasing weights):

  Weights are linear: $w_i = i$ for $i=1\ldots n$. The weighted average is:

  $$\bar{s} = \frac{\sum_{i=1}^n w_i \cdot s_i}{\sum_{i=1}^n w_i} \quad\text{and similarly}\quad
  \bar{e} = \frac{\sum_{i=1}^n w_i \cdot e_i}{\sum_{i=1}^n w_i}$$

  Implementation note: weights = [1,2,...,n]; weight total = n(n+1)/2.

- Expected values before uplift:

  $$\text{expected\_sales} = \bar{s}\qquad\text{expected\_expenses} = \bar{e}\qquad
  \text{expected\_tax} = \overline{t}\qquad\text{expected\_net} = \overline{m}$$

- Per-client uplift (if `growth_percent` is set):

  The normalized uplift $g$ is the `forecast_growth_percent` (quantized to 0.01). The multiplier is:

  $$\mathrm{multiplier} = \frac{100 + g}{100}$$

  The service applies the multiplier to sales, expenses and tax, then recomputes net as:

  $$\text{expected\_sales}' = \text{expected\_sales} \times \mathrm{multiplier}$$
  $$\text{expected\_expenses}' = \text{expected\_expenses} \times \mathrm{multiplier}$$
  $$\text{expected\_net}' = \text{expected\_sales}' - \text{expected\_expenses}'$$

  (Values are quantized to 2 decimal places in the implementation.)

- Trend detection (separate summary forecast):

  A simple trend test is used in the non-predictive forecast path: split the recent monthly net values into two halves (older vs newer), compute older and newer averages, then:

  $$\text{change\_ratio} = \frac{\text{newer\_avg} - \text{older\_avg}}{\max(|\text{older\_avg}|, 1)}$$

  If $\text{change\_ratio} > 0.08$ → "Increasing"; if $< -0.08$ → "Decreasing"; otherwise "Stable".

- Confidence level

  - High if $n \ge 5$ active periods
  - Medium if $3 \le n < 5$
  - Low if $n < 3$

- Sparkline

  The sparkline series is the historical net series with the predicted net appended.

---

## Worked example

Given 3 active chronological periods (oldest → newest):

- sales: $s = [1000.00,\ 1200.00,\ 1100.00]$
- expenses: $e = [600.00,\ 700.00,\ 650.00]$

Weights: $w = [1,2,3]$, weight total $= 1+2+3 = 6$.

Compute weighted sales:

$$\bar{s}=\frac{1\cdot1000 + 2\cdot1200 + 3\cdot1100}{6} = \frac{1000 + 2400 + 3300}{6} = \frac{6700}{6} \approx 1116.67$$

Compute weighted expenses:

$$\bar{e}=\frac{1\cdot600 + 2\cdot700 + 3\cdot650}{6} = \frac{600 + 1400 + 1950}{6} = \frac{3950}{6} \approx 658.33$$

Expected net before uplift:

$$\overline{m} = \bar{s} - \bar{e} \approx 1116.67 - 658.33 = 458.34$$

If a per-client uplift `forecast_growth_percent = 10.00` (10%), multiplier $= 1.10$.

Apply uplift and recompute net:

$$\text{expected\_sales}' = 1116.67 \times 1.10 \approx 1228.34$$
$$\text{expected\_expenses}' = 658.33 \times 1.10 \approx 724.16$$
$$\text{expected\_net}' = 1228.34 - 724.16 = 504.18$$

(Implementation rounds to 2 decimal places.)

---

## Implementation references
- Code: `safebooks/services/analytics_service.py`
- Functions: `_weighted_average`, `_build_predictive_forecast`, `_build_forecast_from_monthly_net`

---

If you want, I can:
- Add this file to the repository and commit it, or
- Expand examples (quarterly/annual) and include step-by-step numeric tables.
