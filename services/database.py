import asyncpg
from typing import Optional


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
        await conn.execute("""
            ALTER TABLE power_logs ADD COLUMN IF NOT EXISTS idempotency_key TEXT
        """)
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_power_logs_idempotency
            ON power_logs(idempotency_key)
            WHERE idempotency_key IS NOT NULL
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS device_config_versions (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(100) NOT NULL,
                channel VARCHAR(20) NOT NULL,
                channel_name VARCHAR(100),
                pump_model_id INTEGER REFERENCES pump_models(id) ON DELETE SET NULL,
                flow_rate REAL,
                pump_type VARCHAR(50),
                dbo5 INTEGER,
                dco INTEGER,
                mes INTEGER,
                effective_from DATE NOT NULL,
                effective_to DATE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                version INTEGER NOT NULL DEFAULT 1,
                CONSTRAINT flow_rate_positive CHECK (flow_rate IS NULL OR flow_rate > 0),
                CONSTRAINT valid_date_range CHECK (effective_to IS NULL OR effective_to > effective_from),
                CONSTRAINT pump_type_valid CHECK (pump_type IS NULL OR pump_type IN ('relevage', 'sortie', 'autre'))
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_config_versions_lookup
            ON device_config_versions(device_id, channel, effective_from DESC)
        """)
        try:
            await conn.execute("""
                CREATE UNIQUE INDEX idx_config_versions_active
                ON device_config_versions(device_id, channel)
                WHERE effective_to IS NULL
            """)
        except Exception:
            pass

    print("✅ Tables verified/created", flush=True)
    await _migrate_to_config_versions(pool)


async def _migrate_to_config_versions(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM device_config_versions")
        if count > 0:
            print("✅ Migration device_config_versions already done, skip", flush=True)
            return

        configs = await conn.fetch("""
            SELECT device_id, channel, channel_name, pump_model_id,
                   flow_rate, pump_type, dbo5_mg_l, dco_mg_l, mes_mg_l
            FROM device_config
        """)

        if not configs:
            print("✅ No device_config to migrate", flush=True)
            return

        print("🔄 Migrating device_config → device_config_versions", flush=True)
        migrated = 0
        for cfg in configs:
            device_id = cfg['device_id']
            channel = cfg['channel']

            first_measure = await conn.fetchval("""
                SELECT MIN(timestamp)::date
                FROM power_logs
                WHERE device_id = $1 AND channel = $2
            """, device_id, channel)

            effective_from = first_measure if first_measure else '2025-01-01'

            await conn.execute("""
                INSERT INTO device_config_versions (
                    device_id, channel, channel_name, pump_model_id,
                    flow_rate, pump_type, dbo5, dco, mes,
                    effective_from, effective_to, version
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NULL, 1)
            """,
                device_id, channel,
                cfg['channel_name'], cfg['pump_model_id'],
                cfg['flow_rate'], cfg['pump_type'] or 'relevage',
                cfg['dbo5_mg_l'], cfg['dco_mg_l'], cfg['mes_mg_l'],
                effective_from
            )
            migrated += 1
            print(f"  ✅ Migrated {device_id}/{channel} from {effective_from}", flush=True)

        print(f"✅ Migration done: {migrated} configs migrated", flush=True)


async def close_db_pool(pool: Optional[asyncpg.Pool]):
    if pool:
        try:
            await pool.close()
            print("✅ Database closed", flush=True)
        except Exception as e:
            print(f"Error closing pool: {e}", flush=True)


