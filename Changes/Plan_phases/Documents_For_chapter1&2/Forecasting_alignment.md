I need you to refactor the Predictive Forecasting logic in my SafeBooks system.

Current issue:
The system currently forecasts all values as monthly using Linear Regression. This is wrong because financial records have different frequencies: Monthly, Quarterly, and Annually. The system must respect each record's frequency when forecasting.

Required behavior:

1. Group financial records by:
   - Client
   - Transaction type or line item category, such as Sales, Expenses, Taxes
   - Frequency: Monthly, Quarterly, Annually

2. Do not combine monthly, quarterly, and annual records into one forecasting model.

3. Forecast each group separately:
   - Monthly records should forecast every future month.
   - Quarterly records should forecast only on quarter-ending months or every 3 months based on their recorded schedule.
   - Annual records should forecast only every 12 months based on their recorded schedule.

4. For example:
   - If Sales is recorded monthly, forecast Sales for Feb, Mar, Apr, etc.
   - If Expenses are recorded quarterly, do not show Expenses for Feb if the next quarterly period is March.
   - If Taxes are recorded quarterly, show Taxes only in the projected quarter month.
   - If a record is annual, only show it when the forecast reaches the annual period.

5. The forecast report should display projected values only when that transaction type is applicable for that forecast period.
   Example:
   - Feb 2026: show Sales only
   - Mar 2026: show Sales, Expenses, Taxes if quarterly records fall in March
   - Apr 2026: show Sales only
   - Jun 2026: show Sales, Expenses, Taxes if quarterly records fall in June

6. Keep Linear Regression as the forecasting model for now, but apply it separately per grouped dataset.

7. If a group has too few data points for Linear Regression:
   - Keep Linear Regression as the selected forecasting method
   - Use a one-point Linear Regression baseline until more records exist
   - Do not return zero unless there is truly no historical record for that transaction type.
   - If Linear Regression projects a negative amount for a scheduled monetary group, mark that value as unavailable/cannot forecast instead of displaying a confusing negative expense, tax, or sales amount.

8. Net Value should be computed per forecast period:
   Net Value = Projected Sales - Projected Expenses
   Taxes are forecasted and displayed separately, but they are not deducted from Net Value.
   If projected expenses cannot be forecast for a scheduled period, Net Value should still display the projected Sales value instead of becoming unavailable.

9. If Expenses or Taxes are not scheduled for that forecast period, they should appear as blank, N/A, or 0 depending on the current UI design, but they must not be forecasted monthly unless their frequency is monthly.

10. Update the predictive forecast table so each row respects frequency scheduling.

Expected output example:

Forecast horizon: 3 months from Jan 2026

Feb 2026:
- Sales: forecasted
- Expenses: N/A if not scheduled
- Tax: N/A if not scheduled

Mar 2026:
- Sales: forecasted
- Expenses: forecasted if quarterly
- Tax: forecasted if quarterly

Apr 2026:
- Sales: forecasted
- Expenses: N/A
- Tax: N/A

Important:
Do not break the existing Analytics UI. Only refactor the forecasting computation logic and the data preparation logic. Keep the current cards and report table, but make the values frequency-aware.
