from datetime import datetime, timezone, timedelta


def make_record(timestamp, channel, apower_w, device_id="test_device", current_a=5.0, voltage_v=230.0):
    return (timestamp, channel, apower_w, device_id, current_a, voltage_v)


def sample_power_logs_single_cycle():
    start_time = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(15):
        ts = start_time + timedelta(minutes=i)
        records.append(make_record(ts, "PR 1", 1200.0))
    return records


def sample_power_logs_two_cycles():
    start_time = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(10):
        ts = start_time + timedelta(minutes=i)
        records.append(make_record(ts, "PR 1", 1200.0))
    for i in range(10):
        ts = start_time + timedelta(minutes=15 + i)
        records.append(make_record(ts, "PR 1", 1500.0, current_a=6.5))
    return records


def sample_power_logs_short_cycle():
    start_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    records = []
    for i in range(3):
        ts = start_time + timedelta(minutes=i)
        records.append(make_record(ts, "PR 2", 800.0, current_a=3.5))
    return records


def sample_power_logs_no_power():
    start_time = datetime(2026, 2, 15, 16, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(20):
        ts = start_time + timedelta(minutes=i)
        records.append(make_record(ts, "PS", 0.0, current_a=0.0))
    return records


def sample_power_logs_multi_channel():
    start_time = datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
    records = []
    for i in range(10):
        ts = start_time + timedelta(minutes=i)
        records.append(make_record(ts, "PR 1", 1200.0))
        records.append(make_record(ts, "PR 2", 900.0, current_a=4.0))
    return records


def sample_pump_config():
    return {
        "device_id": "test_device",
        "channel": "PR 1",
        "debit_m3_h": 6.0,
        "pump_model": "Test Model",
    }


def sample_co2e_defaults():
    return {
        "bo_factor": 0.6,
        "mcf_fosse": 0.5,
        "mcf_fpv": 0.03,
        "gwp_ch4": 28,
    }
