"""Read-only period views over already fitted, frequency-specific models.

Never fits, fills missing history, allocates quarterly money to months, or
changes recorded categories/frequencies. Net Value retains sales minus expenses.
"""
from decimal import Decimal
from safebooks.services.forecasting_service import FORECAST_READY_STATUSES, rejected_prediction_note


MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
CATEGORIES = ('sales', 'expenses', 'tax')


def _shift(period, offset):
    index = period[0] * 12 + period[1] - 1 + offset
    return index // 12, index % 12 + 1


def _money(value):
    return float(value.quantize(Decimal('0.01'))) if value is not None else None


def _native(model, period, readiness):
    if not model or period not in model['scheduled_periods']:
        return None, False, 'Not scheduled this period', 'SARIMA'
    value = model['forecast_by_period'].get(period) if model['status'] in FORECAST_READY_STATUSES else None
    note = 'SARIMA' if value is not None else (rejected_prediction_note(model, period) or readiness([model]))
    return value, True, note, 'SARIMA'


def _quarter_from_months(model, totals, end, readiness):
    values, actuals = [], 0
    for offset in (-2, -1, 0):
        period = _shift(end, offset)
        if period in totals:
            values.append(totals[period])
            actuals += 1
        elif model['status'] in FORECAST_READY_STATUSES and period in model['forecast_by_period']:
            values.append(model['forecast_by_period'][period].quantize(Decimal('0.01')))
        else:
            note = rejected_prediction_note(model, period) or readiness([model])
            return None, True, 'Complete three-month coverage required; ' + note, 'Monthly total'
    method = 'Monthly actuals + SARIMA total' if actuals else 'Three-month SARIMA total'
    return sum(values, Decimal('0.00')), True, method, method


def build_frequency_forecasts(*, models_by_category, grouped_totals, projection_slots, readiness):
    """Separate native schedules; derive quarterly comparisons only with full coverage."""
    models = {(model['client_id'], category, model['frequency']): model
              for category, items in models_by_category.items() for model in items}
    actuals = {(client, category, frequency): totals
               for (client, category, frequency, _), totals in grouped_totals.items()}
    clients = sorted({key[0] for key in models})
    frequencies = {key[2] for key in models}
    window = {(year, month) for year, month, _ in projection_slots}
    outcomes = {}

    def outcome(client, category, frequency, end):
        key = client, category, frequency, end
        if key not in outcomes:
            native = models.get((client, category, frequency))
            monthly = models.get((client, category, 'monthly'))
            if frequency == 'quarterly' and native is None and monthly is not None:
                result = _quarter_from_months(monthly, actuals[(client, category, 'monthly')], end, readiness)
            elif frequency == 'quarterly' and native is not None and end not in native['scheduled_periods']:
                result = None, True, 'Quarterly coverage does not align with this period', 'SARIMA'
            else:
                result = _native(native, end, readiness)
            outcomes[key] = result
        return outcomes[key]

    def aligned_net(frequency, end):
        basis = {'sales': Decimal('0.00'), 'expenses': Decimal('0.00')}
        for client in clients:
            for category in ('sales', 'expenses'):
                recorded = {key[2] for key in models if key[:2] == (client, category)}
                if not recorded:
                    return None, 'Matching sales and expense history required', {}
                if not recorded <= {'monthly', 'quarterly'}:
                    return None, 'Unsupported frequency in sales or expense history', {}
                if frequency == 'monthly' and recorded != {'monthly'}:
                    return None, 'Use a full quarterly comparison; amounts are not allocated to months', {}
                # Like Preview Report, include every recorded frequency component.
                # Never infer that a quarterly amount includes monthly entries,
                # discard one component, or allocate a quarterly amount to months.
                for component in sorted(recorded):
                    model = models[(client, category, component)]
                    if frequency == 'quarterly' and component == 'monthly':
                        value, applicable, note, _ = _quarter_from_months(
                            model, actuals[(client, category, component)], end, readiness)
                    else:
                        value, applicable, note, _ = outcome(client, category, component, end)
                    if value is None or not applicable:
                        return None, f'{category.capitalize()} ({component}): {note}', {}
                    basis[category] += value
        if not clients:
            return None, 'Needs historical data', {}
        basis = {category: value.quantize(Decimal('0.01')) for category, value in basis.items()}
        return (basis['sales'] - basis['expenses'],
            'Sales minus expenses for the same period; all recorded frequency components included; tax separate', basis)

    sections = []
    for frequency in ('monthly', 'quarterly'):
        if frequency not in frequencies:
            continue
        if frequency == 'monthly':
            ends = sorted(window)
        else:
            ends = sorted({period for key, model in models.items() if key[2] == 'quarterly'
                           for period in model['scheduled_periods'] if period in window})
        rows = []
        for end in ends:
            start = end if frequency == 'monthly' else _shift(end, -2)
            if frequency == 'monthly':
                label = f'{MONTHS[end[1] - 1]} {end[0]}'
            elif end[1] % 3 == 0:
                label = f'Q{end[1] // 3} {end[0]} ({MONTHS[start[1] - 1]}–{MONTHS[end[1] - 1]})'
            else:
                label = f'{MONTHS[start[1] - 1]} {start[0]}–{MONTHS[end[1] - 1]} {end[0]}'
            row = {'period_label': label, 'frequency': frequency,
                   'coverage_start': '%04d-%02d' % start, 'coverage_end': '%04d-%02d' % end}
            for category in CATEGORIES:
                parts = [outcome(client, category, frequency, end) for client in clients]
                scheduled = [part for part in parts if part[1]]
                complete = bool(scheduled) and all(part[0] is not None for part in scheduled)
                total = sum((part[0] for part in scheduled), Decimal('0.00')) if complete else None
                notes = '; '.join(dict.fromkeys(part[2] for part in scheduled)) or 'No history for this frequency'
                methods = '; '.join(dict.fromkeys(part[3] for part in scheduled)) or 'SARIMA'
                row.update({f'expected_{category}': _money(total),
                    f'expected_{category}_applicable': bool(scheduled),
                    f'{category}_unreliable': bool(scheduled) and not complete,
                    f'{category}_limited_data': False,
                    f'{category}_readiness_note': notes, f'{category}_method': methods})
            net, note, basis = aligned_net(frequency, end)
            row.update({'expected_net': _money(net), 'expected_net_applicable': net is not None,
                        'expected_net_unreliable': net is None, 'net_readiness_note': note,
                        'net_sales_basis': _money(basis.get('sales')),
                        'net_expenses_basis': _money(basis.get('expenses'))})
            rows.append(row)
        note = ('One-month predictions. Quarterly amounts are never distributed across monthly rows.' if frequency == 'monthly'
                else 'Full three-month periods. Monthly-only categories use all three months, including recorded actuals where available. Net Value requires matching coverage.')
        if not rows:
            note = 'No quarterly period ends within this horizon. Choose a longer horizon.'
        note += ' Net Value is sales minus expenses; tax is shown separately.'
        if 'annually' in frequencies:
            note += ' Annual forecasting remains unsupported.'
        sections.append({'frequency': frequency, 'frequency_label': frequency.capitalize(),
            'future_projections': rows, 'coverage_note': note,
            'has_forecast': any(row[f'expected_{category}'] is not None for row in rows for category in CATEGORIES),
            'sparkline': [row['expected_sales'] for row in rows if row['expected_sales'] is not None]})
    return sections
