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
            SELECT device_id, device_name, channel, channel_name
            FROM device_config
        """)

    configs = {}
    for row in rows:
        device_id = row['device_id']
        if device_id not in configs:
            configs[device_id] = {
                'device_name': row['device_name'],
                'channels': {}
            }
        if row['channel']:
            configs[device_id]['channels'][row['channel']] = row['channel_name']

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
