from fastapi import APIRouter, Query, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import config
from services.cycle_detector import detect_cycles
from services.config_service import (
    get_all_devices_from_logs,
    get_configs_map,
    upsert_device_name,
    upsert_channel_name,
    delete_device_config,
    get_all_pump_models,
    create_pump_model,
    update_pump_model,
    delete_pump_model,
    upsert_device_with_channels
)

router = APIRouter(prefix="/api")


def calculate_co2e_impact(volume_m3: float, dbo5_mg_l: float) -> dict:
    if volume_m3 <= 0 or dbo5_mg_l <= 0:
        return {"co2e_avoided_kg": 0, "reduction_percent": 0, "ch4_avoided_kg": 0}

    dbo5_kg_per_m3 = dbo5_mg_l / 1000
    bo_factor = 0.6
    mcf_fosse = 0.5
    mcf_fpv = 0.03
    gwp_ch4 = 28

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


@router.get("/pump-cycles")
async def get_pump_cycles(
    request: Request,
    channel: Optional[str] = Query(None, description="Filtrer par canal (ex: switch:1)"),
    device_id: Optional[str] = Query(None, description="Filtrer par device_id"),
    start_date: Optional[str] = Query(None, description="Date debut ISO (ex: 2026-02-01)"),
    end_date: Optional[str] = Query(None, description="Date fin ISO (ex: 2026-02-14)"),
    limit: int = Query(1000, ge=1, le=10000, description="Nombre max de cycles")
):
    db_pool = request.app.state.db_pool

    try:
        if not start_date:
            start_dt = datetime.now(timezone.utc) - timedelta(days=config.DEFAULT_DAYS_HISTORY)
        else:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

        if not end_date:
            end_dt = datetime.now(timezone.utc)
        else:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        query = """
            SELECT timestamp, channel, apower_w, device_id, current_a, voltage_v
            FROM power_logs
            WHERE timestamp >= $1 AND timestamp <= $2
        """
        params = [start_dt, end_dt]

        if device_id:
            query += " AND device_id = $" + str(len(params) + 1)
            params.append(device_id)

        if channel:
            query += " AND channel = $" + str(len(params) + 1)
            params.append(channel)

        query += " ORDER BY device_id, channel, timestamp ASC"

        async with db_pool.acquire() as conn:
            records = await conn.fetch(query, *params)

        print(f"📊 API: Fetched {len(records)} records for cycle detection", flush=True)

        records_list = [(r['timestamp'], r['channel'], r['apower_w'], r['device_id'], r['current_a'], r['voltage_v']) for r in records]

        cycles = detect_cycles(
            records_list,
            gap_threshold_minutes=config.GAP_THRESHOLD_MINUTES,
            min_duration_minutes=config.MIN_CYCLE_DURATION_MINUTES
        )

        print(f"🔍 API: Detected {len(cycles)} cycles", flush=True)

        cycles = cycles[:limit]

        for cycle in cycles:
            cycle['start_time'] = cycle['start_time'].strftime('%Y-%m-%dT%H:%M:%SZ')
            if cycle['end_time']:
                cycle['end_time'] = cycle['end_time'].strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                cycle['end_time'] = None

        found_device_ids = list(set(r['device_id'] for r in records))

        configs = await get_configs_map(db_pool)

        stats = {
            "max_current": 0,
            "min_current": float('inf'),
            "max_power": 0,
            "min_power": float('inf')
        }

        treated_water_m3 = 0.0

        for cycle in cycles:
            pw = cycle.get('avg_power_w')
            if pw is not None:
                stats['max_power'] = max(stats['max_power'], pw)
                stats['min_power'] = min(stats['min_power'], pw)
            ca = cycle.get('avg_current_a')
            if ca is not None:
                stats['max_current'] = max(stats['max_current'], ca)
                stats['min_current'] = min(stats['min_current'], ca)

            dev = cycle.get('device_id')
            ch = cycle.get('channel')
            ch_config = None
            if dev and ch and dev in configs and ch in configs[dev].get('channels', {}):
                ch_config = configs[dev]['channels'][ch]

            pump_type = ch_config.get('pump_type', 'relevage') if ch_config else 'relevage'
            flow_rate = ch_config.get('flow_rate') if ch_config else None
            cycle['pump_type'] = pump_type

            if pump_type == 'relevage' and flow_rate and cycle.get('duration_minutes'):
                volume = round((cycle['duration_minutes'] / 60) * flow_rate, 2)
                cycle['volume_m3'] = volume
                if not cycle.get('is_ongoing'):
                    treated_water_m3 += volume
            else:
                cycle['volume_m3'] = None

        if stats['min_current'] == float('inf'):
            stats['min_current'] = 0
        if stats['min_power'] == float('inf'):
            stats['min_power'] = 0
        stats = {k: round(v, 1) for k, v in stats.items()}

        today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_dt.date() >= today_utc.date():
            last_full_day = end_dt - timedelta(days=1)
        else:
            last_full_day = end_dt
        if last_full_day >= start_dt:
            num_days = (last_full_day - start_dt).days + 1
        else:
            num_days = 0
        treated_water_per_day = round(treated_water_m3 / num_days, 2) if num_days > 0 else 0

        dbo5_val = 570
        if device_id and device_id in configs:
            dbo5_val = configs[device_id].get('dbo5_mg_l', 570)
        elif found_device_ids:
            for did in found_device_ids:
                if did in configs:
                    dbo5_val = configs[did].get('dbo5_mg_l', 570)
                    break
        co2e_impact = calculate_co2e_impact(treated_water_m3, dbo5_val)

        return {
            "total": len(cycles),
            "device_ids": found_device_ids,
            "configs": configs,
            "stats": stats,
            "treatment_stats": {
                "treated_water_m3": round(treated_water_m3, 2),
                "treated_water_per_day": treated_water_per_day,
                "num_days": num_days
            },
            "co2e_impact": co2e_impact,
            "filters": {
                "device_id": device_id,
                "channel": channel,
                "start_date": start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "end_date": end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            },
            "cycles": cycles
        }

    except Exception as e:
        print(f"❌ Error in /api/pump-cycles: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@router.get("/config/devices")
async def get_devices_config(request: Request):
    db_pool = request.app.state.db_pool

    try:
        devices = await get_all_devices_from_logs(db_pool)
        configs = await get_configs_map(db_pool)

        for device in devices:
            did = device['device_id']
            if did in configs:
                device['device_name'] = configs[did]['device_name']
                device['channel_configs'] = configs[did]['channels']
                device['channel_names'] = {ch: info['channel_name'] for ch, info in configs[did]['channels'].items()}
                device['dbo5_mg_l'] = configs[did].get('dbo5_mg_l', 570)
                device['dco_mg_l'] = configs[did].get('dco_mg_l', 1250)
                device['mes_mg_l'] = configs[did].get('mes_mg_l', 650)
            else:
                device['device_name'] = None
                device['channel_configs'] = {}
                device['channel_names'] = {}
                device['dbo5_mg_l'] = 570
                device['dco_mg_l'] = 1250
                device['mes_mg_l'] = 650

        return {"devices": devices}
    except Exception as e:
        print(f"❌ Error in /api/config/devices: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/device")
async def update_device_name(request: Request):
    db_pool = request.app.state.db_pool

    try:
        body = await request.json()
        did = body.get("device_id")
        name = body.get("device_name", "").strip() or None

        if not did:
            raise HTTPException(400, "device_id required")

        if "channels" in body:
            channels = body["channels"]
            dbo5 = int(body.get("dbo5_mg_l", 570))
            dco = int(body.get("dco_mg_l", 1250))
            mes = int(body.get("mes_mg_l", 650))
            await upsert_device_with_channels(db_pool, did, name, channels, dbo5, dco, mes)
            print(f"✅ Device saved with channels: {did} -> {name}", flush=True)
        else:
            await upsert_device_name(db_pool, did, name)
            print(f"✅ Device name updated: {did} -> {name}", flush=True)

        return {"success": True}
    except HTTPException:
        raise
    except ValueError as e:
        print(f"❌ Validation error: {e}", flush=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error updating device name: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/channel")
async def update_channel_name(request: Request):
    db_pool = request.app.state.db_pool

    try:
        body = await request.json()
        did = body.get("device_id")
        ch = body.get("channel")
        name = body.get("channel_name", "").strip() or None

        if not did or not ch:
            raise HTTPException(400, "device_id and channel required")

        await upsert_channel_name(db_pool, did, ch, name)
        print(f"✅ Channel name updated: {did}/{ch} -> {name}", flush=True)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating channel name: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/device/{device_id}")
async def delete_device(request: Request, device_id: str):
    db_pool = request.app.state.db_pool

    try:
        await delete_device_config(db_pool, device_id)
        print(f"✅ Device config deleted: {device_id}", flush=True)
        return {"success": True}
    except Exception as e:
        print(f"❌ Error deleting device: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/pump-models")
async def get_pump_models(request: Request):
    db_pool = request.app.state.db_pool

    try:
        models = await get_all_pump_models(db_pool)
        return models
    except Exception as e:
        print(f"❌ Error fetching pump models: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/pump-model")
async def create_pump_model_route(request: Request):
    db_pool = request.app.state.db_pool

    try:
        body = await request.json()
        name = body.get("name")
        power_kw = body.get("power_kw")
        current_ampere = body.get("current_ampere")
        flow_rate_hmt8 = body.get("flow_rate_hmt8")

        if not name or power_kw is None or current_ampere is None:
            raise HTTPException(400, "name, power_kw and current_ampere required")

        new_id = await create_pump_model(db_pool, name, float(power_kw), float(current_ampere), float(flow_rate_hmt8) if flow_rate_hmt8 is not None else None)
        print(f"✅ Pump model created: {name} (id={new_id})", flush=True)
        return {"success": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating pump model: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/pump-model/{pump_id}")
async def update_pump_model_route(request: Request, pump_id: int):
    db_pool = request.app.state.db_pool

    try:
        body = await request.json()
        name = body.get("name")
        power_kw = body.get("power_kw")
        current_ampere = body.get("current_ampere")
        flow_rate_hmt8 = body.get("flow_rate_hmt8")

        if not name or power_kw is None or current_ampere is None:
            raise HTTPException(400, "name, power_kw and current_ampere required")

        await update_pump_model(db_pool, pump_id, name, float(power_kw), float(current_ampere), float(flow_rate_hmt8) if flow_rate_hmt8 is not None else None)
        print(f"✅ Pump model updated: {name} (id={pump_id})", flush=True)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating pump model: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/pump-model/{pump_id}")
async def delete_pump_model_route(request: Request, pump_id: int):
    db_pool = request.app.state.db_pool

    try:
        result = await delete_pump_model(db_pool, pump_id)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        print(f"✅ Pump model deleted: id={pump_id}", flush=True)
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting pump model: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-export-password")
async def verify_export_password(request: Request):
    body = await request.json()
    password = body.get("password", "")
    expected = os.environ.get("CSV_EXPORT_PASSWORD", "")
    if not expected or password != expected:
        raise HTTPException(status_code=403, detail="Mot de passe incorrect")
    return {"success": True}
