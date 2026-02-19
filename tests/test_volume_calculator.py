import pytest
from services.volume_calculator import calculate_volume_m3
from tests.fixtures import sample_pump_config


class TestVolumeCalculator:

    def test_volume_simple_case(self):
        config = sample_pump_config()
        volume = calculate_volume_m3(config["debit_m3_h"], 10)
        expected = 6.0 * (10 / 60)
        assert abs(volume - expected) < 0.01

    def test_volume_15_minutes(self):
        volume = calculate_volume_m3(6.0, 15)
        assert abs(volume - 1.5) < 0.01

    def test_volume_one_hour(self):
        volume = calculate_volume_m3(6.0, 60)
        assert abs(volume - 6.0) < 0.01

    def test_volume_different_debit(self):
        volume = calculate_volume_m3(8.0, 30)
        expected = 8.0 * 0.5
        assert abs(volume - expected) < 0.01

    def test_volume_zero_duration(self):
        volume = calculate_volume_m3(6.0, 0)
        assert volume == 0.0

    def test_volume_negative_duration_raises(self):
        with pytest.raises(ValueError):
            calculate_volume_m3(6.0, -10)

    def test_volume_precision(self):
        volume = calculate_volume_m3(5.5, 7)
        expected = 5.5 * (7 / 60)
        assert abs(volume - expected) < 0.001

    def test_volume_fractional_duration(self):
        volume = calculate_volume_m3(6.0, 14.5)
        expected = 6.0 * (14.5 / 60)
        assert abs(volume - expected) < 0.001

    def test_volume_large_duration(self):
        volume = calculate_volume_m3(6.0, 1440)
        expected = 6.0 * 24
        assert abs(volume - expected) < 0.01
