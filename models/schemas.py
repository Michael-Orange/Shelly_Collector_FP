from pydantic import BaseModel, Field
from datetime import datetime


class PowerLogData(BaseModel):
    device_id: str = Field(..., description="ID unique du device Shelly")
    channel: str = Field(..., description="Canal de l'appareil (ex: switch:0)")
    apower_w: float = Field(..., ge=0, description="Puissance active en Watts")
    voltage_v: float = Field(..., ge=0, description="Tension en Volts")
    current_a: float = Field(..., ge=0, description="Courant en Ampères")
    energy_total_wh: float = Field(..., ge=0, description="Énergie totale cumulée en Wh")
    timestamp: datetime = Field(..., description="Timestamp de la mesure")

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "shellypro4pm-a0dd6c9ef474",
                "channel": "switch:1",
                "apower_w": 430.5,
                "voltage_v": 230.0,
                "current_a": 1.87,
                "energy_total_wh": 15420.0,
                "timestamp": "2026-02-13T14:30:00Z"
            }
        }
