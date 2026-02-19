import pytest
from datetime import datetime, timezone, timedelta
from services.cycle_detector import detect_cycles
from tests.fixtures import (
    sample_power_logs_single_cycle,
    sample_power_logs_two_cycles,
    sample_power_logs_short_cycle,
    sample_power_logs_no_power,
    sample_power_logs_multi_channel,
    make_record,
)


class TestCycleDetection:

    def test_single_cycle_detected(self):
        records = sample_power_logs_single_cycle()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        assert len(cycles) == 1
        cycle = cycles[0]
        assert cycle["duration_minutes"] == 14.0
        assert cycle["channel"] == "PR 1"
        assert 1100 <= cycle["avg_power_w"] <= 1300

    def test_two_cycles_detected(self):
        records = sample_power_logs_two_cycles()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        assert len(cycles) == 2
        cycles_sorted = sorted(cycles, key=lambda c: c["start_time"])
        assert cycles_sorted[0]["duration_minutes"] == 9.0
        assert 1100 <= cycles_sorted[0]["avg_power_w"] <= 1300
        assert cycles_sorted[1]["duration_minutes"] == 9.0
        assert 1400 <= cycles_sorted[1]["avg_power_w"] <= 1600

    def test_short_cycle_detected(self):
        records = sample_power_logs_short_cycle()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        assert len(cycles) == 1
        assert cycles[0]["duration_minutes"] == 2.0
        assert cycles[0]["channel"] == "PR 2"

    def test_no_cycle_zero_power(self):
        records = sample_power_logs_no_power()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        ongoing = [c for c in cycles if not c["is_ongoing"]]
        for c in ongoing:
            assert c["avg_power_w"] == 0.0

    def test_empty_logs(self):
        cycles = detect_cycles([], gap_threshold_minutes=4, min_duration_minutes=2)
        assert len(cycles) == 0

    def test_multi_channel_separated(self):
        records = sample_power_logs_multi_channel()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        channels = {c["channel"] for c in cycles}
        assert "PR 1" in channels
        assert "PR 2" in channels

    def test_cycle_timestamps_order(self):
        records = sample_power_logs_two_cycles()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        for cycle in cycles:
            if not cycle["is_ongoing"] and cycle["end_time"] is not None:
                assert cycle["start_time"] < cycle["end_time"]

    def test_cycle_has_required_fields(self):
        records = sample_power_logs_single_cycle()
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        required_fields = [
            "device_id", "channel", "start_time", "end_time",
            "duration_minutes", "avg_power_w", "avg_current_a",
            "records_count", "is_ongoing"
        ]
        for cycle in cycles:
            for field in required_fields:
                assert field in cycle, f"Champ manquant: {field}"

    def test_gap_below_threshold_merges(self):
        start = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        records = []
        for i in range(5):
            records.append(make_record(start + timedelta(minutes=i), "PR 1", 1200.0))
        for i in range(5):
            records.append(make_record(start + timedelta(minutes=5 + 2 + i), "PR 1", 1200.0))
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=2)
        non_ongoing = [c for c in cycles if not c["is_ongoing"]]
        assert len(non_ongoing) <= 1

    def test_min_duration_filters_short(self):
        start = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
        records = [make_record(start + timedelta(minutes=i), "PR 1", 1200.0) for i in range(2)]
        records += [make_record(start + timedelta(minutes=10 + i), "PR 1", 1200.0) for i in range(10)]
        cycles = detect_cycles(records, gap_threshold_minutes=4, min_duration_minutes=3)
        non_ongoing = [c for c in cycles if not c["is_ongoing"]]
        for c in non_ongoing:
            assert c["duration_minutes"] >= 3
