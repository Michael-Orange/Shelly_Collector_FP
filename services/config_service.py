import asyncpg
from typing import Dict, List, Optional


async def get_all_devices_from_logs(pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT device_id, channel
            FROM power_logs
            ORDER BY device_id, channel
        """)

    devices = {}
    for row in rows:
        device_id = row['device_id']
        if device_id not in devices:
            devices[device_id] = []
        devices[device_id].append(row['channel'])

    return [{'device_id': k, 'channels': v} for k, v in devices.items()]


async def get_configs_map(pool: asyncpg.Pool) -> Dict:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT dc.device_id, dc.device_name, dc.channel, dc.channel_name,
                   dc.pump_model_id, dc.flow_rate, dc.pump_type,
                   dc.dbo5_mg_l, dc.dco_mg_l, dc.mes_mg_l,
                   pm.id as pm_id, pm.name as pm_name, pm.power_kw as pm_power_kw,
                   pm.current_ampere as pm_current_ampere, pm.flow_rate_hmt8 as pm_flow_rate_hmt8
            FROM device_config dc
            LEFT JOIN pump_models pm ON dc.pump_model_id = pm.id
        """)

    configs = {}
    for row in rows:
        device_id = row['device_id']
        if device_id not in configs:
            configs[device_id] = {
                'device_name': row['device_name'],
                'dbo5_mg_l': row['dbo5_mg_l'] or 570,
                'dco_mg_l': row['dco_mg_l'] or 1250,
                'mes_mg_l': row['mes_mg_l'] or 650,
                'channels': {}
            }
        if row['channel']:
            pump_model = None
            if row['pm_id'] is not None:
                pump_model = {
                    'id': row['pm_id'],
                    'name': row['pm_name'],
                    'power_kw': row['pm_power_kw'],
                    'current_ampere': row['pm_current_ampere'],
                    'flow_rate_hmt8': row['pm_flow_rate_hmt8']
                }
            configs[device_id]['channels'][row['channel']] = {
                'channel_name': row['channel_name'],
                'pump_model_id': row['pump_model_id'],
                'pump_model': pump_model,
                'flow_rate': row['flow_rate'],
                'pump_type': row['pump_type']
            }

    return configs


async def upsert_device_name(pool: asyncpg.Pool, device_id: str, device_name: Optional[str]):
    async with pool.acquire() as conn:
        channels = await conn.fetch("""
            SELECT DISTINCT channel FROM power_logs WHERE device_id = $1
        """, device_id)

        for ch in channels:
            await conn.execute("""
                INSERT INTO device_config (device_id, device_name, channel)
                VALUES ($1, $2, $3)
                ON CONFLICT (device_id, channel) 
                DO UPDATE SET device_name = $2, updated_at = NOW()
            """, device_id, device_name, ch['channel'])


async def upsert_channel_name(pool: asyncpg.Pool, device_id: str, channel: str, channel_name: Optional[str]):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO device_config (device_id, channel, channel_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (device_id, channel) 
            DO UPDATE SET channel_name = $3, updated_at = NOW()
        """, device_id, channel, channel_name)


async def delete_device_config(pool: asyncpg.Pool, device_id: str):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM device_config WHERE device_id = $1", device_id)


async def get_all_pump_models(pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, power_kw, current_ampere, flow_rate_hmt8
            FROM pump_models
            ORDER BY name
        """)
    return [dict(row) for row in rows]


async def create_pump_model(pool: asyncpg.Pool, name: str, power_kw: float, current_ampere: float, flow_rate_hmt8: Optional[float] = None) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO pump_models (name, power_kw, current_ampere, flow_rate_hmt8)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, name, power_kw, current_ampere, flow_rate_hmt8)
    return row['id']


async def update_pump_model(pool: asyncpg.Pool, pump_id: int, name: str, power_kw: float, current_ampere: float, flow_rate_hmt8: Optional[float] = None):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE pump_models
            SET name = $2, power_kw = $3, current_ampere = $4, flow_rate_hmt8 = $5
            WHERE id = $1
        """, pump_id, name, power_kw, current_ampere, flow_rate_hmt8)


async def delete_pump_model(pool: asyncpg.Pool, pump_id: int) -> dict:
    async with pool.acquire() as conn:
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM device_config WHERE pump_model_id = $1
        """, pump_id)
        if count > 0:
            return {"success": False, "error": f"Cannot delete: pump model is used by {count} channel(s)"}
        await conn.execute("DELETE FROM pump_models WHERE id = $1", pump_id)
        return {"success": True}


VALID_PUMP_TYPES = ['relevage', 'sortie', 'autre']


async def upsert_device_with_channels(pool: asyncpg.Pool, device_id: str, device_name: Optional[str], channels: List[Dict], dbo5_mg_l: int = 570, dco_mg_l: int = 1250, mes_mg_l: int = 650):
    for ch in channels:
        fr = ch.get('flow_rate')
        if fr is not None and fr != '':
            try:
                fv = float(fr)
                if fv < 0:
                    raise ValueError(f"Debit effectif doit etre positif pour {ch.get('channel', '?')}")
            except (ValueError, TypeError) as e:
                if 'positif' in str(e):
                    raise
                raise ValueError(f"Debit effectif invalide pour {ch.get('channel', '?')}: {fr}")

        pt = ch.get('pump_type', 'relevage')
        if pt not in VALID_PUMP_TYPES:
            raise ValueError(f"Type de poste invalide pour {ch.get('channel', '?')}: {pt}")

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("""
                UPDATE device_config SET device_name = $2, dbo5_mg_l = $3, dco_mg_l = $4, mes_mg_l = $5, updated_at = NOW()
                WHERE device_id = $1
            """, device_id, device_name, dbo5_mg_l, dco_mg_l, mes_mg_l)
            for ch in channels:
                fr = ch.get('flow_rate')
                flow_rate_val = float(fr) if fr is not None and fr != '' else None
                pump_type_val = ch.get('pump_type', 'relevage')
                await conn.execute("""
                    INSERT INTO device_config (device_id, device_name, channel, channel_name, pump_model_id, flow_rate, pump_type, dbo5_mg_l, dco_mg_l, mes_mg_l)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (device_id, channel)
                    DO UPDATE SET channel_name = $4, pump_model_id = $5, device_name = $2, flow_rate = $6, pump_type = $7, dbo5_mg_l = $8, dco_mg_l = $9, mes_mg_l = $10, updated_at = NOW()
                """, device_id, device_name, ch['channel'], ch.get('name'), ch.get('pump_model_id'), flow_rate_val, pump_type_val, dbo5_mg_l, dco_mg_l, mes_mg_l)
