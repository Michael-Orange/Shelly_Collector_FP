# Overview

This project is a **Shelly device data collector and monitoring dashboard** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. It includes a web dashboard to visualize pump operation cycles with filtering and CSV export.

# Recent Changes

**2026-02-14 (Latest)**: Qualité eaux brutes + Impact CO₂e :
- **New**: `dbo5_mg_l`, `dco_mg_l`, `mes_mg_l` columns added to `device_config` (defaults: 570, 1250, 650)
- **New**: Section "Qualité des eaux brutes" dans /admin (3 inputs DBO5/DCO/MES par device)
- **New**: `calculate_co2e_impact()` function in routes.py (PRG CH₄=28, MCF fosse=0.5, MCF FPV=0.03)
- **New**: API `/api/pump-cycles` returns `co2e_impact` (co2e_avoided_kg, reduction_percent, ch4_avoided_kg)
- **New**: Dashboard bandeau 4 colonnes "TRAITEMENT & IMPACT ENVIRONNEMENTAL" (eau traitée, par jour, émissions évitées, réduction %)
- **Modified**: `upsert_device_with_channels()` — accepts dbo5/dco/mes params, persists on INSERT and UPDATE
- **Modified**: `get_configs_map()` — returns dbo5/dco/mes per device
- **Modified**: GET `/api/config/devices` — returns dbo5/dco/mes per device
- **Fix**: Removed shadowing `from datetime import timedelta` inside pump-cycles handler

**2026-02-14**: Fix voltage : médiane + filtrage 180-260V :
- **Modified**: `cycle_detector.py` — voltage par cycle utilise MÉDIANE au lieu de MOYENNE
- **Modified**: `_median_voltage()` helper — filtre les valeurs < 180V ou > 260V (élimine les 0V artefacts)
- **Modified**: Retourne `None` si aucune valeur valide dans la plage

**2026-02-14**: Refonte dashboard compact + Type de poste + Traitement eau :
- **New**: `pump_type` TEXT NOT NULL DEFAULT 'relevage' column added to `device_config` (relevage/sortie/autre)
- **New**: Dashboard bandeau compact "SYNTHESE DES CYCLES" (Option C) — 6 stats avec emojis sur 2 lignes
- **New**: Dashboard bandeau "TRAITEMENT & ABATTEMENT" — volume eau traitée en m³ (vert teal)
- **New**: API `/api/pump-cycles` returns `treatment_stats.treated_water_m3` + `pump_type`/`volume_m3` per cycle
- **Modified**: `/admin` page — new "Type de poste" dropdown per channel (Relevage/Sortie/Autre)
- **Modified**: Dashboard dates par défaut changées de 45 → 30 jours
- **Modified**: `DEFAULT_DAYS_HISTORY` = 30 in config.py
- **Modified**: Stats ampères et watts affichées en range (min - max) au lieu de 4 cartes séparées

**2026-02-14**: Ajout champ Débit effectif (flow_rate) :
- **New**: `flow_rate` REAL NULL column added to `device_config`
- **Modified**: `/admin` page — new "Débit (m3/h)" column per channel with validation
- **Modified**: `upsert_device_with_channels()` — saves/validates flow_rate (positive number)
- **Modified**: `get_configs_map()` — returns flow_rate in channel_configs
- **Modified**: `POST /api/config/device` — returns 400 on invalid flow_rate
- **Modified**: Pump model select format now shows "si HMT 8" suffix
- **Modified**: Column headers (NOM, MODELE, DEBIT) above channel rows

**2026-02-14**: Pump models management + admin enhancements:
- **New**: `pump_models` table — catalogue of pump models (name, power_kw, current_ampere, flow_rate_hmt8)
- **New**: 2 initial Pedrollo models seeded at startup (VXM 10/35, DM/8)
- **New**: `pump_model_id` column added to `device_config` (FK to pump_models)
- **New**: CRUD API for pump models: GET/POST/PUT/DELETE `/api/config/pump-model*`
- **New**: Page `/admin/pumps` — full CRUD for pump models (create, edit, delete with protection)
- **Modified**: `/admin` page — per-channel pump model dropdown + single "Enregistrer tout" button (transaction)
- **Modified**: `POST /api/config/device` — accepts `channels` array with `pump_model_id` (backward compatible)
- **Modified**: `GET /api/config/devices` — returns `channel_configs` with pump_model info (LEFT JOIN)
- **Gap threshold**: Changed from 3 to 4 minutes for cycle detection

**2026-02-14**: Dashboard KPI min/max + tri colonnes :
- **Cycle detector**: Calcule `avg_current_a` par cycle (requête SQL inclut `current_a`)
- **API**: `/api/pump-cycles` retourne `stats` (max_current, min_current, max_power, min_power)
- **Dashboard**: 4 nouveaux KPI (Max/Min Ampères, Max/Min Watts) — total 8 cartes
- **Dashboard**: Colonnes du tableau triables (clic en-tête : desc → asc → reset)
- **Dashboard**: Dropdowns Device/Canal chargés dynamiquement avec noms custom

**2026-02-13**: Admin config page for custom device/channel names:
- **New**: `services/config_service.py` - CRUD for device/channel name mappings
- **New**: `web/admin.py` - Admin page at `/admin` for editing device/channel names
- **New**: `device_config` table created automatically at startup (no manual migration)
- **New**: API endpoints: GET `/api/config/devices`, POST `/api/config/device`, POST `/api/config/channel`, DELETE `/api/config/device/{id}`
- **Dashboard**: Displays custom names (device_name, channel_name) with fallback on technical IDs
- **Dashboard**: Link to Configuration page in header
- **CSV**: Uses custom names in export
- **Auto-discovery**: Devices/channels detected from `power_logs` (no hardcoding)

**2026-02-13**: Multi-device support + date fix:
- **Fix**: ISO date format bug (`+00:00Z` → `Z` only) — "Invalid Date" in JavaScript resolved
- **Multi-device**: API `device_id` filter now optional (all devices by default)
- **Multi-device**: Cycle detector groups by `(device_id, channel)` instead of channel only
- **Multi-device**: Dashboard has "Device" dropdown filter, auto-populated from DB
- **Multi-device**: API returns `device_ids` list instead of single `device_id`
- **UI**: Device ID column added to table (before Canal)
- **UI**: Header cleaned — removed "Shelly Pro 4PM" reference
- **UI**: Date format DD/MM/YYYY and HHhMM via manual UTC parsing (no toLocaleDateString)
- **CSV**: Device ID column added, same manual date formatting

**2026-02-13**: Dashboard and cycle detection added:
- `services/cycle_detector.py` - Detects pump ON/OFF cycles via gap analysis (3min gap = pump stopped)
- `api/routes.py` - GET `/api/pump-cycles` endpoint returning cycle data as JSON
- `web/dashboard.py` - Full HTML dashboard with FiltrePlante style (#2d8659 green)
- `/dashboard` route serving the web interface
- Filter by channel/date, export CSV (French format), stats cards, ongoing cycle detection
- `SHELLY_DEVICE_ID` in config.py (used as reference, no longer mandatory filter)
- `db_pool` stored in `app.state` to avoid circular imports

**2026-02-13**: Modular architecture refactoring:
- Refactored from single `main.py` into modular structure
- `config.py`, `services/database.py`, `models/schemas.py`
- Zero behavioral changes, timezone bug caught and fixed

**2025-10-11**: Complete system rewrite - Ultra-simplified architecture:
- Simple 1-minute throttling per channel
- Code reduction: 321 lines → 110 lines

# User Preferences

Preferred communication style: Simple, everyday language (French).

# Project Architecture

## File Structure

```
shelly_collector_fp/
├── main.py                    # FastAPI app, middleware, WebSocket, dashboard/admin routes, startup/shutdown
├── config.py                  # Centralized configuration (DB, throttle, dashboard, device ID)
├── services/
│   ├── __init__.py
│   ├── database.py            # DB pool (create/close), create_tables(), should_write(), insert_power_log()
│   ├── cycle_detector.py      # detect_cycles() - gap-based ON/OFF cycle detection
│   └── config_service.py      # CRUD for device/channel names + pump models (device_config, pump_models)
├── api/
│   ├── __init__.py
│   └── routes.py              # /api/pump-cycles + /api/config/* endpoints
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
| `/ws` | WebSocket | Shelly data collection endpoint |
| `/dashboard` | GET | Web dashboard (HTML) |
| `/admin` | GET | Admin config page (HTML) |
| `/api/pump-cycles` | GET | Cycle data API (JSON) |
| `/admin/pumps` | GET | Pump models management page (HTML) |
| `/api/config/devices` | GET | List devices with custom names + pump model info |
| `/api/config/device` | POST | Update device + channels config (transaction) |
| `/api/config/channel` | POST | Update channel name |
| `/api/config/device/{id}` | DELETE | Delete device config |
| `/api/config/pump-models` | GET | List all pump models |
| `/api/config/pump-model` | POST | Create pump model |
| `/api/config/pump-model/{id}` | PUT | Update pump model |
| `/api/config/pump-model/{id}` | DELETE | Delete pump model (protected if in use) |

## Dashboard Features

- **Cycle detection**: Gap >= 4 minutes between measurements = pump stopped
- **Minimum cycle**: Cycles < 2 minutes filtered out (noise)
- **Default view**: Last 30 days
- **Filters**: Device ID, Channel (switch:0/1/2), date range
- **Stats banner**: Compact "SYNTHESE DES CYCLES" with emojis (total, ongoing, avg duration, avg power, ampere range, watt range)
- **Treatment banner**: "TRAITEMENT & ABATTEMENT" showing treated water volume in m³ for relevage pumps
- **Export CSV**: French format (semicolon separator)
- **Ongoing cycles**: Marked as "En cours" if last measurement < 3 min ago
- **Style**: FiltrePlante green theme (#2d8659)
- **Timezone**: UTC+0 (Senegal, no conversion needed)

## Data Collection Strategy

**Cloudflare Worker Prefiltering** (upstream):
- Worker URL: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
- Filters messages to >10W only on valid channels (0, 1, 2)
- Lazy connection: Only connects to Replit when >10W detected

**1-Minute Throttling** (in `services/database.py`):
- `should_write()` with state key format: `{device_id}_ch{channel_int}`
- On message arrival: If >1 minute since last write → write to DB

**RPC Bootstrap** (in `main.py`):
- Sent via `send_text()` (NOT `send_json()`) with `"src":"collector"`
- Command 1: `NotifyStatus` with `enable: true`
- Command 2: `Shelly.GetStatus`

## Configuration (config.py)

```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 3
THROTTLE_INTERVAL_SECONDS = 60
SHELLY_DEVICE_ID = "shellypro4pm-a0dd6c9ef474"
GAP_THRESHOLD_MINUTES = 4
MIN_CYCLE_DURATION_MINUTES = 2
DEFAULT_DAYS_HISTORY = 45
```

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server
- **asyncpg** - Async PostgreSQL driver
- **pydantic** - Data validation (included with FastAPI)

## External Services

- **Shelly Pro 4PM** - IoT device (WebSocket JSON-RPC)
- **Cloudflare Worker** - Message filtering proxy (`wss://shelly-filter-proxy.michael-orange09.workers.dev`)
- **Replit Autoscale** - Production hosting (`wss://shelly-ws-collector-sagemcom.replit.app/ws`)

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
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_power_logs_timestamp ON power_logs(timestamp);
CREATE INDEX idx_power_logs_device_channel ON power_logs(device_id, channel);

CREATE TABLE pump_models (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    power_kw REAL NOT NULL,
    current_ampere REAL NOT NULL,
    flow_rate_hmt8 REAL NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- device_config also has: pump_model_id INTEGER REFERENCES pump_models(id)
-- device_config also has: flow_rate REAL NULL
-- device_config also has: pump_type TEXT NOT NULL DEFAULT 'relevage' (relevage/sortie/autre)
```

## Deployment

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Shelly Device Configuration

- Enable: Settings → Connectivity → Outbound Websocket
- Server address: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
