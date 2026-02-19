import pytest
from services.co2e_calculator import calculate_co2e_impact
from tests.fixtures import sample_co2e_defaults


class TestCO2eCalculator:

    def test_co2e_base_calculation(self):
        result = calculate_co2e_impact(volume_m3=1.0, dbo5_mg_l=570)
        assert result["co2e_avoided_kg"] > 0
        assert result["ch4_avoided_kg"] > 0
        assert result["reduction_percent"] > 0
        dbo5_kg = 570 / 1000
        ch4_fosse = 1.0 * dbo5_kg * 0.6 * 0.5
        ch4_fpv = 1.0 * dbo5_kg * 0.6 * 0.03
        expected_co2e = (ch4_fosse - ch4_fpv) * 28
        assert abs(result["co2e_avoided_kg"] - round(expected_co2e, 2)) < 0.01

    def test_co2e_zero_volume(self):
        result = calculate_co2e_impact(volume_m3=0.0, dbo5_mg_l=570)
        assert result["co2e_avoided_kg"] == 0
        assert result["ch4_avoided_kg"] == 0
        assert result["reduction_percent"] == 0

    def test_co2e_negative_volume(self):
        result = calculate_co2e_impact(volume_m3=-5.0, dbo5_mg_l=570)
        assert result["co2e_avoided_kg"] == 0

    def test_co2e_zero_dbo5(self):
        result = calculate_co2e_impact(volume_m3=1.0, dbo5_mg_l=0)
        assert result["co2e_avoided_kg"] == 0

    def test_co2e_linearity(self):
        r1 = calculate_co2e_impact(1.0, 570)
        r100 = calculate_co2e_impact(100.0, 570)
        expected = r1["co2e_avoided_kg"] * 100
        assert abs(r100["co2e_avoided_kg"] - expected) < 0.1

    def test_co2e_higher_dbo5_more_impact(self):
        r_low = calculate_co2e_impact(1.0, 300)
        r_high = calculate_co2e_impact(1.0, 900)
        assert r_high["co2e_avoided_kg"] > r_low["co2e_avoided_kg"]

    def test_co2e_avoidance_positive_when_fosse_gt_fpv(self):
        result = calculate_co2e_impact(
            volume_m3=1.0, dbo5_mg_l=570,
            mcf_fosse=0.5, mcf_fpv=0.03
        )
        assert result["co2e_avoided_kg"] > 0
        assert result["reduction_percent"] == 94.0

    def test_co2e_different_gwp(self):
        r_ar5 = calculate_co2e_impact(1.0, 570, gwp_ch4=28)
        r_ar6 = calculate_co2e_impact(1.0, 570, gwp_ch4=29.8)
        ratio = r_ar6["co2e_avoided_kg"] / r_ar5["co2e_avoided_kg"]
        assert 1.06 < ratio < 1.07

    def test_co2e_mcf_fosse_dominates(self):
        r_fosse_only = calculate_co2e_impact(1.0, 570, mcf_fosse=0.5, mcf_fpv=0.0)
        r_fpv_only = calculate_co2e_impact(1.0, 570, mcf_fosse=0.0, mcf_fpv=0.03)
        assert r_fosse_only["co2e_avoided_kg"] > 0
        assert r_fpv_only["co2e_avoided_kg"] < 0

    def test_co2e_reduction_percent_formula(self):
        result = calculate_co2e_impact(1.0, 570)
        expected_pct = ((0.5 - 0.03) / 0.5) * 100
        assert abs(result["reduction_percent"] - expected_pct) < 0.1

    def test_co2e_custom_coefficients(self):
        defaults = sample_co2e_defaults()
        result = calculate_co2e_impact(
            volume_m3=10.0, dbo5_mg_l=1000,
            **defaults
        )
        dbo5_kg = 1000 / 1000
        ch4_fosse = 10.0 * dbo5_kg * 0.6 * 0.5
        ch4_fpv = 10.0 * dbo5_kg * 0.6 * 0.03
        expected = (ch4_fosse - ch4_fpv) * 28
        assert abs(result["co2e_avoided_kg"] - round(expected, 2)) < 0.01
