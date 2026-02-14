from datetime import datetime, timezone, timedelta
from typing import List, Dict
from statistics import median


def _median_voltage(voltages):
    valid = [v for v in voltages if v is not None and 180 <= v <= 260]
    if not valid:
        return None
    return round(median(valid), 1)


def detect_cycles(
    records: List[tuple],
    gap_threshold_minutes: int = 4,
    min_duration_minutes: int = 2
) -> List[Dict]:
    if not records:
        return []

    cycles = []
    grouped = {}

    has_device_id = len(records[0]) >= 4

    has_current = len(records[0]) >= 5
    has_voltage = len(records[0]) >= 6

    for record in records:
        timestamp = record[0]
        channel = record[1]
        apower = record[2]
        dev_id = record[3] if has_device_id else "unknown"
        current = record[4] if has_current else 0
        voltage = record[5] if has_voltage else 0

        key = (dev_id, channel)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((timestamp, apower, current, voltage))

    for (dev_id, channel), channel_records in grouped.items():
        if not channel_records:
            continue

        channel_records.sort(key=lambda x: x[0])

        cycle_start = channel_records[0][0]
        cycle_powers = [channel_records[0][1]]
        cycle_currents = [channel_records[0][2]]
        cycle_voltages = [channel_records[0][3]]

        for i in range(1, len(channel_records)):
            current_time = channel_records[i][0]
            current_power = channel_records[i][1]
            current_amp = channel_records[i][2]
            current_volt = channel_records[i][3]
            previous_time = channel_records[i - 1][0]

            gap_minutes = (current_time - previous_time).total_seconds() / 60

            if gap_minutes >= gap_threshold_minutes:
                cycle_end = previous_time
                cycle_duration = (cycle_end - cycle_start).total_seconds() / 60

                if cycle_duration >= min_duration_minutes:
                    avg_power = sum(cycle_powers) / len(cycle_powers) if cycle_powers else 0
                    avg_current = sum(cycle_currents) / len(cycle_currents) if cycle_currents else 0
                    med_voltage = _median_voltage(cycle_voltages)

                    cycles.append({
                        "device_id": dev_id,
                        "channel": channel,
                        "start_time": cycle_start,
                        "end_time": cycle_end,
                        "duration_minutes": round(cycle_duration, 1),
                        "avg_power_w": round(avg_power, 1),
                        "avg_current_a": round(avg_current, 2),
                        "avg_voltage_v": med_voltage,
                        "records_count": len(cycle_powers),
                        "is_ongoing": False
                    })

                cycle_start = current_time
                cycle_powers = [current_power]
                cycle_currents = [current_amp]
                cycle_voltages = [current_volt]
            else:
                cycle_powers.append(current_power)
                cycle_currents.append(current_amp)
                cycle_voltages.append(current_volt)

        if cycle_powers:
            cycle_end = channel_records[-1][0]
            cycle_duration = (cycle_end - cycle_start).total_seconds() / 60

            time_since_last = (datetime.now(timezone.utc) - cycle_end).total_seconds() / 60
            is_ongoing = time_since_last < gap_threshold_minutes

            if cycle_duration >= min_duration_minutes or is_ongoing:
                avg_power = sum(cycle_powers) / len(cycle_powers) if cycle_powers else 0
                avg_current = sum(cycle_currents) / len(cycle_currents) if cycle_currents else 0
                med_voltage = _median_voltage(cycle_voltages)

                cycles.append({
                    "device_id": dev_id,
                    "channel": channel,
                    "start_time": cycle_start,
                    "end_time": cycle_end if not is_ongoing else None,
                    "duration_minutes": round(cycle_duration, 1),
                    "avg_power_w": round(avg_power, 1),
                    "avg_current_a": round(avg_current, 2),
                    "avg_voltage_v": med_voltage,
                    "records_count": len(cycle_powers),
                    "is_ongoing": is_ongoing
                })

    cycles.sort(key=lambda x: x["start_time"], reverse=True)

    return cycles
