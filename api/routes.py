from fastapi import APIRouter, Query, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import config
from services.cycle_detector import detect_cycles

router = APIRouter(prefix="/api")


@router.get("/pump-cycles")
async def get_pump_cycles(
    request: Request,
    channel: Optional[str] = Query(None, description="Filtrer par canal (ex: switch:1)"),
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
            SELECT timestamp, channel, apower_w
            FROM power_logs
            WHERE timestamp >= $1 AND timestamp <= $2
            AND device_id = $3
        """
        params = [start_dt, end_dt, config.SHELLY_DEVICE_ID]

        if channel:
            query += " AND channel = $4"
            params.append(channel)

        query += " ORDER BY channel, timestamp ASC"

        async with db_pool.acquire() as conn:
            records = await conn.fetch(query, *params)

        print(f"📊 API: Fetched {len(records)} records for cycle detection", flush=True)

        records_list = [(r['timestamp'], r['channel'], r['apower_w']) for r in records]

        cycles = detect_cycles(
            records_list,
            gap_threshold_minutes=config.GAP_THRESHOLD_MINUTES,
            min_duration_minutes=config.MIN_CYCLE_DURATION_MINUTES
        )

        print(f"🔍 API: Detected {len(cycles)} cycles", flush=True)

        cycles = cycles[:limit]

        for cycle in cycles:
            cycle['start_time'] = cycle['start_time'].isoformat() + 'Z'
            if cycle['end_time']:
                cycle['end_time'] = cycle['end_time'].isoformat() + 'Z'
            else:
                cycle['end_time'] = None

        return {
            "total": len(cycles),
            "device_id": config.SHELLY_DEVICE_ID,
            "filters": {
                "channel": channel,
                "start_date": start_dt.isoformat() + 'Z',
                "end_date": end_dt.isoformat() + 'Z'
            },
            "cycles": cycles
        }

    except Exception as e:
        print(f"❌ Error in /api/pump-cycles: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
