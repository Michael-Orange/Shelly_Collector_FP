from datetime import datetime, timezone, timedelta
from typing import List, Dict


def detect_cycles(
    records: List[tuple],
    gap_threshold_minutes: int = 3,
    min_duration_minutes: int = 2
) -> List[Dict]:
    if not records:
        return []

    cycles = []
    grouped = {}

    has_device_id = len(records[0]) >= 4

    for record in records:
        timestamp = record[0]
        channel = record[1]
        apower = record[2]
        dev_id = record[3] if has_device_id else "unknown"

        key = (dev_id, channel)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((timestamp, apower))

    for (dev_id, channel), channel_records in grouped.items():
        if not channel_records:
            continue

        channel_records.sort(key=lambda x: x[0])

        cycle_start = channel_records[0][0]
        cycle_powers = [channel_records[0][1]]

        for i in range(1, len(channel_records)):
            current_time = channel_records[i][0]
            current_power = channel_records[i][1]
            previous_time = channel_records[i - 1][0]

            gap_minutes = (current_time - previous_time).total_seconds() / 60

            if gap_minutes >= gap_threshold_minutes:
                cycle_end = previous_time
                cycle_duration = (cycle_end - cycle_start).total_seconds() / 60

                if cycle_duration >= min_duration_minutes:
                    avg_power = sum(cycle_powers) / len(cycle_powers) if cycle_powers else 0

                    cycles.append({
                        "device_id": dev_id,
                        "channel": channel,
                        "start_time": cycle_start,
                        "end_time": cycle_end,
                        "duration_minutes": round(cycle_duration, 1),
                        "avg_power_w": round(avg_power, 1),
                        "records_count": len(cycle_powers),
                        "is_ongoing": False
                    })

                cycle_start = current_time
                cycle_powers = [current_power]
            else:
                cycle_powers.append(current_power)

        if cycle_powers:
            cycle_end = channel_records[-1][0]
            cycle_duration = (cycle_end - cycle_start).total_seconds() / 60

            time_since_last = (datetime.now(timezone.utc) - cycle_end).total_seconds() / 60
            is_ongoing = time_since_last < gap_threshold_minutes

            if cycle_duration >= min_duration_minutes or is_ongoing:
                avg_power = sum(cycle_powers) / len(cycle_powers) if cycle_powers else 0

                cycles.append({
                    "device_id": dev_id,
                    "channel": channel,
                    "start_time": cycle_start,
                    "end_time": cycle_end if not is_ongoing else None,
                    "duration_minutes": round(cycle_duration, 1),
                    "avg_power_w": round(avg_power, 1),
                    "records_count": len(cycle_powers),
                    "is_ongoing": is_ongoing
                })

    cycles.sort(key=lambda x: x["start_time"], reverse=True)

    return cycles
