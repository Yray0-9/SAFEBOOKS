# SafeBooks Forecasting Refactor Plan

## Goal

Replace the current Linear Regression forecasting algorithm with Weighted Moving Average (WMA), while preserving the current Analytics page behavior, UI structure, filtering behavior, and frequency-based forecasting logic.

This refactor must change only the forecasting calculation algorithm, not the existing business workflow.

---

## Important Rule

Do not rewrite the whole Analytics module.

Do not change the existing UI layout.

Do not change the client filter, year range filter, forecast horizon filter, report table structure, or existing financial record grouping behavior.

Only replace the forecasting computation from Linear Regression to Weighted Moving Average.

---

## Current System Behavior to Preserve

The system currently has these working behaviors and they must remain intact:

1. The Analytics page displays predictive forecasting results.
2. The forecast horizon filter controls how many future periods are projected.
3. Sales, expenses, tax, and net value are shown in the forecast report.
4. Net value is computed as:

```text
Projected Net Value = Projected Sales - Projected Expenses
```

Projected tax is forecasted and displayed separately, but it is not deducted from projected net value.

5. Records are based on the financial entries of the selected client.
6. Line items represent financial categories such as sales, expenses, and taxes.
7. The system already supports records with different frequencies such as:
   - Monthly
   - Quarterly
   - Annually

---

## Required Forecasting Behavior

The forecasting logic must respect the record frequency.

### Monthly Records

Monthly records must be forecasted every month.

Example:

```text
Sales recorded monthly:
Feb 2026 -> forecast sales
Mar 2026 -> forecast sales
Apr 2026 -> forecast sales
```

### Quarterly Records

Quarterly records must be forecasted only on quarter periods.

Example:

```text
Expenses recorded quarterly:
Feb 2026 -> no expense forecast
Mar 2026 -> forecast expense
Apr 2026 -> no expense forecast
May 2026 -> no expense forecast
Jun 2026 -> forecast expense
```

### Annual Records

Annual records must be forecasted only on annual periods.

Example:

```text
Annual record:
Forecast only when the projected period reaches the next annual schedule.
```

---

## Do Not Combine Different Frequencies

Do not combine monthly, quarterly, and annual data into one forecast equation.

Correct approach:

```text
Monthly sales -> forecast monthly
Quarterly expenses -> forecast quarterly
Quarterly taxes -> forecast quarterly
Annual records -> forecast annually
```

Incorrect approach:

```text
Combine monthly sales + quarterly expenses + quarterly taxes into one monthly regression model
```

That will distort the forecast and must be avoided.

---

## New Forecasting Algorithm: Weighted Moving Average

Replace Linear Regression with Weighted Moving Average.

Use this formula:

```text
Forecast = (Oldest Value × 0.2) + (Middle Value × 0.3) + (Newest Value × 0.5)
```

Using notation:

```text
F(t) = 0.2A(t-3) + 0.3A(t-2) + 0.5A(t-1)
```

Where:

```text
A(t-1) = most recent actual or forecasted value
A(t-2) = second most recent value
A(t-3) = third most recent value
```

The newest value must have the highest weight.

---

## Recursive Multi-Step Forecasting Requirement

The future forecast must be recursive.

This is very important.

Do not calculate every future period using the same last 3 historical values.

Incorrect behavior:

```text
Jan forecast = based on Oct, Nov, Dec
Feb forecast = based again on Oct, Nov, Dec
Mar forecast = based again on Oct, Nov, Dec
```

This causes repeated forecast values.

Correct behavior:

```text
Jan forecast = based on Oct, Nov, Dec
Feb forecast = based on Nov, Dec, forecasted Jan
Mar forecast = based on Dec, forecasted Jan, forecasted Feb
Apr forecast = based on forecasted Jan, forecasted Feb, forecasted Mar
```

Each new forecast must be appended to the history and used for the next forecast step.

---

## Fallback Rule for Insufficient Data

Weighted Moving Average needs at least 3 historical values.

If a category/frequency group has 3 or more values:

```text
Use Weighted Moving Average
```

If a category/frequency group has fewer than 3 values:

```text
Use latest available value as fallback forecast
```

Do not return zero unless there is truly no historical record.

Suggested fallback label:

```text
Insufficient data for WMA; latest-value fallback used
```

---

## Forecasting Function Requirement

Create or update a reusable forecasting function similar to this logic:

```text
function weightedMovingAverageForecast(history, numberOfSteps) {
    weights = [0.2, 0.3, 0.5]
    values = copy of history
    forecasts = []

    for each future step:
        if values has at least 3 records:
            lastThree = last 3 values from values
            forecast = lastThree[0] * 0.2 + lastThree[1] * 0.3 + lastThree[2] * 0.5
        else if values has at least 1 record:
            forecast = latest value
        else:
            forecast = 0

        append forecast to forecasts
        append forecast to values

    return forecasts
}
```

Adapt this to the existing project language and coding style.

---

## Integration Requirement

Wherever the system currently calls Linear Regression for forecast generation, replace only that calculation with Weighted Moving Average.

Do not change:

```text
- controller routing
- UI structure
- database schema unless absolutely necessary
- analytics cards
- forecast table columns
- client filtering
- year range filtering
- forecast horizon filtering
- net value computation
```

Only change:

```text
forecast calculation algorithm
```

---

## Frequency-Aware Forecast Report Logic

For each projected period, the system must check whether a category is scheduled for that period.

Example forecast horizon from January to June:

```text
Feb 2026:
Sales -> forecasted if monthly
Expenses -> blank/0/N/A if quarterly and not scheduled
Tax -> blank/0/N/A if quarterly and not scheduled

Mar 2026:
Sales -> forecasted
Expenses -> forecasted if quarterly
Tax -> forecasted if quarterly

Apr 2026:
Sales -> forecasted
Expenses -> blank/0/N/A if not scheduled
Tax -> blank/0/N/A if not scheduled

Jun 2026:
Sales -> forecasted
Expenses -> forecasted if quarterly
Tax -> forecasted if quarterly
```

---

## Display Requirement

The UI may continue showing the same cards and forecast table.

However, update the method label from:

```text
Linear Regression
```

to:

```text
Weighted Moving Average
```

If fallback is used, optionally show:

```text
Weighted Moving Average / fallback due to insufficient data
```

---

## Algorithm Comparison Context

The reason for replacing Linear Regression is not because Linear Regression is wrong.

The replacement is based on the algorithm comparison result where Weighted Moving Average achieved the lowest forecasting error using MAE, MAPE, and RMSE.

Selection rule:

```text
Lowest MAPE = highest forecasting accuracy
Lowest MAE and RMSE support the selection
```

---

## Validation Checklist

After implementation, verify the following:

- [ ] Sales forecasts appear monthly.
- [ ] Quarterly expenses do not appear every month.
- [ ] Quarterly taxes do not appear every month.
- [ ] Annual records only appear on annual forecast periods.
- [ ] Forecast values are not repeated incorrectly for every month.
- [ ] Multi-step WMA uses recursive forecasting.
- [ ] Net value is still computed correctly.
- [ ] UI layout remains unchanged.
- [ ] Forecast horizon filter still works.
- [ ] Client filter still works.
- [ ] Year range filter still works.
- [ ] Forecast method label displays Weighted Moving Average.

---

## Expected Final Behavior

The system should behave like this:

```text
User selects forecast horizon: 6 months

Sales:
Forecast every month because sales are monthly.

Expenses:
Forecast only on quarter periods if expenses are recorded quarterly.

Taxes:
Forecast only on quarter periods if taxes are recorded quarterly.

Net Value:
Computed per forecast period as projected sales minus projected expenses. Projected tax remains a separate forecast value and is not deducted from net value.
```

---

## Panel Defense Explanation

Use this explanation if needed:

```text
The forecasting module was refactored to use Weighted Moving Average after comparing three forecasting algorithms using MAE, MAPE, and RMSE. Weighted Moving Average achieved the lowest forecasting error on the provided dataset. The system also respects the original frequency of each financial record: monthly records are forecasted monthly, quarterly records are forecasted quarterly, and annual records are forecasted annually. This prevents monthly and quarterly data from being incorrectly combined into one forecasting equation.
```

---

## Final Instruction for Codex

Refactor carefully.

Do not redesign the module.

Do not change the working user interface.

Do not remove existing filters.

Do not change how financial records are displayed.

Only replace Linear Regression forecasting with recursive Weighted Moving Average while preserving frequency-aware forecasting behavior.
