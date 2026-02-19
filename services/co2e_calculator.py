def calculate_co2e_impact(volume_m3: float, dbo5_mg_l: float,
                          bo_factor: float = 0.6,
                          mcf_fosse: float = 0.5,
                          mcf_fpv: float = 0.03,
                          gwp_ch4: int = 28) -> dict:
    if volume_m3 <= 0 or dbo5_mg_l <= 0:
        return {"co2e_avoided_kg": 0, "reduction_percent": 0, "ch4_avoided_kg": 0}

    dbo5_kg_per_m3 = dbo5_mg_l / 1000
    masse_dbo5_kg = volume_m3 * dbo5_kg_per_m3
    ch4_fosse_kg = masse_dbo5_kg * bo_factor * mcf_fosse
    ch4_fpv_kg = masse_dbo5_kg * bo_factor * mcf_fpv
    ch4_avoided_kg = ch4_fosse_kg - ch4_fpv_kg
    co2e_avoided_kg = ch4_avoided_kg * gwp_ch4
    reduction_percent = (ch4_avoided_kg / ch4_fosse_kg * 100) if ch4_fosse_kg > 0 else 0

    return {
        "co2e_avoided_kg": round(co2e_avoided_kg, 2),
        "reduction_percent": round(reduction_percent, 1),
        "ch4_avoided_kg": round(ch4_avoided_kg, 2)
    }
