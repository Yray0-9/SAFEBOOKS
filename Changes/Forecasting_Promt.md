# Forecasting Analytics UI Specification (Linear Regression Module)

## Module Name

Financial Forecasting Insights (Linear Regression Engine)

---

## Overview

This module extends the SafeBooks Analytics Dashboard by introducing predictive forecasting using Linear Regression. It generates future financial projections based on historical monthly data (Sales, Expenses, Tax, and Net Income).

This feature is visually integrated into the existing Analytics Page alongside:

- Descriptive Analytics (Summation)
- Trend Analysis

---

## UI Structure (Analytics Page Enhancement)

The Forecasting section will be added as a dedicated panel:

### 📍 Section Title

"Forecasting Insights (Linear Regression Model)"

---

## 1. Forecast Summary Cards

Display 4 primary forecast outputs:

- 💰 Forecasted Sales (Next Month)
- 💸 Forecasted Expenses (Next Month)
- 🧾 Forecasted Tax (Next Month)
- 📊 Forecasted Net Income (Next Month)

Each card includes:

- Current predicted value
- Small trend indicator (↑ or ↓)
- Label: “Predicted using Linear Regression”

---

## 2. Forecast Trend Visualization (Main Chart)

### Chart Type:

Line Graph

### Content:

- X-axis: Time (Months)
- Y-axis: Financial Values

### Lines Displayed:

- Actual historical data (Sales/Expenses/Net)
- Linear Regression Forecast line (future projection)

### UI Behavior:

- Historical data shown in solid line
- Forecasted values shown in dashed line
- Forecast separation marker labeled: "Forecast Start Point"

---

## 3. Forecast Insight Panel

A dedicated insight box showing:

### 📌 Model Explanation (UI Text)

"Linear Regression is used to predict financial trends by calculating the best-fit line based on historical data movement."

### 📌 Trend Interpretation:

- Increasing Trend
- Decreasing Trend
- Stable Trend

### 📌 Insight Output Example:

"Based on historical financial movement, the system predicts a steady upward trend in Net Income."

---

## 4. Forecast Report Table

A structured report section:

| Month   | Actual Value | Predicted Value | Variance |
| ------- | ------------ | --------------- | -------- |
| Month 1 | X            | -               | -        |
| Month 2 | X            | -               | -        |
| Month 3 | X            | -               | -        |
| Month 4 | -            | Predicted       | ± Value  |

Includes:

- Actual vs Predicted comparison
- Variance calculation
- Forecast accuracy preview

---

## 5. Model Selection Badge (UI Feature – Prepared for Future Expansion)

Even if only Linear Regression is currently active, include UI structure for model comparison readiness:

### Badge Section:

- 🏆 Selected Forecasting Model:
  - Linear Regression (Active)

### Subtext:

"Selected based on forecasting performance evaluation framework."

(This prepares system for future 3-model comparison requirement.)

---

## 6. Forecast Confidence Indicator

Display a confidence level based on data size:

- High Confidence (≥ 5 months data)
- Medium Confidence (3–4 months data)
- Low Confidence (< 3 months data)

Shown as:

- Colored badge (Green / Yellow / Red)
- Tooltip explanation

---

## 7. Export / Report Actions

Buttons:

- 📄 Generate Forecast Report (PDF)
- 📊 Export Forecast Data (CSV)
- 🖨 Print Analytics Report

Report includes:

- Forecast values
- Historical comparison
- Trend summary
- Model description

---

## 8. Integration with Existing Analytics Module

This forecasting module is placed AFTER:

### Existing Sections:

- Summation Analytics
- Trend Analytics

### New Section:

- Forecasting Insights (Linear Regression)

Flow:

1. User views descriptive analytics
2. User scrolls to trend analysis
3. User views forecasting insights

---

## 9. System Labeling (Important for Panel Defense)

All forecasting outputs must include:

- “Generated using Linear Regression Algorithm”
- “Based on historical financial data movement”
- “Predictive Analytics Module”

---

## 10. UI Purpose Statement

This module demonstrates:

- Predictive analytics capability
- Financial forecasting integration
- Data-driven decision support
- Transition from descriptive → predictive analytics
