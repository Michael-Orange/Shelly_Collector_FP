import asyncpg
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


async def create_db_pool(database_url: str, min_size: int, max_size: int):
    try:
        pool = await asyncpg.create_pool(
            database_url,
            min_size=min_size,
            max_size=max_size
        )
        return pool
    except Exception as e:
        print(f"DB pool creation failed: {e}", flush=True)
        raise


async def close_db_pool(pool: Optional[asyncpg.Pool]):
    if pool:
        try:
            await pool.close()
            print("✅ Database closed", flush=True)
        except Exception as e:
            print(f"Error closing pool: {e}", flush=True)


def should_write(
    last_write_time: Dict[str, datetime],
    device_id: str,
    channel: int,
    now: datetime
) -> bool:
    state_key = f"{device_id}_ch{channel}"

    if state_key not in last_write_time or (now - last_write_time[state_key]) >= timedelta(minutes=1):
        last_write_time[state_key] = now
        return True

    return False


async def insert_power_log(
    pool: Optional[asyncpg.Pool],
    device_id: str,
    channel: int,
    apower: float,
    voltage: float,
    current: float,
    energy_total: float
) -> bool:
    if not pool:
        return False

    try:
        timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO power_logs (timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', timestamp, device_id, f"switch:{channel}", apower, voltage, current, energy_total)

        print(f"DB: {device_id} ch:{channel} {apower}W @ {timestamp.strftime('%H:%M')} (sample)", flush=True)
        return True
    except Exception as e:
        print(f"DB error: {e}", flush=True)
        return False
