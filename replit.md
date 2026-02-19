# Overview

This project is a **Shelly device data collector and monitoring dashboard** that receives power consumption data from Shelly Pro 4PM devices via Cloudflare Queue → HTTP batch POST, and logs it to a PostgreSQL database with minute-level deduplication. It includes a web dashboard to visualize pump operation cycles with filtering and CSV export.

# Recent Changes

**2026-02-19 (Latest)**: Power consumption chart with historical date selector :
- **New**: `GET /api/power-chart-data` — temporal aggregation endpoint (1min/10min/1h based on period)
- **New**: Param\u00e8tre `end_date` optionnel (YYYY-MM-DD) pour analyse historique
- **New**: Chart.js line chart on dashboard with dual Y-axis (Watts left, Amperes right)
- **New**: 3 period buttons (24h, 7 jours, 30 jours) with automatic aggregation
- **New**: Date picker "Jusqu'au" avec bouton reset pour exploration historique
- **New**: Titre dynamique avec plage de dates (ex: 05/02/2026 — 12/02/2026)
- **New**: PNG export button for chart
- **New**: Chart syncs with device/channel filters
- **Feature**: Channels shown with distinct colors, filled area for power, dashed line for current
- **Validation**: Dates futures bloqu\u00e9es (frontend max + backend validation)

**2026-02-19**: Configuration versioning — SCD Type 2 :
- **New**: Table `device_config_versions` with `effective_from`/`effective_to` for temporal config tracking
- **New**: Service `services/config_versions_service.py` with full version management
- **New**: API `POST /api/config/version` — create new config version with effective date
- **New**: API `GET /api/config/current` — list all active configs from versions table
- **New**: API `PUT /api/config/current` — update current config in place (no versioning)
- **New**: API `GET /api/config/history` — list all config versions for a device/channel
- **New**: `bulk_load_configs_for_period()` + `find_config_for_date_in_memory()` for batch optimization
- **Modified**: `/api/pump-cycles` uses versioned configs per cycle (flow_rate + DBO5/DCO/MES historical)
- **Modified**: CO2e calculation uses per-cycle DBO5 from versioned config
- **Modified**: Admin interface — "Historique des versions" collapsible panel per channel
- **Modified**: New version form pre-filled with current values, targeted refresh (no page reload)
- **Migration**: Existing `device_config` data auto-migrated to `device_config_versions` on startup
- **Feature**: Fusion logic — changing one field copies others from previous version

**2026-02-15**: Architecture migration — WebSocket → HTTP batch ingestion :
- **BREAKING**: Removed WebSocket endpoint `/ws` entirely (no more WS connection)
- **New**: `POST /api/ingest/batch` — Secure HTTP batch endpoint for Cloudflare Queue consumer
- **New**: `GET /api/stats/queue` — Stats endpoint for monitoring (last 24h insertions)
- **New**: `idempotency_key` TEXT column on `power_logs` with partial unique index (deduplication)
- **New**: Pydantic models `ShellyMessage` + `BatchIngest` with validation (max 1000 msgs/batch)
- **Security**: `INGEST_API_KEY` header required (`X-Api-Key`), 401 if missing/wrong, 500 if not configured
- **Removed**: `should_write()` and `insert_power_log()` from database.py (replaced by batch logic)
- **Removed**: `THROTTLE_INTERVAL_SECONDS` from config.py (dedup handled by idempotency_key)
- **Modified**: `main.py` — simplified, no more WebSocket imports, startup message updated

**2026-02-15**: Dashboard fixes :
- **Fix**: CSV export password prompt — apostrophe causing JS syntax error (all JS broken)
- **Fix**: Date picker initialization — `valueAsDate` replaced by explicit `.value` with YYYY-MM-DD format
- **Fix**: `num_days` calculation simplified — all days in period counted (no exclusion)
- **Label**: "Eau traitée (période)" → "Eau usée traitée (période)"

**2026-02-14**: Qualité eaux brutes + Impact CO₂e :
- **New**: `dbo5_mg_l`, `dco_mg_l`, `mes_mg_l` columns added to `device_config` (defaults: 570, 1250, 650)
- **New**: Section "Qualité des eaux brutes" dans /admin (3 inputs DBO5/DCO/MES par device)
- **New**: `calculate_co2e_impact()` function in routes.py (PRG CH₄=28, MCF fosse=0.5, MCF FPV=0.03)
- **New**: API `/api/pump-cycles` returns `co2e_impact` (co2e_avoided_kg, reduction_percent, ch4_avoided_kg)
- **New**: Dashboard bandeau 4 colonnes "TRAITEMENT & IMPACT ENVIRONNEMENTAL"

**2026-02-14**: Fix voltage : médiane + filtrage 180-260V
**2026-02-14**: Refonte dashboard compact + Type de poste + Traitement eau
**2026-02-14**: Ajout champ Débit effectif (flow_rate)
**2026-02-14**: Pump models management + admin enhancements
**2026-02-14**: Dashboard KPI min/max + tri colonnes
**2026-02-13**: Admin config page for custom device/channel names
**2026-02-13**: Multi-device support + date fix
**2026-02-13**: Dashboard and cycle detection added
**2026-02-13**: Modular architecture refactoring

# User Preferences

Preferred communication style: Simple, everyday language (French).

# Project Architecture

## File Structure

```
shelly_collector_fp/
├── main.py                    # FastAPI app, middleware, dashboard/admin routes, startup/shutdown
├── config.py                  # Centralized configuration (DB, dashboard, device ID)
├── services/
│   ├── __init__.py
│   ├── database.py            # DB pool (create/close), create_tables(), migration
│   ├── cycle_detector.py      # detect_cycles() - gap-based ON/OFF cycle detection
│   ├── config_service.py      # CRUD for device/channel names + pump models (device_config, pump_models)
│   └── config_versions_service.py  # SCD Type 2 config versioning (device_config_versions)
├── api/
│   ├── __init__.py
│   └── routes.py              # /api/ingest/batch + /api/pump-cycles + /api/config/* + /api/stats/queue
├── web/
│   ├── __init__.py
│   ├── dashboard.py           # render_dashboard() - Full HTML/CSS/JS page
│   └── admin.py               # render_admin() + render_pumps_admin() - Config pages
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic PowerLogData model
├── pyproject.toml
└── replit.md
```

## Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Health check (plain text) |
| `/dashboard` | GET | Web dashboard (HTML) |
| `/admin` | GET | Admin config page (HTML) |
| `/admin/pumps` | GET | Pump models management page (HTML) |
| `/api/ingest/batch` | POST | Batch data ingestion from Cloudflare Queue (secured by X-Api-Key) |
| `/api/stats/queue` | GET | Ingestion stats (last 24h) |
| `/api/pump-cycles` | GET | Cycle data API (JSON) |
| `/api/verify-export-password` | POST | Verify CSV export password |
| `/api/config/devices` | GET | List devices with custom names + pump model info |
| `/api/config/device` | POST | Update device + channels config (transaction) |
| `/api/config/channel` | POST | Update channel name |
| `/api/config/device/{id}` | DELETE | Delete device config |
| `/api/config/current` | GET | List all active configs (from device_config_versions) |
| `/api/config/current` | PUT | Update current config in place (no versioning) |
| `/api/config/version` | POST | Create new config version with effective date |
| `/api/config/history` | GET | List all config versions for device/channel |
| `/api/config/pump-models` | GET | List all pump models |
| `/api/config/pump-model` | POST | Create pump model |
| `/api/config/pump-model/{id}` | PUT | Update pump model |
| `/api/config/pump-model/{id}` | DELETE | Delete pump model (protected if in use) |

## Dashboard Features

- **Cycle detection**: Gap >= 4 minutes between measurements = pump stopped
- **Minimum cycle**: Cycles < 2 minutes filtered out (noise)
- **Default view**: Last 30 days
- **Filters**: Device ID, Channel (switch:0/1/2/3), date range
- **Stats banner**: Compact "SYNTHESE DES CYCLES" with emojis (total, ongoing, avg duration, avg power, ampere range, watt range)
- **Treatment banner**: "TRAITEMENT & IMPACT ENVIRONNEMENTAL" showing treated water volume, daily average, CO₂e avoided
- **Export CSV**: French format (semicolon separator), password-protected
- **Ongoing cycles**: Marked as "En cours" if last measurement < 3 min ago
- **Style**: FiltrePlante green theme (#2d8659)
- **Timezone**: UTC+0 (Senegal, no conversion needed)

## Data Collection Strategy

**Architecture: Shelly → Cloudflare Queue → HTTP batch POST → Replit**

**Cloudflare Queue** (upstream):
- Shelly devices push to Cloudflare Worker
- Worker queues messages with throttling
- Queue consumer sends HTTP POST batch to Replit `/api/ingest/batch`

**Batch Ingestion** (in `api/routes.py`):
- `POST /api/ingest/batch` receives up to 1000 messages per batch
- Secured by `INGEST_API_KEY` (X-Api-Key header)
- Deduplication via `idempotency_key` = `{device_id}_{channel}_{minute_epoch}`
- Minute-level bucketing: `minute_epoch = timestamp // 60`
- Supports 4 channels (switch:0, switch:1, switch:2, switch:3)
- Atomic transaction per batch
- Returns: `{inserted, duplicates, errors, total_messages, devices, processing_time}`

## Configuration (config.py)

```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 3
SHELLY_DEVICE_ID = "shellypro4pm-a0dd6c9ef474"
GAP_THRESHOLD_MINUTES = 4
MIN_CYCLE_DURATION_MINUTES = 2
DEFAULT_DAYS_HISTORY = 30
```

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP endpoints
- **uvicorn** - ASGI server
- **asyncpg** - Async PostgreSQL driver
- **pydantic** - Data validation (included with FastAPI)

## External Services

- **Shelly Pro 4PM** - IoT device
- **Cloudflare Queue** - Message queuing and batch delivery
- **Replit Autoscale** - Production hosting

## Database Schema

```sql
CREATE TABLE power_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    apower_w FLOAT NOT NULL,
    voltage_v FLOAT NOT NULL,
    current_a FLOAT NOT NULL,
    energy_total_wh FLOAT NOT NULL,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_power_logs_timestamp ON power_logs(timestamp DESC);
CREATE INDEX idx_power_logs_device_channel ON power_logs(device_id, channel);
CREATE UNIQUE INDEX idx_power_logs_idempotency ON power_logs(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE pump_models (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    power_kw REAL NOT NULL,
    current_ampere REAL NOT NULL,
    flow_rate_hmt8 REAL NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- device_config kept for backward compatibility (synced by config_versions_service)

CREATE TABLE device_config_versions (
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
    effective_to DATE,  -- NULL = currently active version
    created_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

-- SCD Type 2: effective_from/effective_to for temporal tracking
-- Fusion: changing one field copies others from previous version
-- Multiple versions per device/channel, only one active (effective_to IS NULL)
```

## Environment Variables / Secrets

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `INGEST_API_KEY` | API key for batch ingestion endpoint |
| `CSV_EXPORT_PASSWORD` | Password for CSV export |
| `SESSION_SECRET` | Session secret |

## Deployment

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```
