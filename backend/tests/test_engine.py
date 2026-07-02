"""Engine tests against closed-form reference values.

The reference cases are computed with independent closed-form formulas
(perpetuity / growing annuity), not by re-running the engine's loop, so a bug
in the projection logic cannot cancel itself out.
"""

import pytest
from pydantic import ValidationError

from app.dcf.engine import DcfError, run_dcf
from app.models import DcfInputs


def base_inputs(**overrides) -> DcfInputs:
    defaults = dict(
        ticker="TEST",
        base_revenue=1000.0,
        base_margin=0.20,
        target_margin=0.20,
        tax_rate=0.25,
        sales_to_capital=2.0,
        growth_stage1=0.0,
        terminal_growth=0.0,
        wacc_override=0.08,
        total_debt=500.0,
        cash=200.0,
        diluted_shares=100.0,
        current_price=50.0,
    )
    defaults.update(overrides)
    return DcfInputs(**defaults)


class TestFlatPerpetuity:
    """Zero growth: FCFF is a flat 150/yr, so EV must equal 150 / 0.08 exactly."""

    def test_enterprise_value_matches_perpetuity(self):
        result = run_dcf(base_inputs())
        assert result.enterprise_value == pytest.approx(150.0 / 0.08)

    def test_yearly_rows(self):
        result = run_dcf(base_inputs())
        assert len(result.years) == 10
        for row in result.years:
            assert row.revenue == pytest.approx(1000.0)
            assert row.ebit == pytest.approx(200.0)
            assert row.nopat == pytest.approx(150.0)
            assert row.reinvestment == pytest.approx(0.0)
            assert row.fcff == pytest.approx(150.0)

    def test_equity_bridge_and_per_share(self):
        result = run_dcf(base_inputs())
        assert result.equity_value == pytest.approx(1875.0 - 500.0 + 200.0)
        assert result.intrinsic_per_share == pytest.approx(15.75)
        assert result.upside == pytest.approx(15.75 / 50.0 - 1)


class TestConstantGrowth:
    """g = 2% in both stages. FCFF_t = 143 * 1.02^(t-1) (derived by hand),
    valued as a growing annuity plus a Gordon terminal value."""

    def test_matches_closed_form(self):
        inputs = base_inputs(growth_stage1=0.02, terminal_growth=0.02)
        result = run_dcf(inputs)

        wacc, g = 0.08, 0.02
        ratio = (1 + g) / (1 + wacc)
        # Growing annuity of FCFF_1 = 143 over 10 years
        pv_explicit = (143.0 / (1 + wacc)) * (1 - ratio**10) / (1 - ratio)
        # Terminal: NOPAT_11 with reinvestment rate g/wacc
        nopat_10 = 150.0 * (1 + g) ** 10
        terminal_fcff = nopat_10 * (1 + g) * (1 - g / wacc)
        terminal_value = terminal_fcff / (wacc - g)
        pv_terminal = terminal_value / (1 + wacc) ** 10

        assert result.sum_pv_explicit == pytest.approx(pv_explicit)
        assert result.terminal_value == pytest.approx(terminal_value)
        assert result.enterprise_value == pytest.approx(pv_explicit + pv_terminal)


class TestWaccComputation:
    def test_component_build_up(self):
        inputs = base_inputs(
            wacc_override=None,
            risk_free=0.04,
            beta=1.2,
            erp=0.05,
            pretax_cost_of_debt=0.05,
            market_cap=8000.0,
            total_debt=2000.0,
        )
        result = run_dcf(inputs)
        assert result.cost_of_equity == pytest.approx(0.10)
        # 0.10 * 0.8 + 0.05 * 0.75 * 0.2
        assert result.wacc == pytest.approx(0.0875)

    def test_override_skips_components(self):
        result = run_dcf(base_inputs())
        assert result.wacc == pytest.approx(0.08)
        assert result.cost_of_equity is None

    def test_missing_components_rejected(self):
        with pytest.raises(ValidationError, match="missing"):
            base_inputs(wacc_override=None, risk_free=0.04)


class TestValidation:
    def test_terminal_growth_at_or_above_wacc(self):
        with pytest.raises(DcfError, match="must exceed terminal growth"):
            run_dcf(base_inputs(wacc_override=0.05, terminal_growth=0.06))
        with pytest.raises(DcfError, match="must exceed terminal growth"):
            run_dcf(base_inputs(wacc_override=0.05, terminal_growth=0.05))

    def test_terminal_growth_above_risk_free(self):
        with pytest.raises(ValidationError, match="risk-free"):
            base_inputs(
                wacc_override=None,
                risk_free=0.03,
                beta=1.0,
                pretax_cost_of_debt=0.05,
                market_cap=8000.0,
                terminal_growth=0.04,
            )


class TestFadePaths:
    def test_margin_fade_years_1_to_5(self):
        inputs = base_inputs(base_margin=0.10, target_margin=0.30, growth_stage1=0.0)
        result = run_dcf(inputs)
        margins = [row.margin for row in result.years]
        assert margins[:5] == pytest.approx([0.14, 0.18, 0.22, 0.26, 0.30])
        assert margins[5:] == pytest.approx([0.30] * 5)

    def test_growth_fade_years_6_to_10(self):
        inputs = base_inputs(growth_stage1=0.10, terminal_growth=0.02)
        result = run_dcf(inputs)
        growths = [row.growth for row in result.years]
        assert growths[:5] == pytest.approx([0.10] * 5)
        assert growths[5:] == pytest.approx([0.084, 0.068, 0.052, 0.036, 0.02])


class TestWarnings:
    def test_negative_fcff_flagged(self):
        inputs = base_inputs(
            growth_stage1=0.30,
            base_margin=0.10,
            target_margin=0.10,
            sales_to_capital=0.5,
            terminal_growth=0.02,
        )
        result = run_dcf(inputs)
        assert any(row.fcff < 0 for row in result.years)
        assert any("negative in some forecast years" in w for w in result.warnings)


class TestSensitivity:
    def test_grid_shape_and_center(self):
        result = run_dcf(base_inputs(terminal_growth=0.02, growth_stage1=0.05))
        grid = result.sensitivity
        assert len(grid.wacc_values) == 5
        assert len(grid.growth_values) == 5
        assert len(grid.matrix) == 5
        assert all(len(row) == 5 for row in grid.matrix)
        # Center cell = base case
        assert grid.matrix[2][2] == pytest.approx(result.intrinsic_per_share)

    def test_undefined_cells_are_none(self):
        # wacc 0.035 low corner: 0.035 - 0.015 = 0.02 vs growth up to 0.02+0.01
        result = run_dcf(base_inputs(wacc_override=0.035, terminal_growth=0.02))
        grid = result.sensitivity
        assert grid.matrix[0][3] is None  # wacc 0.02 vs g 0.025
        assert grid.matrix[0][2] is None  # wacc 0.02 vs g 0.02 (equal)
        assert grid.matrix[4][0] is not None  # wacc 0.05 vs g 0.01
