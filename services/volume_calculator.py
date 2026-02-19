def calculate_volume_m3(debit_m3_h: float, duration_minutes: float) -> float:
    if duration_minutes < 0:
        raise ValueError("La durée ne peut pas être négative")

    if duration_minutes == 0:
        return 0.0

    duration_hours = duration_minutes / 60.0
    volume = debit_m3_h * duration_hours

    return round(volume, 3)
