import asyncpg
from typing import Optional, List, Dict
from datetime import date, timedelta


async def get_current_config(
    pool: asyncpg.Pool,
    device_id: str,
    channel: str
) -> Optional[Dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, device_id, channel, channel_name, pump_model_id,
                   flow_rate, pump_type, dbo5, dco, mes,
                   effective_from, effective_to, version
            FROM device_config_versions
            WHERE device_id = $1 AND channel = $2 AND effective_to IS NULL
            ORDER BY version DESC
            LIMIT 1
        """, device_id, channel)
        return dict(row) if row else None


async def get_all_current_configs(pool: asyncpg.Pool) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT dcv.device_id, dcv.channel, dcv.channel_name, dcv.pump_model_id,
                   dcv.flow_rate, dcv.pump_type, dcv.dbo5, dcv.dco, dcv.mes,
                   dcv.effective_from,
                   pm.name as pm_name, pm.power_kw as pm_power_kw,
                   pm.current_ampere as pm_current_ampere, pm.flow_rate_hmt8 as pm_flow_rate_hmt8
            FROM device_config_versions dcv
            LEFT JOIN pump_models pm ON dcv.pump_model_id = pm.id
            WHERE dcv.effective_to IS NULL
            ORDER BY dcv.device_id, dcv.channel
        """)
        return [dict(row) for row in rows]


async def get_config_history(
    pool: asyncpg.Pool,
    device_id: str,
    channel: str
) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, device_id, channel, channel_name, pump_model_id,
                   flow_rate, pump_type, dbo5, dco, mes,
                   effective_from, effective_to, created_at, version
            FROM device_config_versions
            WHERE device_id = $1 AND channel = $2
            ORDER BY effective_from DESC, version DESC
        """, device_id, channel)
        return [dict(row) for row in rows]


async def add_config_version(
    pool: asyncpg.Pool,
    device_id: str,
    channel: str,
    effective_from: date,
    channel_name: Optional[str] = None,
    pump_model_id: Optional[int] = None,
    flow_rate: Optional[float] = None,
    pump_type: Optional[str] = None,
    dbo5: Optional[int] = None,
    dco: Optional[int] = None,
    mes: Optional[int] = None
):
    async with pool.acquire() as conn:
        async with conn.transaction():
            if flow_rate is not None and flow_rate <= 0:
                raise ValueError("Le debit doit etre positif")
            if pump_type is not None and pump_type not in ('relevage', 'sortie', 'autre'):
                raise ValueError("pump_type invalide")

            current = await conn.fetchrow("""
                SELECT id, channel_name, pump_model_id, flow_rate, pump_type,
                       dbo5, dco, mes, effective_from, version
                FROM device_config_versions
                WHERE device_id = $1 AND channel = $2 AND effective_to IS NULL
                ORDER BY version DESC
                LIMIT 1
            """, device_id, channel)

            final_channel_name = channel_name if channel_name is not None else (current['channel_name'] if current else None)
            final_pump_model_id = pump_model_id if pump_model_id is not None else (current['pump_model_id'] if current else None)
            final_flow_rate = flow_rate if flow_rate is not None else (current['flow_rate'] if current else None)
            final_pump_type = pump_type if pump_type is not None else (current['pump_type'] if current else 'relevage')
            final_dbo5 = dbo5 if dbo5 is not None else (current['dbo5'] if current else None)
            final_dco = dco if dco is not None else (current['dco'] if current else None)
            final_mes = mes if mes is not None else (current['mes'] if current else None)

            if current:
                if effective_from == current['effective_from']:
                    await conn.execute("""
                        DELETE FROM device_config_versions WHERE id = $1
                    """, current['id'])
                    new_version = current['version'] + 1
                elif effective_from < current['effective_from']:
                    await conn.execute("""
                        DELETE FROM device_config_versions WHERE id = $1
                    """, current['id'])
                    new_version = current['version'] + 1
                else:
                    new_version = 1
                    closing_date = effective_from - timedelta(days=1)
                    await conn.execute("""
                        UPDATE device_config_versions
                        SET effective_to = $2
                        WHERE id = $1
                    """, current['id'], closing_date)
            else:
                new_version = 1

            await conn.execute("""
                INSERT INTO device_config_versions (
                    device_id, channel, channel_name, pump_model_id,
                    flow_rate, pump_type, dbo5, dco, mes,
                    effective_from, effective_to, version
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NULL, $11)
            """,
                device_id, channel, final_channel_name, final_pump_model_id,
                final_flow_rate, final_pump_type, final_dbo5, final_dco, final_mes,
                effective_from, new_version
            )

            await conn.execute("""
                UPDATE device_config
                SET channel_name = $3, pump_model_id = $4, flow_rate = $5, pump_type = $6,
                    dbo5_mg_l = $7, dco_mg_l = $8, mes_mg_l = $9, updated_at = NOW()
                WHERE device_id = $1 AND channel = $2
            """, device_id, channel, final_channel_name, final_pump_model_id,
                final_flow_rate, final_pump_type, final_dbo5, final_dco, final_mes)

            print(f"✅ Config version added: {device_id}/{channel} v{new_version} from {effective_from}", flush=True)


async def update_current_config(
    pool: asyncpg.Pool,
    device_id: str,
    channel: str,
    channel_name: Optional[str] = None,
    pump_model_id: Optional[int] = None,
    flow_rate: Optional[float] = None,
    pump_type: Optional[str] = None,
    dbo5: Optional[int] = None,
    dco: Optional[int] = None,
    mes: Optional[int] = None
):
    async with pool.acquire() as conn:
        updates = []
        params = [device_id, channel]
        param_idx = 3

        if channel_name is not None:
            updates.append(f"channel_name = ${param_idx}")
            params.append(channel_name)
            param_idx += 1

        if pump_model_id is not None:
            updates.append(f"pump_model_id = ${param_idx}")
            params.append(pump_model_id)
            param_idx += 1

        if flow_rate is not None:
            if flow_rate <= 0:
                raise ValueError("Le debit doit etre positif")
            updates.append(f"flow_rate = ${param_idx}")
            params.append(flow_rate)
            param_idx += 1

        if pump_type is not None:
            if pump_type not in ('relevage', 'sortie', 'autre'):
                raise ValueError("pump_type invalide")
            updates.append(f"pump_type = ${param_idx}")
            params.append(pump_type)
            param_idx += 1

        if dbo5 is not None:
            updates.append(f"dbo5 = ${param_idx}")
            params.append(dbo5)
            param_idx += 1

        if dco is not None:
            updates.append(f"dco = ${param_idx}")
            params.append(dco)
            param_idx += 1

        if mes is not None:
            updates.append(f"mes = ${param_idx}")
            params.append(mes)
            param_idx += 1

        if not updates:
            return

        query = f"""
            UPDATE device_config_versions
            SET {', '.join(updates)}
            WHERE device_id = $1 AND channel = $2 AND effective_to IS NULL
        """
        await conn.execute(query, *params)

        dc_updates = []
        dc_params = [device_id, channel]
        dc_idx = 3
        if flow_rate is not None:
            dc_updates.append(f"flow_rate = ${dc_idx}")
            dc_params.append(flow_rate)
            dc_idx += 1
        if pump_type is not None:
            dc_updates.append(f"pump_type = ${dc_idx}")
            dc_params.append(pump_type)
            dc_idx += 1
        if channel_name is not None:
            dc_updates.append(f"channel_name = ${dc_idx}")
            dc_params.append(channel_name)
            dc_idx += 1
        if pump_model_id is not None:
            dc_updates.append(f"pump_model_id = ${dc_idx}")
            dc_params.append(pump_model_id)
            dc_idx += 1
        if dbo5 is not None:
            dc_updates.append(f"dbo5_mg_l = ${dc_idx}")
            dc_params.append(dbo5)
            dc_idx += 1
        if dco is not None:
            dc_updates.append(f"dco_mg_l = ${dc_idx}")
            dc_params.append(dco)
            dc_idx += 1
        if mes is not None:
            dc_updates.append(f"mes_mg_l = ${dc_idx}")
            dc_params.append(mes)
            dc_idx += 1
        if dc_updates:
            dc_updates.append("updated_at = NOW()")
            dc_query = f"UPDATE device_config SET {', '.join(dc_updates)} WHERE device_id = $1 AND channel = $2"
            await conn.execute(dc_query, *dc_params)

        print(f"✅ Current config updated: {device_id}/{channel}", flush=True)


async def bulk_load_configs_for_period(
    pool: asyncpg.Pool,
    device_id: str,
    channel: str,
    start_date: date,
    end_date: date
) -> List[Dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT device_id, channel, flow_rate, pump_type,
                   dbo5, dco, mes, effective_from, effective_to
            FROM device_config_versions
            WHERE device_id = $1
              AND channel = $2
              AND effective_from <= $4
              AND (effective_to IS NULL OR effective_to >= $3)
            ORDER BY effective_from DESC, version DESC
        """, device_id, channel, start_date, end_date)
        return [dict(row) for row in rows]


def find_config_for_date_in_memory(configs: List[Dict], target_date: date) -> Optional[Dict]:
    for cfg in configs:
        ef = cfg['effective_from']
        et = cfg['effective_to']
        if ef <= target_date and (et is None or et > target_date):
            return cfg
    return None
