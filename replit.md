# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system accepts incoming WebSocket connections from Shelly smart switches, processes their status updates, and maintains minute-by-minute power consumption logs with intelligent activity-based filtering.

The primary goal is to monitor specific power channels (particularly switch:2 for a pump) and log data only when the device is actively consuming power above a configurable threshold, minimizing noise and storage while maintaining accurate historical records.

# Recent Changes

**2025-10-08 (Latest)**: Migrated from CSV to PostgreSQL for data persistence:
- Created `power_logs` table with proper indexing (timestamp, device_id+channel)
- Replaced CSV file writes with async PostgreSQL inserts using asyncpg
- Resolved Autoscale persistence issue where CSV files were lost on instance restart
- All data now persists reliably in managed PostgreSQL database (free tier)
- Removed debug logs (RAW messages) to reduce noise
- Set `POWER_THRESHOLD_W = 5W` for production (only logs activity above 5W)

**2025-10-09**: Adjusted monitored channels to [0, 1, 2] (removed channel 3)

**2025-10-08**: Added RPC bootstrap commands to actively request data from Shelly upon WebSocket connection:
- `NotifyStatus` with `{"enable": true}` to activate streaming notifications
- `Shelly.GetStatus` to immediately retrieve full device status
- Fixed JSON parsing to support both flat (`params.switch:X`) and nested (`params.device_status.switch:X`) formats
- Expanded monitoring from channel [2] to all channels [0,1,2,3]

**2025-10-08**: Fixed critical bug in `fill_missing_minutes()` where backfilled rows were incorrectly using the newest telemetry values instead of historical data for intermediate minutes.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Framework & Server
- **FastAPI** web framework with WebSocket support
- **Uvicorn ASGI** server for production deployment
- Hosted on **Replit** with public WebSocket endpoint at `/ws`
- HTTP health check endpoint at `/` returning plain text status

## Data Collection Strategy
**Problem**: Shelly devices send frequent status updates, but we only want minute-granularity data during active periods.

**Solution**: Smart activity-based logging with configurable power threshold
- Monitor power consumption (`apower`) against configurable threshold (default: 5W)
- Write maximum one entry per minute per channel
- Only log when device is actively consuming power (above threshold)
- Fill missing minutes during active periods to ensure continuity

**Rationale**: This approach minimizes storage and noise while preserving complete activity records. The minute-resolution provides sufficient granularity for power analysis without overwhelming detail.

## State Management
**In-memory channel state tracking** using Python dictionaries:
- Stores last written timestamp per device/channel combination
- Tracks last known values for gap-filling
- Maintains activity state (above/below threshold)

**Trade-offs**: 
- ✅ Simple implementation, no external dependencies
- ✅ Fast lookups and updates
- ⚠️ State lost on restart (acceptable for continuous logging use case)
- ⚠️ Memory grows with number of unique device/channel combinations (minimal for typical deployments)

## Data Storage
**PostgreSQL database** (`power_logs` table)
- Schema: `timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh`
- UTC timestamps stored as TIMESTAMPTZ
- Indexed on timestamp and (device_id, channel) for efficient queries
- Async inserts via asyncpg connection pool

**Design choice rationale**:
- PostgreSQL chosen for reliable persistence on Replit Autoscale (files don't persist across instance restarts)
- Free tier PostgreSQL database provided by Replit
- Async inserts maintain performance without blocking WebSocket processing
- Queryable via SQL for analysis and exports
- Connection pooling (1-10 connections) balances resource usage and throughput

## Message Processing Pipeline
1. **WebSocket connection** accepted from Shelly device
2. **RPC bootstrap commands** sent immediately to activate data flow:
   - `NotifyStatus` with `enable: true` to start streaming
   - `Shelly.GetStatus` to retrieve immediate status dump
3. **JSON-RPC message parsing** from `params.switch:{X}` or `params.device_status.switch:{X}` (dual lookup)
4. **Threshold evaluation** to determine activity state
5. **Minute-based rate limiting** with gap-filling logic
6. **PostgreSQL insert** with async connection pooling and error handling

## Configuration
**Top-level constants** for easy customization:
- `CHANNELS = [0, 1, 2]` - Which switch channels to monitor
- `POWER_THRESHOLD_W = 5` - Activity threshold in watts (only logs when power > 5W)
- `WRITE_TZ = "UTC"` - Timezone for timestamps

**Environment variables** (auto-configured by Replit):
- `DATABASE_URL` - PostgreSQL connection string

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server for running FastAPI application
- **asyncpg** - Async PostgreSQL driver for database operations

## External Services & Integrations
- **Shelly Smart Devices** - IoT switches/relays that initiate outbound WebSocket connections
  - Protocol: WebSocket (wss:// or ws://)
  - Message format: JSON-RPC NotifyStatus messages
  - Connection model: Device connects TO server (outbound from device perspective)
  
- **Replit Hosting Platform**
  - Deployment: Autoscale (stateless, cost-effective)
  - Provides SSL/TLS termination for wss:// connections
  - Public URL format: `wss://<repl-name>.<username>.repl.co/ws`
  - Free PostgreSQL database for data persistence

## Deployment Commands
```bash
uv add fastapi uvicorn asyncpg
uvicorn main:app --host 0.0.0.0 --port 5000
```

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
```

## Shelly Device Configuration
- Enable: Settings → Connectivity → Outbound Websocket
- Server address: `wss://<your-repl>.<your-user>.repl.co/ws`
- Alternative for testing: `ws://` (unencrypted)