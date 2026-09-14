Hmm i have a concern that my prof said like predictive forecasting i don't think what is it really but as you can see in the image am i doing right or not? Btw the system is based on storing client transactions based from their transaction so could you really please what my prof said about he said that you add a predictive forecasting in this. That is what he said but still it is really confuses me up if i am doing right or wrong

You are actually very close to what your professor wants — the confusion is mostly about what “predictive forecasting” really means in an information system.

Right now, your dashboard already has:

historical transaction summaries ✅
trends/charts ✅
risk insight ✅

Those are good analytics features.

But your professor is probably expecting something more specific:

A system that uses past transaction data to estimate or predict future financial behavior.

That is the core idea of predictive forecasting.

What You Currently Have

From the screenshot:

Descriptive Analytics

These explain past/current data:

monthly sales
expenses
totals
charts
recorded entries

This part is already correct.

What Your Professor Probably Wants

Your current “Forecasting” card says:

“Expected Trend: Stable”

The issue is:

it looks static
it does not clearly show how the prediction was computed
there is no visible future projection

So your professor may think:

“This is just a label, not actual predictive forecasting.”

What Real Predictive Forecasting Looks Like

Since your system stores client transactions, you can forecast things like:

Example Predictions
next month expected sales
expected expenses
cash flow trend
possible tax obligations
risk of missing records
seasonal income behavior

That is already enough for a thesis/capstone-level predictive feature.

SIMPLE VERSION You Can Implement

You do NOT need AI or machine learning.

Most professors are already satisfied with:

trend-based forecasting
moving averages
linear prediction from historical data

Example:

Month	Sales
Jan	5000
Feb	5500
Mar	6000
Apr	6200

Your system predicts:

May estimated sales = ₱6500

THAT is predictive forecasting.

How To Improve Your Dashboard

Instead of only showing:

Expected Trend: Stable

Add something like:

Forecast Section
Predicted Next Month Sales: ₱8,200
Predicted Expenses: ₱4,100
Estimated Profit: ₱4,100

AND:

Future Trend Graph

Show:

previous 6 months
next predicted 1–3 months

Usually:

solid line = historical data
dotted line = predicted data

That immediately makes your analytics look predictive.

The Main Thing Your Professor Wants

Your professor probably wants:

“Use the stored transaction history to generate future estimates.”

Not just displaying data.

GOOD NEWS

Your project structure is already correct.

You are NOT wrong.

You only need to:

make the forecasting more explicit
calculate future values from past transactions
display the prediction visually







# Forecasting Analytics Explanation

The forecasting analytics feature in the system is designed to predict future financial trends using previously recorded client transaction data.

Unlike descriptive analytics, which only shows past and current financial information, forecasting analytics attempts to estimate what may happen in the future based on historical patterns.

The system analyzes stored transactions such as:
- sales
- expenses
- taxes
- profit records
- monthly financial activity

Using these records, the system generates estimated future financial outcomes. For example:
- predicted next month sales
- expected expenses
- expected profit trend
- financial stability indicators
- possible financial risks

The purpose of forecasting analytics is to help users make better financial decisions by giving insights into future financial behavior instead of only reviewing past records.

The forecasting process may use simple trend analysis techniques such as:
- moving averages
- historical trend comparison
- growth pattern analysis

Example:
If sales consistently increase over the previous months, the system may forecast continued growth in the following month. If expenses become unstable or transaction entries are frequently missing, the system may identify potential financial risk.

The forecasting feature should visually present:
- predicted values
- future trend indicators
- projected graphs or charts
- financial risk insights

This transforms the analytics dashboard from a simple reporting system into a predictive financial monitoring system.

The main goal of forecasting analytics is:
"To use historical transaction data to estimate future financial outcomes and support financial planning and decision-making."  