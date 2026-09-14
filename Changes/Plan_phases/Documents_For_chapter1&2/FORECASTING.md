# SafeBooks SARIMA Forecasting Migration Plan

**Document purpose:** Plan the replacement of the current Weighted Moving Average (WMA) forecasting implementation with the selected Seasonal Autoregressive Integrated Moving Average (SARIMA) model.

**Status:** SARIMA runtime migration completed and locally verified on July 25, 2026. The reproducibility, real-data readiness, adviser-acceptance, and deployment gates below remain required before the forecasting study is presented as fully validated.

**Selected model:** SARIMA `(0,1,0)(0,1,0)s`

**Selection basis:** The documented time-based holdout comparison reports that SARIMA produced the lowest MAE, MAPE, RMSE, and WAPE among SARIMA, Holt-Winters, and WMA. This result supports its selection for SafeBooks, but it does not mean that SARIMA will be the most accurate model for every future client dataset.

## 0. Final readiness decision

Replacing WMA with SARIMA is now implemented in the current Django application. The local dependency, service, integration, and regression checks pass, but the following evidence and release gates must still be completed:

| Blocking gate | Why it is required | Pass condition |
|---|---|---|
| Reproducible comparison | The reported 93.94% WAPE-based presentation value cannot be independently regenerated from the files currently in the repository. | A sanitized dataset and executable script reproduce the accepted model ranking within an agreed rounding tolerance. |
| Evaluation-production series parity | The current service forecasts very granular groups, while the documents describe monthly sales and quarterly expense/tax series. A model that wins on one aggregation level is not automatically validated for another. | The evaluation script and production series builder use the same client scope, category, frequency, transaction grouping, period alignment, and missing-value policy. |
| Client data-readiness audit | Existing SafeBooks clients may not have the consecutive 24 monthly or 8 quarterly observations required by this project policy. | A read-only audit reports how many real client series are eligible, irregular, insufficient, annual-only, or zero-only before the default model changes. |
| Runtime and deployment check | SARIMA adds NumPy, SciPy, pandas, Patsy, and statsmodels and is substantially heavier than WMA. | The pinned dependency set passes locally under Python 3.14.3; the same installation and tests must still pass in the deployment Linux environment. |
| Adviser acceptance of unavailable states | A truthful SARIMA-only migration may show no forecast for short or irregular histories instead of displaying a fallback value. | The adviser accepts the documented unavailable behavior and annual-frequency exclusion. |

The running local system now identifies and calculates forecasts through SARIMA. Until the remaining gates pass, the documented 93.94% WAPE-based value must still be presented only as the result of the reported holdout evaluation and not as a universal accuracy guarantee or proof of deployment readiness.

### Decisions already locked

- The candidate production model is fixed at SARIMA `(0,1,0)(0,1,0)s`.
- Monthly and quarterly histories remain separate native-frequency series.
- Monthly uses `s = 12`; quarterly uses `s = 4`.
- Annual SARIMA forecasting is unsupported until separately evaluated.
- Missing periods are not treated as recorded zero amounts.
- Negative or non-finite forecasts are unavailable, not clamped to zero.
- Net value remains forecast sales minus forecast expenses; tax remains separate.
- WMA, latest-value, and other fallback values must never be labeled SARIMA.

## 1. Target outcome

SafeBooks will generate forecasts through SARIMA when a client has enough regularly spaced historical observations for the applicable reporting frequency. The migration must preserve the existing Analytics page, client-level analytics, horizon selection, transaction categorization, reporting schedules, and JSON response structure as far as practical. Only the forecasting method, its data-eligibility rules, method labels, and related tests should change.

The implementation must never label a WMA result, a latest-value result, or another fallback calculation as SARIMA. When the SARIMA requirements are not met, the interface must clearly state that a forecast is unavailable and identify the reason in plain language.

## 2. Verified current system behavior

The forecasting integration remains in `safebooks/services/analytics_service.py`, while the statistical model is isolated in `safebooks/services/forecasting_service.py`. It now:

- groups transaction details by Bookkeeper/client, financial category, and stored record frequency;
- forecasts sales, expenses, and tax-related amounts separately;
- keeps monthly and quarterly histories separate and preserves their established calendar anchors;
- applies SARIMA `(0,1,0)(0,1,0)s`, with `s = 12` for monthly and `s = 4` for quarterly histories;
- requires 24 consecutive monthly or 8 consecutive quarterly observations;
- reports insufficient, irregular, annual, failed, negative, or non-finite cases as unavailable instead of using WMA or latest-value fallback;
- returns future projections for the selected horizon and calculates expected net as sales minus expenses, with tax shown separately; and
- exposes SARIMA labels and readiness messages in the Analytics and Client Details interfaces.

Relevant implementation areas are:

| Area | Current location | Planned treatment |
|---|---|---|
| Forecast grouping and response assembly | `safebooks/services/analytics_service.py` | Implemented; evaluation-production aggregation parity remains an evidence gate. |
| Forecast model code | `safebooks/services/forecasting_service.py` | Implemented as an isolated SARIMA service. |
| API and forecasting tests | `safebooks/tests/test_analytics_summary_api.py` and `test_sarima_forecasting_service.py` | Implemented and passing locally. |
| Analytics labels and messages | `templates/base/analytics.html` | Updated to SARIMA and readiness-based wording. |
| Client analytics labels and messages | `templates/base/client_details.html` | Updated to the same method and status wording. |
| Statistical dependency | `requirements.txt` | `statsmodels==0.14.6` added and locally verified. |

No database schema migration is expected for the algorithm replacement itself.

## 3. Mandatory evidence gate before implementation

The Chapter 1 and Chapter 2 files contain the reported comparison and selected configuration, but the workspace does not currently contain the source evaluation dataset or a reproducible script that generated the reported values. The implementation must not begin by assuming that the table alone is sufficient evidence.

Before changing the live forecasting code, create a reproducibility package containing:

1. the exact dataset used for the comparison, with private client information removed or replaced by non-identifying codes;
2. a data dictionary explaining each date, frequency, category, and amount column;
3. a script that rebuilds each evaluated time series using the same aggregation rules intended for SafeBooks;
4. the fixed training period of 2023-2024 and test period of 2025;
5. the exact WMA, Holt-Winters, and SARIMA specifications;
6. the treatment of missing observations and zero actual values;
7. the calculated MAE, MAPE, RMSE, WAPE, and `100 - WAPE` presentation value; and
8. a machine-readable results file that reproduces Table 4 within an agreed rounding tolerance;
9. a manifest identifying the aggregation key used for every evaluated series; and
10. a rolling-origin sensitivity report when the available history permits it, used as a robustness check rather than as a silent replacement for the documented 2025 holdout result.

Suggested future location:

```text
analysis/forecasting/
|-- README.md
|-- data/
|   `-- forecasting_evaluation_sanitized.csv
|-- evaluate_models.py
|-- expected_results.json
`-- generated_results.csv
```

The gate passes only if another project member can run the script in a clean environment and reproduce the reported ranking. The script must also build series at the exact granularity planned for production. If either the ranking or aggregation differs, the evaluation, manuscript, and integration choice must be reconciled before implementation.

The reported `93.94%` is `100 - WAPE` for the documented holdout. It is not a universal probability of correctness, a confidence level, or a guarantee for every client. It must be presented as a WAPE-based evaluation value tied to that dataset and split.

## 4. SARIMA model specification

The general multiplicative seasonal ARIMA form is:

```text
Phi_P(B^s) phi_p(B) (1 - B)^d (1 - B^s)^D y_t
    = c + Theta_Q(B^s) theta_q(B) epsilon_t
```

Where:

- `B` is the backshift operator;
- `p`, `d`, and `q` are the non-seasonal autoregressive, differencing, and moving-average orders;
- `P`, `D`, and `Q` are the corresponding seasonal orders;
- `s` is the number of observations in one seasonal cycle; and
- `epsilon_t` is the random error at time `t`.

For the selected SafeBooks specification, all autoregressive and moving-average orders are zero, while both ordinary and seasonal differencing are one:

```text
(1 - B)(1 - B^s)y_t = epsilon_t
```

The planned `statsmodels` configuration is:

```python
SARIMAX(
    series,
    order=(0, 1, 0),
    seasonal_order=(0, 1, 0, seasonal_period),
    trend="n",
    simple_differencing=False,
)
```

The model will be fitted without displaying optimizer output, and forecasts will be obtained through `get_forecast(steps=...)`. `get_forecast` is preferred because it provides the predicted mean and retains access to prediction intervals if a later approved requirement needs them. Prediction intervals will not be added to the present interface during this migration because they were not part of the evaluated requirement.

The following settings must remain fixed during the initial integration:

- no automatic order search;
- no exogenous variables;
- no logarithmic or other transformation that was absent from the comparison;
- no growth-percentage adjustment after the model output;
- no refitting with test-period observations during validation; and
- no change to the selected orders without repeating the model comparison and updating the documents.

## 5. Production data contract

SARIMA requires an ordered time series with a known and consistent interval. SafeBooks must never combine different clients or record frequencies in one equation. The final category and transaction grouping is deliberately gated because it must match the series used in the accepted comparison.

Two candidate aggregation levels must be compared against the evaluation package:

```text
Candidate A: Bookkeeper/client + category + record frequency
Candidate B: Bookkeeper/client + category + record frequency + transaction grouping key
```

The current production service uses Candidate B, including separate tax-form grouping and transaction type/code grouping. The documents more closely describe Candidate A. The migration must not choose between them by convenience. The accepted evaluation script decides the production grouping. If SARIMA was evaluated only on Candidate A, deploying separate Candidate B models would require a new comparison at that granularity.

The series builder must then:

1. aggregate duplicate transaction details within the same expected period;
2. sort periods chronologically;
3. create an explicit calendar index for the selected frequency;
4. distinguish a missing period from an explicitly recorded zero amount;
5. reject irregular series instead of silently compressing the dates; and
6. return the reason when the series is not eligible.

An absent expected period must not automatically be filled with zero. A zero means that the Bookkeeper recorded a value of zero; a missing period means that SafeBooks has no observation for that period. Treating the two as equal could create false seasonal patterns and change the evaluation basis.

### Frequency rules

| Record frequency | Seasonal period | Initial minimum history | Forecasting decision |
|---|---:|---:|---|
| Monthly | `s = 12` | 24 consecutive monthly observations | Eligible after all validation checks pass. |
| Quarterly | `s = 4` | 8 consecutive quarterly observations | Eligible after all validation checks pass; mark the result as based on limited history because only two seasonal cycles are available. |
| Annual | Not applicable under the selected configuration | Not applicable | Do not generate a SARIMA forecast until an annual model is separately evaluated and documented. |

The 24-month and 8-quarter thresholds match the two seasonal cycles available in the documented 2023-2024 training period. They are SafeBooks project eligibility policies, not universal mathematical minima and not guarantees of accuracy. Published forecasting research notes that minimum sample requirements depend on model complexity and random variation, and real data can require substantially more history. The readiness audit must therefore report both threshold eligibility and the actual number of complete cycles.

Annual records remain supported for entry, storage, summaries, schedule monitoring, and reports. They are excluded only from SARIMA forecasting because annual observations do not have a meaningful within-year seasonal period, and a seasonal period of one is not a valid substitute for the selected monthly or quarterly configuration.

The seasonal period must follow the record frequency, not the financial category. For example, monthly expenses use `s = 12`, while quarterly sales use `s = 4`, if such records are allowed and have sufficient regular history.

## 6. Forecast horizon and aggregation rules

The current interface expresses the forecast horizon in future calendar months. The SARIMA service will forecast in the native steps of each group and then map those steps to the calendar slots already used by the response.

- Monthly groups produce one model step for every future month.
- Quarterly groups produce values only on the future quarterly dates established by that group's schedule.
- Annual groups display `Forecast unavailable for this frequency` until an annual configuration is validated.
- Groups with different frequencies are never placed in the same SARIMA equation.
- The model is fitted once per eligible group for a request, and enough future steps are requested to cover the selected horizon.
- Forecasts from eligible groups are summed only after each group has been processed independently.

Quarterly indexing must reuse the same anchor semantics as SafeBooks record scheduling. A client whose recorded three-month cycle begins in January may use January-March as its first three-month record period; the series builder must not silently reinterpret that history as a different calendar-quarter endpoint. SARIMA still receives equally spaced quarterly steps with `s = 4`, while a dedicated mapping layer converts those native steps to the existing SafeBooks calendar labels.

For a client-level category, SafeBooks must not silently omit an ineligible scheduled group and present the remaining sum as complete. The result should be unavailable, or explicitly marked as partial if a later interface requirement is approved. The initial implementation should use the safer rule: a category total is available only when every scheduled group contributing to that category has a valid result.

The existing calculation `expected net = expected sales - expected expenses` remains unchanged, and expected tax remains a separate value. The migration must not introduce an accounting interpretation beyond the current system scope.

## 7. Model result and failure contract

The forecasting service should return a structured result instead of raising model errors into the view layer. Each group result must contain at least:

```text
status
model_code
model_label
order
seasonal_order
seasonal_period
history_start
history_end
observation_count
forecast_values
message
```

Planned statuses are:

| Status | Meaning | User-facing treatment |
|---|---|---|
| `forecast` | The series passed validation and produced finite, non-negative values. | Display the SARIMA result. |
| `not_scheduled` | The group has no value due in the selected calendar slot. | Display `Not scheduled`. |
| `insufficient_history` | Fewer than the required consecutive observations exist. | Explain that more regularly spaced history is required. |
| `irregular_history` | One or more expected historical periods are missing or out of sequence. | Ask the Bookkeeper to review the period records. |
| `unsupported_frequency` | The selected SARIMA configuration does not cover the frequency. | Explain that annual forecasting is not yet evaluated. |
| `invalid_series` | Values are non-finite or otherwise cannot be processed. | Mark the forecast unavailable without exposing a technical traceback. |
| `model_error` | Fitting or forecasting failed despite valid input. | Log the technical cause and show a neutral unavailable message. |
| `unreliable_result` | The model returned a negative or non-finite forecast. | Do not clamp or display it as a valid amount. |

There will be no automatic WMA or latest-value fallback. A fallback would contradict the method label and make it impossible to defend which algorithm produced the displayed value.

Money values will be converted back to `Decimal` and rounded to two decimal places only after forecasting. Input aggregation should retain the stored precision for as long as possible. Any `NaN`, infinite, or negative predicted value must be rejected rather than converted to zero.

## 8. Planned code changes

### Phase 1: Freeze and reproduce the evaluation

- Add the sanitized evaluation package described in Section 3.
- Lock the formulas and zero-denominator policy for every error metric.
- Confirm the exact Table 4 values and the selected `(0,1,0)(0,1,0)s` configuration.
- Record the package versions and random-state settings, even though the selected model is expected to be deterministic for fixed data and settings.
- Compare the evaluation aggregation key with both production candidates in Section 5 and formally lock one.
- Add a read-only data-readiness command or analysis script that reports eligibility by client, category, frequency, and selected grouping key without changing stored records.
- Review a sample of mixed monthly and quarterly clients to verify that the same calendar month may legitimately contain separate native-frequency observations.

Metric definitions to implement in the evaluation script:

```text
MAE  = mean(abs(actual - forecast))
MAPE = mean(abs((actual - forecast) / actual)) * 100
RMSE = sqrt(mean((actual - forecast)^2))
WAPE = sum(abs(actual - forecast)) / sum(abs(actual)) * 100
WAPE-based Accuracy = 100 - WAPE
```

MAPE must not divide by zero. The script must state whether zero-actual observations are excluded from MAPE or handled through another fixed rule. WAPE is undefined when the sum of absolute actual values is zero; that case must be reported as unavailable rather than forced to zero.

### Phase 2: Prepare the dependency and runtime

- Add and test `statsmodels==0.14.6` in `requirements.txt`.
- Rebuild the local virtual environment and record the resolved NumPy, SciPy, pandas, Patsy, and packaging versions.
- Run the full Django test suite under Python 3.14.4.
- Pin the deployment Python version through `.python-version` or the Render `PYTHON_VERSION` setting so local and deployment environments do not drift.
- Verify a clean Render-style Linux installation before merging the dependency change.

The current local environment is Python 3.14.4 and does not yet contain NumPy, SciPy, pandas, or statsmodels. Statsmodels 0.14.6 publishes CPython 3.14 wheels for Windows and Linux, so the current Python version is supportable, but the complete resolved dependency set still requires installation and testing.

### Phase 3: Isolate model-specific logic

Create `safebooks/services/forecasting_service.py` with focused functions such as:

```text
build_regular_series(...)
validate_sarima_eligibility(...)
fit_and_forecast_sarima(...)
map_forecast_steps_to_periods(...)
```

The service should contain the SARIMA constants, frequency configuration, data validation, fit call, controlled warning/error handling, and conversion of the model output to the structured result. Django views and templates must not import statsmodels directly.

The generic helper `_weighted_average()` in `analytics_service.py` must not be removed merely because of its name until its remaining call sites are checked. Only the confirmed WMA forecast path - `WMA_WEIGHTS`, `_weighted_moving_average_next()`, the WMA projection state, and its messages - should be retired after SARIMA passes acceptance tests.

### Phase 4: Integrate with analytics

- Preserve the current transaction classification rules; preserve or simplify group keys only according to the parity decision in Section 5.
- Replace `_build_group_forecast_model()` with preparation of a validated regular series and a SARIMA result.
- Replace recursive calls in `_project_group_value()` with lookups from the fitted group's forecast vector.
- Preserve the current monthly projection slots and frequency scheduling behavior.
- Preserve the existing public fields used by JavaScript, including `future_projections`, applicability flags, method fields, and expected values.
- Add optional metadata fields for the actual model specification and eligibility status without removing fields used by the current interface.
- Set `has_forecast` to true only when at least one complete, defensible forecast is available; do not set it merely because historical records exist.
- Ensure Bookkeeper and client data isolation remains unchanged.

### Phase 5: Update interface wording

Replace hard-coded WMA text in both analytics templates. The interface should use the method and status returned by the service so it cannot display a method different from the calculation that ran.

Recommended wording:

```text
Method: SARIMA (0,1,0)(0,1,0)[12]
Method: SARIMA (0,1,0)(0,1,0)[4]
Forecast unavailable: at least 24 consecutive monthly observations are required.
Forecast unavailable: at least 8 consecutive quarterly observations are required.
Forecast unavailable: annual SARIMA forecasting has not been evaluated.
Forecast unavailable: review missing reporting periods in the historical records.
```

Avoid claiming that the forecast is certain, predictive risk scoring, artificial intelligence, or an official accounting conclusion. It remains a statistical estimate based on the Bookkeeper's historical entries.

### Phase 6: Add tests before removing WMA

Add a dedicated `safebooks/tests/test_sarima_forecasting_service.py` and update `test_analytics_summary_api.py`.

Required test coverage:

1. a monthly fixture with 24 consecutive observations and `s = 12`;
2. a quarterly fixture with 8 consecutive observations and `s = 4`;
3. correct multi-step forecasts for the 3-, 6-, and 12-month interface horizons;
4. correct mapping of quarterly steps to scheduled calendar months;
5. separation of clients, categories, frequencies, and transaction grouping keys;
6. rejection of missing historical periods without zero imputation;
7. acceptance of an explicitly recorded zero amount as an observation;
8. insufficient-history results at 23 monthly and 7 quarterly observations;
9. annual records returning `unsupported_frequency` without affecting summaries or reports;
10. handling of negative, `NaN`, and infinite model outputs;
11. controlled handling of statsmodels warnings and fit failures;
12. no silent partial aggregate when one scheduled contributing group is ineligible;
13. preservation of sales, expense, tax, and net response fields;
14. preservation of Bookkeeper/client isolation;
15. interface and accessibility labels showing SARIMA rather than WMA; and
16. a regression fixture that reproduces the accepted evaluation results;
17. a mixed-frequency client with monthly and quarterly records in the same calendar month;
18. preservation of the client's established quarterly anchor when mapping native forecast steps to calendar months;
19. explicit distinction between an absent period and a recorded zero;
20. MAPE unavailable handling when actual values contain zero and WAPE unavailable handling when total absolute actuals are zero; and
21. evaluation-production aggregation parity for the selected group key.

Expected SARIMA values in tests must come from reviewed, fixed fixtures or independently calculated model output - not from copying whatever value the production function returns during the test.

### Phase 7: Performance and caching check

Fitting a statistical model for every request is more expensive than calculating a three-value WMA. Measure the client-specific and all-client Analytics endpoints with representative data before release.

Start with request-local reuse: fit each unique group once, request the maximum needed number of steps once, and reuse its forecast vector for all horizon rows. If this is not fast enough, add Django caching only after defining a cache key that includes:

```text
Bookkeeper/client scope + group identity + latest data signature
+ model specification + forecast horizon + package/model version
```

Any create, update, or delete operation affecting a group's historical financial records must invalidate the corresponding cached result. Do not introduce persistent serialized statsmodels objects in the first implementation; cache the final structured forecast values instead.

### Phase 8: Controlled rollout and removal

- Keep the existing WMA code temporarily behind an internal rollback setting while SARIMA is being verified.
- Ensure the interface always displays the method that actually ran.
- Run the reproducibility script, targeted forecast tests, complete Django test suite, and manual Analytics checks before switching the default.
- Verify local SQLite and configured PostgreSQL environments because database ordering and date handling must produce the same series.
- Deploy to a non-production Render service and confirm dependency installation, memory use, response time, logs, and PostgreSQL results.
- Switch the default to SARIMA only after all acceptance criteria pass.
- Remove the WMA runtime path and rollback setting after an agreed observation period. WMA may remain only in the comparison evidence and manuscript discussion.

## 9. Acceptance criteria

Implementation is complete only when all of the following are true:

- The evaluation script reproduces the accepted Table 4 result and identifies SARIMA as the selected model.
- The evaluation script and production service construct the same series at the same aggregation level.
- The data-readiness audit has been reviewed and the expected percentage of unavailable client forecasts is accepted.
- The system fits exactly SARIMA `(0,1,0)(0,1,0)s` with `s = 12` for eligible monthly series and `s = 4` for eligible quarterly series.
- Irregular, insufficient, annual, invalid, and failed series produce honest unavailable states without WMA or latest-value substitution.
- Monthly and quarterly schedules are not combined.
- Existing client filtering, forecast horizons, reports, descriptive analytics, and stored-record calculations still work.
- The API and interface identify the actual algorithm and configuration used.
- No user can obtain another Bookkeeper's client data through forecasting.
- Targeted tests and the full Django test suite pass in the pinned local and deployment runtime.
- Forecast endpoint response time and deployment memory use remain within an agreed limit measured before rollout.
- Chapter 1, Chapter 2, diagrams, labels, questionnaire statements, and the running system describe the same implemented behavior.
- The displayed 93.94% value, if retained, is explicitly identified as the documented holdout's WAPE-based evaluation value rather than a per-client guarantee.

## 10. Explicitly excluded from this migration

The following work requires a separate evaluation or approved requirement and must not be added while replacing WMA:

- automatic SARIMA order selection;
- annual forecasting through an untested model;
- machine-learning models or FastAPI services;
- external economic or BIR data;
- automatic tax calculation, filing, payment, or compliance confirmation;
- prediction intervals or risk scores in the interface;
- automatic correction or imputation of missing Bookkeeper records;
- post-forecast growth adjustments; and
- unrelated changes to dashboards, reports, authentication, database tables, or record-entry workflows.

## 11. Authoritative implementation references

- [Statsmodels SARIMAX model documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)
- [Statsmodels SARIMAX introduction and seasonal notation](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_stata.html)
- [Statsmodels SARIMAX out-of-sample forecast API](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html)
- [Statsmodels forecasting and fixed-frequency date indexes](https://www.statsmodels.org/dev/examples/notebooks/generated/statespace_forecasting.html)
- [Pandas time-series and PeriodIndex documentation](https://pandas.pydata.org/docs/user_guide/timeseries.html)
- [Statsmodels 0.14.6 package and CPython 3.14 wheels](https://pypi.org/project/statsmodels/)
- [SciPy 1.16.1 Python 3.14 wheel support](https://docs.scipy.org/doc/scipy/release/1.16.1-notes.html)
- [Hyndman and Koehler: Another look at measures of forecast accuracy](https://doi.org/10.1016/j.ijforecast.2006.03.001)
- [Hyndman and Kostenko: Minimum sample size requirements for seasonal forecasting models](https://research.monash.edu/en/publications/minimum-sample-size-requirements-for-seasonal-forecasting-models/)
- [Tashman: Out-of-sample tests of forecasting accuracy](https://doi.org/10.1016/S0169-2070(00)00065-0)
- [Render Python version configuration](https://render.com/docs/python-version)

## 12. Recommended execution order

```text
Reproduce and approve the comparison
    -> install and pin the statistical runtime
    -> build and test the regular-series validator
    -> build and test the SARIMA service
    -> connect it to the existing analytics response
    -> update interface labels and unavailable states
    -> run regression, security, and performance tests
    -> verify on a non-production deployment
    -> enable SARIMA by default
    -> observe and then remove the WMA runtime path
```

This order keeps the implementation traceable to the reported evaluation and prevents a method label from being changed before the underlying calculation is verified.
