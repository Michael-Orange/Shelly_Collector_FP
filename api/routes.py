from fastapi import APIRouter, Query, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta, date as date_type
from typing import Optional, List
from pydantic import BaseModel, validator
import os
import time
import hashlib
import hmac
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
from services.config_versions_service import (
    get_all_current_configs,
    get_config_history,
    add_config_version,
    update_current_config,
    bulk_load_configs_for_period,
    find_config_for_date_in_memory
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

        configs_cache = {}
        unique_pairs = set()
        for cycle in cycles:
            dev = cycle.get('device_id')
            ch = cycle.get('channel')
            if dev and ch:
                unique_pairs.add((dev, ch))
        for dev, ch in unique_pairs:
            period_configs = await bulk_load_configs_for_period(
                db_pool, dev, ch, start_dt.date(), end_dt.date()
            )
            configs_cache[(dev, ch)] = period_configs

        stats = {
            "max_current": 0,
            "min_current": float('inf'),
            "max_power": 0,
            "min_power": float('inf')
        }

        treated_water_m3 = 0.0
        co2e_dbo5_weighted = []

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

            cycle_start = cycle.get('start_time')
            if isinstance(cycle_start, str):
                cycle_date = datetime.fromisoformat(cycle_start.replace('Z', '+00:00')).date()
            else:
                cycle_date = cycle_start.date() if cycle_start else start_dt.date()

            versioned_config = find_config_for_date_in_memory(
                configs_cache.get((dev, ch), []), cycle_date
            )

            pump_type = versioned_config['pump_type'] if versioned_config and versioned_config.get('pump_type') else 'relevage'
            flow_rate = versioned_config['flow_rate'] if versioned_config else None
            cycle['pump_type'] = pump_type

            if pump_type == 'relevage' and flow_rate and cycle.get('duration_minutes'):
                volume = round((cycle['duration_minutes'] / 60) * flow_rate, 2)
                cycle['volume_m3'] = volume
                if not cycle.get('is_ongoing'):
                    treated_water_m3 += volume
                    dbo5_for_cycle = versioned_config.get('dbo5', 570) if versioned_config else 570
                    co2e_dbo5_weighted.append((volume, dbo5_for_cycle or 570))
            else:
                cycle['volume_m3'] = None

        if stats['min_current'] == float('inf'):
            stats['min_current'] = 0
        if stats['min_power'] == float('inf'):
            stats['min_power'] = 0
        stats = {k: round(v, 1) for k, v in stats.items()}

        num_days = (end_dt - start_dt).days + 1
        treated_water_per_day = round(treated_water_m3 / num_days, 2) if num_days > 0 else 0

        if co2e_dbo5_weighted and treated_water_m3 > 0:
            total_co2e_avoided = 0.0
            total_ch4_avoided = 0.0
            for vol, dbo5_val in co2e_dbo5_weighted:
                impact = calculate_co2e_impact(vol, dbo5_val)
                total_co2e_avoided += impact['co2e_avoided_kg']
                total_ch4_avoided += impact['ch4_avoided_kg']
            co2e_impact = {
                "co2e_avoided_kg": round(total_co2e_avoided, 2),
                "reduction_percent": round(94.0, 1),
                "ch4_avoided_kg": round(total_ch4_avoided, 2)
            }
        else:
            co2e_impact = calculate_co2e_impact(0, 570)

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


def _make_admin_token():
    secret = os.environ.get("SESSION_SECRET", "fallback-secret")
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}:{sig}"

def _verify_admin_token(token: str) -> bool:
    if not token:
        return False
    secret = os.environ.get("SESSION_SECRET", "fallback-secret")
    parts = token.split(":", 1)
    if len(parts) != 2:
        return False
    ts, sig = parts
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if time.time() - ts_int > 86400:
        return False
    expected_sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)

@router.post("/verify-export-password")
async def verify_export_password(request: Request):
    body = await request.json()
    password = body.get("password", "")
    expected = os.environ.get("CSV_EXPORT_PASSWORD", "")
    if not expected or password != expected:
        raise HTTPException(status_code=403, detail="Mot de passe incorrect")
    response = JSONResponse(content={"success": True})
    token = _make_admin_token()
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
        path="/"
    )
    return response

@router.get("/admin/check-session")
async def check_admin_session(request: Request):
    token = request.cookies.get("admin_session", "")
    if _verify_admin_token(token):
        return {"authenticated": True}
    raise HTTPException(status_code=401, detail="Non authentifié")


class ShellyMessage(BaseModel):
    src: str
    timestamp: int
    params: dict

    @validator('src')
    def validate_src(cls, v):
        if not v or not v.strip():
            raise ValueError('Device ID cannot be empty')
        return v.strip()

    @validator('timestamp')
    def validate_timestamp(cls, v):
        if v <= 0 or v > time.time() + 86400:
            raise ValueError('Invalid timestamp')
        return v


class BatchIngest(BaseModel):
    messages: List[ShellyMessage]

    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('Batch cannot be empty')
        if len(v) > 1000:
            raise ValueError('Batch too large (max 1000)')
        return v


@router.post("/ingest/batch")
async def ingest_batch(
    batch: BatchIngest,
    request: Request,
    x_api_key: str = Header(...)
):
    expected_token = os.environ.get("INGEST_API_KEY")
    if not expected_token:
        print("\u274c INGEST_API_KEY not configured in environment", flush=True)
        raise HTTPException(status_code=500, detail="Server configuration error")

    if x_api_key != expected_token:
        print(f"\u26a0\ufe0f Unauthorized batch ingest attempt", flush=True)
        raise HTTPException(status_code=401, detail="Unauthorized")

    start_time = time.time()
    inserted = 0
    duplicates = 0
    errors = 0
    devices = set()

    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        for msg in batch.messages:
            device_id = msg.src
            devices.add(device_id)
            ts = datetime.fromtimestamp(msg.timestamp, tz=timezone.utc)
            minute_epoch = msg.timestamp // 60

            for ch_num in [0, 1, 2, 3]:
                switch_data = msg.params.get(f"switch:{ch_num}")

                if not switch_data or not isinstance(switch_data, dict):
                    continue

                apower = switch_data.get("apower")
                if apower is None:
                    continue

                voltage = switch_data.get("voltage", 0)
                current = switch_data.get("current", 0)
                energy_total = 0
                aenergy = switch_data.get("aenergy")
                if aenergy and isinstance(aenergy, dict):
                    energy_total = aenergy.get("total", 0)

                channel = f"switch:{ch_num}"
                idempotency_key = f"{device_id}_{ch_num}_{minute_epoch}"

                try:
                    row_id = await conn.fetchval("""
                        INSERT INTO power_logs
                        (timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh, idempotency_key)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL
                        DO NOTHING
                        RETURNING id
                    """, ts, device_id, channel, apower, voltage, current, energy_total, idempotency_key)

                    if row_id is None:
                        duplicates += 1
                    else:
                        inserted += 1

                except Exception as e:
                    print(f"\u274c Insert failed for {idempotency_key}: {e}", flush=True)
                    errors += 1

    processing_time = time.time() - start_time
    print(f"\U0001f4e5 Batch: {inserted} new, {duplicates} dup, {errors} err, "
          f"{len(batch.messages)} msgs, {len(devices)} devices, {processing_time:.2f}s", flush=True)

    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors,
        "total_messages": len(batch.messages),
        "devices": len(devices),
        "processing_time": round(processing_time, 2)
    }


@router.get("/config/current")
async def get_all_current_configs_route(request: Request):
    db_pool = request.app.state.db_pool
    try:
        configs = await get_all_current_configs(db_pool)
        for c in configs:
            if c.get('effective_from'):
                c['effective_from'] = c['effective_from'].isoformat()
        return {"configs": configs}
    except Exception as e:
        print(f"❌ Error fetching current configs: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/current")
async def update_current_config_route(request: Request):
    db_pool = request.app.state.db_pool
    try:
        body = await request.json()
        device_id = body.get("device_id")
        channel = body.get("channel")
        if not device_id or not channel:
            raise HTTPException(400, "device_id et channel requis")

        flow_rate_val = body.get("flow_rate")
        if flow_rate_val is not None:
            flow_rate_val = float(flow_rate_val)
        pump_model_val = body.get("pump_model_id")
        if pump_model_val is not None:
            pump_model_val = int(pump_model_val)
        dbo5_val = body.get("dbo5")
        if dbo5_val is not None:
            dbo5_val = int(dbo5_val)
        dco_val = body.get("dco")
        if dco_val is not None:
            dco_val = int(dco_val)
        mes_val = body.get("mes")
        if mes_val is not None:
            mes_val = int(mes_val)

        await update_current_config(
            db_pool, device_id, channel,
            channel_name=body.get("channel_name"),
            pump_model_id=pump_model_val,
            flow_rate=flow_rate_val,
            pump_type=body.get("pump_type"),
            dbo5=dbo5_val,
            dco=dco_val,
            mes=mes_val
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating current config: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/history")
async def get_config_history_route(
    request: Request,
    device_id: str = Query(...),
    channel: str = Query(...)
):
    db_pool = request.app.state.db_pool
    try:
        history = await get_config_history(db_pool, device_id, channel)
        for h in history:
            if h.get('effective_from'):
                h['effective_from'] = h['effective_from'].isoformat()
            if h.get('effective_to'):
                h['effective_to'] = h['effective_to'].isoformat()
            if h.get('created_at'):
                h['created_at'] = h['created_at'].isoformat()
        return {"history": history}
    except Exception as e:
        print(f"❌ Error fetching config history: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/version")
async def add_config_version_route(request: Request):
    db_pool = request.app.state.db_pool
    try:
        body = await request.json()
        device_id = body.get("device_id")
        channel = body.get("channel")
        effective_from_str = body.get("effective_from")
        if not all([device_id, channel, effective_from_str]):
            raise HTTPException(400, "device_id, channel et effective_from requis")

        effective_from = datetime.strptime(effective_from_str, '%Y-%m-%d').date()

        flow_rate_val = body.get("flow_rate")
        if flow_rate_val is not None:
            flow_rate_val = float(flow_rate_val)
        pump_model_val = body.get("pump_model_id")
        if pump_model_val is not None:
            pump_model_val = int(pump_model_val)
        dbo5_val = body.get("dbo5")
        if dbo5_val is not None:
            dbo5_val = int(dbo5_val)
        dco_val = body.get("dco")
        if dco_val is not None:
            dco_val = int(dco_val)
        mes_val = body.get("mes")
        if mes_val is not None:
            mes_val = int(mes_val)

        await add_config_version(
            db_pool, device_id, channel, effective_from,
            channel_name=body.get("channel_name"),
            pump_model_id=pump_model_val,
            flow_rate=flow_rate_val,
            pump_type=body.get("pump_type"),
            dbo5=dbo5_val,
            dco=dco_val,
            mes=mes_val
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error adding config version: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/power-chart-data")
async def get_power_chart_data(
    request: Request,
    device_id: str = Query(...),
    channel: str = Query(None),
    period: str = Query("24h"),
    end_date: str = Query(None)
):
    db_pool = request.app.state.db_pool

    try:
        print(f"🔍 DEBUG Chart - end_date param: {end_date!r}, period: {period}", flush=True)

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Format end_date invalide. Attendu: YYYY-MM-DD")
        else:
            end_dt = datetime.now(timezone.utc)

        if period == "7d":
            start_time = end_dt - timedelta(days=7)
        elif period == "30d":
            start_time = end_dt - timedelta(days=30)
        else:
            start_time = end_dt - timedelta(hours=24)
            period = "24h"

        print(f"🔍 DEBUG Chart - end_dt: {end_dt.isoformat()}, start_time: {start_time.isoformat()}", flush=True)

        if channel and channel != "all":
            params = [device_id, start_time, end_dt, channel]
            channel_filter_sql = "AND channel = $4"
        else:
            params = [device_id, start_time, end_dt]
            channel_filter_sql = ""

        if period == "24h":
            time_bucket_expr = "date_trunc('hour', timestamp) + INTERVAL '5 minutes' * FLOOR(EXTRACT(MINUTE FROM timestamp) / 5)"
        elif period == "7d":
            time_bucket_expr = "date_trunc('hour', timestamp)"
        else:
            time_bucket_expr = "date_trunc('day', timestamp) + INTERVAL '6 hours' * FLOOR(EXTRACT(HOUR FROM timestamp) / 6)"

        query = f"""
            SELECT
                {time_bucket_expr} as time_bucket,
                channel,
                AVG(apower_w) as avg_power_w,
                AVG(current_a) as avg_current_a
            FROM power_logs
            WHERE device_id = $1
              AND timestamp >= $2
              AND timestamp <= $3
              {channel_filter_sql}
            GROUP BY time_bucket, channel
            ORDER BY time_bucket ASC
        """

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        data_by_channel = {}
        for row in rows:
            ch = row['channel']
            if ch not in data_by_channel:
                data_by_channel[ch] = {
                    'timestamps': [],
                    'power_w': [],
                    'current_a': []
                }

            data_by_channel[ch]['timestamps'].append(row['time_bucket'].isoformat())
            data_by_channel[ch]['power_w'].append(round(float(row['avg_power_w']), 2) if row['avg_power_w'] else 0)
            data_by_channel[ch]['current_a'].append(round(float(row['avg_current_a']), 3) if row['avg_current_a'] else 0)

        if period == "7d":
            bucket_delta = timedelta(hours=1)
        elif period == "30d":
            bucket_delta = timedelta(hours=6)
        else:
            bucket_delta = timedelta(minutes=5)

        for ch, cdata in data_by_channel.items():
            if cdata['timestamps']:
                last_time = datetime.fromisoformat(cdata['timestamps'][-1])
                zero_time = last_time + bucket_delta
                cdata['timestamps'].append(zero_time.isoformat())
                cdata['power_w'].append(0)
                cdata['current_a'].append(0)

        start_date_str = start_time.strftime("%Y-%m-%d")
        end_date_str = end_dt.strftime("%Y-%m-%d")

        return {
            "device_id": device_id,
            "period": period,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "start_time_iso": start_time.isoformat(),
            "end_time_iso": end_dt.isoformat(),
            "data": data_by_channel
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching chart data: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/queue")
async def queue_stats(request: Request):
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE idempotency_key IS NOT NULL) as from_queue,
                MAX(timestamp) as last_insert,
                COUNT(DISTINCT device_id) as devices
            FROM power_logs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)

    return {
        "period": "24h",
        "total_logs": result['total'],
        "from_queue": result['from_queue'],
        "devices": result['devices'],
        "last_insert": result['last_insert'].strftime('%Y-%m-%dT%H:%M:%SZ') if result['last_insert'] else None
    }
