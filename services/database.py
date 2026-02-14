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


async def create_tables(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS device_config (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(100) NOT NULL,
                device_name VARCHAR(100),
                channel VARCHAR(20),
                channel_name VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(device_id, channel)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_config_device 
            ON device_config(device_id)
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pump_models (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                power_kw REAL NOT NULL,
                current_ampere REAL NOT NULL,
                flow_rate_hmt8 REAL NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            INSERT INTO pump_models (id, name, power_kw, current_ampere, flow_rate_hmt8)
            VALUES (1, 'Pedrollo VXM 10/35', 0.75, 4.8, 18.0)
            ON CONFLICT (id) DO NOTHING
        """)
        await conn.execute("""
            INSERT INTO pump_models (id, name, power_kw, current_ampere, flow_rate_hmt8)
            VALUES (2, 'Pedrollo DM/8', 0.55, 3.2, NULL)
            ON CONFLICT (id) DO NOTHING
        """)
        await conn.execute("""
            SELECT setval('pump_models_id_seq', GREATEST((SELECT MAX(id) FROM pump_models), 2))
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS pump_model_id INTEGER REFERENCES pump_models(id)
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS flow_rate REAL NULL
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS pump_type TEXT NOT NULL DEFAULT 'relevage'
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS dbo5_mg_l INTEGER DEFAULT 570
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS dco_mg_l INTEGER DEFAULT 1250
        """)
        await conn.execute("""
            ALTER TABLE device_config ADD COLUMN IF NOT EXISTS mes_mg_l INTEGER DEFAULT 650
        """)
    print("✅ Tables verified/created", flush=True)


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
