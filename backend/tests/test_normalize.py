"""Tests for XBRL normalization against synthetic companyfacts structures
that replicate the real data.sec.gov JSON shape, including tag switches,
restated comparatives, and missing concepts.
"""

import pytest

from app.services.normalize import normalize


def duration_fact(end: str, val: float, filed: str = "2024-01-01", form: str = "10-K"):
    start = f"{int(end[:4]) - 1}{end[4:]}"
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "fp": "FY"}


def quarter_fact(end: str, val: float):
    start_year = end[:4]
    return {
        "start": f"{start_year}-07-01",
        "end": end,
        "val": val,
        "form": "10-K",
        "filed": "2024-01-01",
    }


def instant_fact(end: str, val: float, filed: str = "2024-01-01", form: str = "10-K"):
    return {"end": end, "val": val, "form": form, "filed": filed}


def usd(entries):
    return {"units": {"USD": entries}}


def shares(entries):
    return {"units": {"shares": entries}}


def build_facts(gaap: dict, entity_name: str = "Test Corp") -> dict:
    return {"entityName": entity_name, "facts": {"us-gaap": gaap}}


SUBMISSIONS = {"name": "Test Corp", "sic": "3571", "sicDescription": "Electronic Computers"}
BANK_SUBMISSIONS = {"name": "Test Bank", "sic": "6022", "sicDescription": "State Commercial Banks"}


def clean_facts() -> dict:
    """Three fiscal years, modern + legacy revenue tags, full concept coverage."""
    return build_facts(
        {
            # 2021 reported under the legacy tag only; 2022-2023 under the modern tag
            "Revenues": usd([duration_fact("2021-12-31", 800.0)]),
            "RevenueFromContractWithCustomerExcludingAssessedTax": usd(
                [
                    duration_fact("2022-12-31", 900.0),
                    duration_fact("2023-12-31", 1000.0),
                    # Restated 2022 figure filed later must win over the original
                    duration_fact("2022-12-31", 910.0, filed="2024-06-01"),
                    # Quarterly duration inside a 10-K must be ignored
                    quarter_fact("2023-12-31", 250.0),
                ]
            ),
            "OperatingIncomeLoss": usd(
                [
                    duration_fact("2021-12-31", 160.0),
                    duration_fact("2022-12-31", 180.0),
                    duration_fact("2023-12-31", 200.0),
                ]
            ),
            "DepreciationDepletionAndAmortization": usd(
                [
                    duration_fact("2022-12-31", 40.0),
                    duration_fact("2023-12-31", 45.0),
                ]
            ),
            "PaymentsToAcquirePropertyPlantAndEquipment": usd(
                [
                    duration_fact("2022-12-31", 60.0),
                    duration_fact("2023-12-31", 70.0),
                ]
            ),
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": usd(
                [duration_fact("2023-12-31", 190.0)]
            ),
            "IncomeTaxExpenseBenefit": usd([duration_fact("2023-12-31", 38.0)]),
            "LongTermDebtNoncurrent": usd(
                [instant_fact("2022-12-31", 300.0), instant_fact("2023-12-31", 280.0)]
            ),
            "LongTermDebtCurrent": usd([instant_fact("2023-12-31", 20.0)]),
            "CashAndCashEquivalentsAtCarryingValue": usd(
                [instant_fact("2022-12-31", 150.0), instant_fact("2023-12-31", 170.0)]
            ),
            "AssetsCurrent": usd(
                [instant_fact("2021-12-31", 380.0), instant_fact("2022-12-31", 400.0), instant_fact("2023-12-31", 430.0)]
            ),
            "LiabilitiesCurrent": usd(
                [instant_fact("2021-12-31", 210.0), instant_fact("2022-12-31", 220.0), instant_fact("2023-12-31", 230.0)]
            ),
            "WeightedAverageNumberOfDilutedSharesOutstanding": shares(
                [duration_fact("2023-12-31", 100.0)]
            ),
        }
    )


class TestCleanFiler:
    @pytest.fixture()
    def payload(self):
        return normalize("TEST", "0000000001", clean_facts(), SUBMISSIONS)

    def test_revenue_merged_across_tag_switch(self, payload):
        by_year = {y.fiscal_year: y for y in payload.years}
        assert by_year[2021].revenue == 800.0
        assert by_year[2023].revenue == 1000.0

    def test_restated_value_wins(self, payload):
        by_year = {y.fiscal_year: y for y in payload.years}
        assert by_year[2022].revenue == 910.0

    def test_debt_sums_components(self, payload):
        by_year = {y.fiscal_year: y for y in payload.years}
        assert by_year[2023].total_debt == 300.0  # 280 noncurrent + 20 current
        assert by_year[2022].total_debt == 300.0  # no current portion reported

    def test_working_capital(self, payload):
        by_year = {y.fiscal_year: y for y in payload.years}
        assert by_year[2023].working_capital == 200.0

    def test_derived_metrics(self, payload):
        d = payload.derived
        assert d.latest_revenue == 1000.0
        assert d.latest_operating_margin == pytest.approx(0.20)
        assert d.revenue_cagr_1y == pytest.approx(1000.0 / 910.0 - 1)
        assert d.effective_tax_rate == pytest.approx(38.0 / 190.0)
        assert d.latest_diluted_shares == 100.0
        # 2021->2022: delta_rev = 110, reinvest = 60 - 40 + (180 - 170) = 30
        # 2022->2023: delta_rev = 90,  reinvest = 70 - 45 + (200 - 180) = 45
        assert d.sales_to_capital_5y == pytest.approx(200.0 / 75.0)

    def test_not_financial(self, payload):
        assert payload.is_financial is False


def messy_facts() -> dict:
    """Legacy filer: SalesRevenueNet only, LongTermDebt total only, no capex/D&A."""
    return build_facts(
        {
            "SalesRevenueNet": usd(
                [duration_fact("2022-12-31", 500.0), duration_fact("2023-12-31", 550.0)]
            ),
            "LongTermDebt": usd([instant_fact("2023-12-31", 120.0)]),
        },
        entity_name="Messy Inc.",
    )


class TestMessyFiler:
    @pytest.fixture()
    def payload(self):
        return normalize("MSY", "0000000002", messy_facts(), SUBMISSIONS)

    def test_fallback_revenue_tag(self, payload):
        assert [y.revenue for y in payload.years] == [500.0, 550.0]

    def test_fallback_total_debt(self, payload):
        assert payload.years[-1].total_debt == 120.0

    def test_gaps_are_none_and_warned(self, payload):
        latest = payload.years[-1]
        assert latest.operating_income is None
        assert latest.cash is None
        assert any("Missing from latest filing" in w for w in payload.warnings)

    def test_underivable_metrics_are_none(self, payload):
        assert payload.derived.latest_operating_margin is None
        assert payload.derived.sales_to_capital_5y is None
        assert payload.derived.revenue_cagr_1y == pytest.approx(0.10)


class TestFinancialSector:
    def test_bank_flagged(self):
        payload = normalize("BNK", "0000000003", messy_facts(), BANK_SUBMISSIONS)
        assert payload.is_financial is True
        assert any("financial-sector" in w for w in payload.warnings)


class TestEmptyFacts:
    def test_no_data_at_all(self):
        payload = normalize("NIL", "0000000004", build_facts({}), SUBMISSIONS)
        assert payload.years == []
        assert any("No annual revenue" in w for w in payload.warnings)
