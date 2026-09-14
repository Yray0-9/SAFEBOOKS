# SafeBooks Forecasting Model: WMA vs SARIMA

The previous forecasting method used by SafeBooks was the Weighted Moving Average (WMA). WMA generates the next forecast by using the three most recent historical values and assigning greater importance to newer records. The formula used was:

Forecast = (0.2 × oldest value) + (0.3 × middle value) + (0.5 × most recent value)

Mathematically:

F(t+1) = 0.2Y(t-2) + 0.3Y(t-1) + 0.5Y(t)

Where:

- F(t+1) = forecast for the next period
- Y(t) = most recent actual value
- Y(t-1) = second most recent value
- Y(t-2) = third most recent value

For example, if the last three monthly sales records are:

- October = 100,000
- November = 110,000
- December = 120,000

The WMA forecast is:

Forecast = (0.2 × 100,000) + (0.3 × 110,000) + (0.5 × 120,000)

Forecast = 20,000 + 33,000 + 60,000

Forecast = 113,000

Therefore, the forecast for the next month would be 113,000.

The main limitation of WMA is that it only considers the most recent values. It does not directly recognize repeating seasonal patterns. For example, January 2023, January 2024, and January 2025 may have a stronger relationship with each other because they occur during the same month of different years. WMA does not directly capture this relationship because it focuses mainly on the immediately preceding records.

The new forecasting model selected for SafeBooks is the Seasonal Autoregressive Integrated Moving Average, or SARIMA. SARIMA is a statistical time-series forecasting model designed to handle both non-seasonal changes and recurring seasonal patterns in historical data.

The general structure of SARIMA is:

SARIMA(p, d, q)(P, D, Q, s)

Where:

- p = non-seasonal autoregressive order
- d = non-seasonal differencing order
- q = non-seasonal moving-average order
- P = seasonal autoregressive order
- D = seasonal differencing order
- Q = seasonal moving-average order
- s = seasonal period or length of the repeating cycle

For monthly financial records, the seasonal period can be:

s = 12

This represents a yearly cycle consisting of 12 months.

For regularly spaced quarterly financial records, the seasonal period can be:

s = 4

This represents a yearly cycle consisting of four quarters.

The SARIMA configuration used during the SafeBooks forecasting evaluation was:

SARIMA(0,1,0)(0,1,0,s)

This configuration applies both regular differencing and seasonal differencing. A simplified way of understanding its one-step forecasting behavior is:

Predicted Value = Most Recent Value + Value from the Same Seasonal Period - Previous Value Before that Seasonal Period

This may be represented as:

Ŷ(t) = Y(t-1) + Y(t-s) - Y(t-s-1)

Where:

- Ŷ(t) = predicted value
- Y(t-1) = most recent historical value
- Y(t-s) = value from the corresponding previous seasonal period
- Y(t-s-1) = value immediately before the corresponding seasonal period
- s = seasonal length

For example, suppose SafeBooks wants to forecast January 2026 using monthly sales records. Since monthly records use a seasonal period of 12, the model can consider the relationship between recent records and records from the corresponding period of the previous year.

Example values:

- December 2025 = 112,820
- January 2025 = 222,491
- December 2024 = 118,205

Using the simplified seasonal relationship:

Forecast = December 2025 + January 2025 - December 2024

Forecast = 112,820 + 222,491 - 118,205

Forecast = 217,106

Therefore, the simplified example forecast for January 2026 would be approximately 217,106.

This example is only intended to explain the behavior of the selected SARIMA configuration. The actual SafeBooks implementation should use the statistical SARIMA model through the Python `statsmodels` SARIMAX implementation instead of manually calculating forecasts using only this simplified formula.

## Difference Between WMA and SARIMA

| Feature | Weighted Moving Average (WMA) | SARIMA |
|---|---|---|
| Uses recent historical values | Yes | Yes |
| Uses fixed weights | Yes | No |
| Focuses mainly on the last three records | Yes | No |
| Can represent seasonal patterns | No | Yes |
| Can account for changes over time | Limited | Yes |
| Can model monthly or quarterly seasonal cycles | No | Yes |
| Requires regularly spaced historical records | Preferably | Yes |
| Complexity | Simple | More advanced |
| Selected after SafeBooks model evaluation | No | Yes |

The main difference is that WMA asks:

"What happened in the most recent records?"

SARIMA considers:

"What happened recently, how has the time series changed, and are there repeating patterns from previous seasonal periods?"

For example, WMA may forecast January mainly from the records immediately before January. SARIMA can also consider how January behaved during previous yearly cycles when sufficient regularly spaced historical data are available.

## How SARIMA Should Work in SafeBooks

The forecasting process in SafeBooks should follow this general flow:

1. The Bookkeeper enters financial records for a client.
2. SafeBooks retrieves the historical financial records for the selected client and financial category.
3. The records are arranged in chronological order.
4. The system checks whether sufficient historical observations are available.
5. The system checks whether the records are regularly spaced according to their reporting frequency.
6. The system identifies the appropriate seasonal period.
7. For monthly records, the seasonal period is set to 12.
8. For regularly spaced quarterly records, the seasonal period is set to 4.
9. The SARIMA model is fitted using the available historical values.
10. SARIMA processes the non-seasonal and seasonal changes found in the historical series.
11. The model generates the requested future forecast.
12. The resulting forecast is displayed in the SafeBooks analytics module for Bookkeeper review.

Example for monthly sales:

Client A
→ Monthly Sales Records
→ Historical Records from 2023 to 2025
→ Check Record Regularity
→ Seasonal Period = 12
→ Fit SARIMA Model
→ Generate Future Monthly Sales Forecast
→ Display Forecast in Analytics

Example for quarterly expenses:

Client A
→ Quarterly Expense Records
→ Historical Quarterly Records
→ Check Record Regularity
→ Seasonal Period = 4
→ Fit SARIMA Model
→ Generate Future Quarterly Expense Forecast
→ Display Forecast in Analytics

## Why SARIMA Replaced WMA

Weighted Moving Average was originally used because it is simple and gives greater importance to recent financial observations. However, after additional historical records became available, the data showed repeating monthly and quarterly patterns that WMA could not directly model.

Three forecasting models were therefore evaluated:

1. Weighted Moving Average (WMA)
2. Holt-Winters Exponential Smoothing
3. Seasonal Autoregressive Integrated Moving Average (SARIMA)

The three models were evaluated using the same historical financial dataset and holdout testing approach. Their forecasts were compared with actual values using the following error metrics:

- Mean Absolute Error (MAE)
- Mean Absolute Percentage Error (MAPE)
- Root Mean Square Error (RMSE)
- Weighted Absolute Percentage Error (WAPE)

Lower error values indicate better forecasting performance.

Based on the reported SafeBooks forecasting evaluation, SARIMA obtained the lowest overall errors among the three evaluated models. Its reported WAPE was:

WAPE = 6.06%

The reported WAPE-based overall forecasting accuracy was calculated as:

Overall Accuracy = 100% - WAPE

Overall Accuracy = 100% - 6.06%

Overall Accuracy = 93.94%

Therefore, SARIMA was selected as the forecasting model for the SafeBooks forecasting component.

## Important Requirements Before Generating a SARIMA Forecast

SafeBooks should not automatically generate a SARIMA forecast for every available record. Before forecasting, the system should check the following conditions:

1. There must be sufficient historical data.
2. Historical records must be arranged chronologically.
3. Records must follow a regular reporting frequency.
4. The system must identify whether the records are monthly or quarterly.
5. The correct seasonal period must be assigned.

For monthly records:

Seasonal Period = 12

For regularly spaced quarterly records:

Seasonal Period = 4

Examples of regularly spaced monthly records:

January
→ February
→ March
→ April
→ May

Examples of regularly spaced quarterly records:

March
→ June
→ September
→ December

An irregular sequence such as:

January
→ March
→ April
→ September

should not automatically be treated as a regular seasonal series. Missing or irregular periods should be properly handled before the SARIMA model is applied.

## Simplified Developer Implementation Flow

OLD WMA PROCESS:

Historical Financial Records
→ Retrieve the Last Three Values
→ Apply Fixed Weights of 0.2, 0.3, and 0.5
→ Calculate Weighted Average
→ Generate Forecast
→ Display Forecast

NEW SARIMA PROCESS:

Historical Financial Records
→ Filter Records by Client and Financial Category
→ Sort Records Chronologically
→ Check Sufficient Historical Data
→ Check Regular Reporting Frequency
→ Determine Seasonal Period
→ Monthly = 12
→ Quarterly = 4
→ Fit SARIMA Model Using SARIMAX
→ Generate Future Forecast
→ Display Forecast in SafeBooks Analytics

## Important Developer Note

The existing WMA forecasting function should not simply be renamed to SARIMA. SARIMA uses a fundamentally different forecasting process.

The developer should replace the WMA forecast calculation with an actual SARIMA implementation, such as the `SARIMAX` model provided by the Python `statsmodels` library.

The evaluated model configuration was:

SARIMA(0,1,0)(0,1,0,s)

The value of `s` depends on the frequency of the records:

- Monthly records: s = 12
- Quarterly records: s = 4

The simplified seasonal equation shown earlier is intended only to explain the concept. The actual application should rely on the fitted SARIMA/SARIMAX statistical model to generate forecasts.

In summary, WMA primarily predicts future values using a fixed weighted combination of the three most recent historical records. SARIMA, in contrast, uses a statistical time-series approach that can represent both changes over time and recurring seasonal patterns. Because SARIMA achieved lower forecasting errors during the SafeBooks model comparison, it was selected as the new forecasting model for the system.