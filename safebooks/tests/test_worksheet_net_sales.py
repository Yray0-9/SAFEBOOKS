from copy import deepcopy
from unittest import TestCase

from safebooks.services.worksheet_report_service import build_worksheet_net_sales


def line(month, category, amount, coverage="monthly", year=2026, parent="monthly", **extra):
    return {"entry_date": f"{year}-{month:02d}-01", "type_code": category, "description": category,
            "amount": str(amount), "coverage_frequency": coverage, "frequency": parent, **extra}


class WorksheetNetSalesTests(TestCase):
    def test_custom_codes_are_excluded_from_worksheet_net_sales(self):
        result = build_worksheet_net_sales([
            line(1, "Sales", "397411.00"),
            line(1, "2307", "3973.00"),
            line(1, "Custom payment", "75.00"),
            line(1, "BIR Form 2550M", "2265.00"),
        ])
        self.assertEqual(result["total"], "397411.00")

    def sample(self):
        return [line(1, "Sales", "122000"), line(2, "Sales", "128000"), line(3, "Sales", "137500"),
                line(3, "Expenses", "290500", "quarterly")]

    def test_monthly_sales_match_quarterly_expenses_once_without_mutation(self):
        rows = self.sample()
        before = deepcopy(rows)
        result = build_worksheet_net_sales(rows)
        self.assertEqual(result["periods"]["2026-03"]["amount"], "97000.00")
        self.assertEqual(result["periods"]["2026-03"]["sales_basis"], "387500.00")
        self.assertEqual(result["periods"]["2026-03"]["expenses_basis"], "290500.00")
        self.assertEqual(result["periods"]["2026-03"]["coverage_label"], "Jan–Mar 2026")
        for month in ("2026-01", "2026-02"):
            self.assertIsNone(result["periods"][month]["amount"])
            self.assertEqual(result["periods"][month]["status"], "covered")
        self.assertEqual(result["total"], "97000.00")
        self.assertEqual(rows, before)

    def test_monthly_expenses_keep_monthly_subtraction_and_real_loss(self):
        rows = self.sample()
        rows[-1]["coverage_frequency"] = "monthly"
        result = build_worksheet_net_sales(rows)
        self.assertEqual([value["amount"] for value in result["periods"].values()],
                         ["122000.00", "128000.00", "-153000.00"])
        self.assertEqual(result["total"], "97000.00")

    def test_same_quarter_native_amounts_and_explicit_override(self):
        result = build_worksheet_net_sales([line(3, "Sales", "75000", "quarterly"),
                                           line(3, "Expenses", "50000", "quarterly")])
        self.assertEqual(result["periods"]["2026-03"]["amount"], "25000.00")
        rows = self.sample()
        for row in rows:
            row["frequency"] = "quarterly"
        self.assertEqual(build_worksheet_net_sales(rows)["total"], "97000.00")

    def test_all_components_are_additive_not_inferred_to_overlap(self):
        rows = self.sample() + [line(3, "Sales", "1000", "quarterly"),
                               line(1, "Expenses", "500"), line(1, "Expenses", "500")]
        result = build_worksheet_net_sales(rows)
        self.assertEqual(result["total"], "97000.00")
        self.assertEqual(result["periods"]["2026-03"]["sales_basis"], "388500.00")
        self.assertEqual(result["periods"]["2026-03"]["expenses_basis"], "291500.00")

    def test_partial_category_coverage_withholds_result_and_total(self):
        rows = self.sample()
        del rows[1]
        rows.append(line(4, "Sales", "100"))
        result = build_worksheet_net_sales(rows)
        self.assertIsNone(result["periods"]["2026-03"]["amount"])
        self.assertEqual(result["periods"]["2026-03"]["reason"], "Incomplete Sales coverage")
        self.assertEqual(result["periods"]["2026-04"]["amount"], "100.00")
        self.assertIsNone(result["total"], "A footer must not present a partial net as the whole report total")
        rows.append(line(2, "Sales", "0"))
        self.assertEqual(build_worksheet_net_sales(rows)["total"], "-30900.00")
        result = build_worksheet_net_sales([line(3, "Sales", "75000", "quarterly"), line(3, "Expenses", "100")])
        self.assertEqual(result["periods"]["2026-03"]["reason"], "Incomplete Expenses coverage")

    def test_legacy_parent_frequency_and_off_calendar_anchors_are_preserved(self):
        rows = [line(2, "Sales", "75000", None, parent="quarterly"),
                line(2, "Expenses", "1000", None, parent="quarterly")]
        result = build_worksheet_net_sales(rows)
        self.assertEqual(result["total"], "74000.00")
        self.assertEqual(result["periods"]["2026-02"]["coverage_start"], "2025-12")
        self.assertEqual(result["periods"]["2026-02"]["coverage_label"], "Dec 2025–Feb 2026")
        rows += [line(3, "Expenses", "1000", "quarterly")]
        result = build_worksheet_net_sales(rows)
        self.assertIsNone(result["total"])
        self.assertEqual(result["periods"]["2026-03"]["reason"], "Different covered periods")

    def test_supporting_values_tax_and_remarks_do_not_change_net(self):
        rows = self.sample() + [line(1, "BIR Form 1701", "500", "annually", description="Sales Expenses"),
                               line(3, "2551Q", "6006", "quarterly", mict="9000", cogs_cos="1000000",
                                    income_payments_2307="9000", tax_withheld="99999", remarks="Paid")]
        self.assertEqual(build_worksheet_net_sales(rows)["total"], "97000.00")
        self.assertEqual(build_worksheet_net_sales(rows[-2:]), {"periods": {}, "total": None})

    def test_years_stay_separate_and_amounts_use_exact_decimal_cents(self):
        rows = self.sample() + [line(3, "Sales", "1.01", "quarterly", year=2025),
                               line(3, "Expenses", "0.99", "quarterly", year=2025)]
        self.assertEqual(build_worksheet_net_sales(rows)["total"], "97000.02")
        result = build_worksheet_net_sales([line(1, "Sales", "999999999999.99"),
                                           line(1, "Sales", "0.02"), line(1, "Expenses", "999999999999.98")])
        self.assertEqual(result["total"], "0.03")

    def test_annual_recorded_comparison_does_not_create_annual_forecasts(self):
        rows = [line(month, "Sales", "100") for month in range(1, 13)] + [line(12, "Expenses", "200", "annually")]
        result = build_worksheet_net_sales(rows)
        self.assertEqual(result["periods"]["2026-12"]["amount"], "1000.00")
        self.assertEqual(result["periods"]["2026-12"]["coverage_label"], "Jan–Dec 2026")
        self.assertEqual(result["total"], "1000.00")

    def test_blank_categories_and_confirmed_zero_keep_existing_monthly_semantics(self):
        result = build_worksheet_net_sales([line(1, "Sales", "0"), line(2, "Expenses", "25")])
        self.assertEqual(result["periods"]["2026-01"]["amount"], "0.00")
        self.assertEqual(result["periods"]["2026-02"]["amount"], "-25.00")
        self.assertEqual(result["total"], "-25.00")
