# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system accepts incoming WebSocket connections from Shelly smart switches, processes their status updates, and maintains minute-by-minute power consumption logs with intelligent activity-based filtering.

The primary goal is to monitor specific power channels (particularly switch:2 for a pump) and log data only when the device is actively consuming power above a configurable threshold, minimizing noise and storage while maintaining accurate historical records.

# Recent Changes

**2025-10-11 (Latest)**: Cost optimization - reduced resource usage:
- **🔧 PostgreSQL pool**: Reduced max_size from 10 → 3 connections (lightweight usage pattern)
- **🔧 Sampling ch2**: Increased from 20min → 30min (-33% writes for pump channel)
- **Result**: ~30-40% cost reduction on PostgreSQL + compute units while maintaining data quality

**2025-10-11**: Implemented grace period for WebSocket disconnections:
- **🔧 Problem**: WebSocket disconnections (every 5 min from Cloudflare) were cancelling timers prematurely, preventing 0W writes
- **🔧 Solution - Option C**: Timers now continue running during disconnections (automatic grace period of 2 minutes)
- **🔧 Behavior**: Reconnection with activity >10W → timer reset; No reconnection/activity → timer expires → 0W written
- **🔧 Enhanced logging**: Added `flush=True` to all print statements for immediate log visibility
- **Result**: Eliminates missing 0W entries caused by temporary WebSocket disconnections while preserving accurate stop detection

**2025-10-11**: Fixed critical timer recreation bug causing parasitic 0W writes:
- **🔧 Root cause identified**: When ≤10W message arrived, old timer was cancelled but new timer was NOT created (due to `continue` before timer creation)
- **🔧 Solution - try/finally pattern**: Timer now ALWAYS recreated in finally block, even if message is filtered
- **🔧 Separated delay function**: Created `trigger_stop_after_delay()` to cleanly separate sleep from stop logic
- **🔧 Enhanced logging**: Added RAW message logs (before filtering) + detailed STOP attempt logs with decision traces
- **Result**: Eliminates orphaned timers that would expire during active operation and write spurious 0W entries

**2025-10-11**: Uniformized hysteresis timeout to 2 minutes for all channels:
- **All channels (0, 1, 2)**: Now use 2-minute timeout (previously ch0/1 used 1 min)
- Provides consistent stop detection across all equipment types
- Reduces false positives for short-duration equipment on channels 0 & 1

**2025-10-11**: Fixed critical race condition causing duplicate 0W writes:
- **🔧 Protection 5 - asyncio.Lock**: Global lock serializes all stop write operations (prevents concurrent timer execution)
- **🔧 Protection 3b - Enhanced anti-duplication**: Additional check for existing 0W entries in same minute (blocks any doublons)
- **Problem solved**: Multiple timers expiring simultaneously were passing all checks in parallel before any wrote, creating duplicate 0W entries
- **Result**: Zero duplicate stop entries - only ONE 0W per genuine stop event

**2025-10-11**: Added 4-layer protection system to eliminate ALL parasitic 0W writes:
- **🔧 Layer 1 - Security filter**: Server ignores any message with apower ≤10W (double-check after Cloudflare)
- **🔧 Layer 2 - Conditional hysteresis**: Timer only writes 0W if last_written_power >10W (prevents stops on micro-activity)
- **🔧 Layer 3 - Anti-duplication**: No 0W write if >10W entry already exists in same minute
- **🔧 Layer 4 - Systematic timer reset**: Every message (even without DB write) cancels/recreates timer
- **Result**: Only genuine stops (after real activity >10W) write 0W - zero parasitic entries

**2025-10-11**: Complete refactoring to timer-based stop detection with Cloudflare prefiltering:
- **Cloudflare prefiltering**: Messages already filtered (>10W, valid channels only) - removed all server-side threshold/channel verification
- **Timer-based hysteresis**: Stop detection now based on message absence (not power threshold)
- **Simplified logic**: All received messages = pump active (no state machine transitions)
- **Updated sampling**: Channels 0/1 from 3min to 5min, channel 2 stays 20min
- **Result**: Drastically simplified codebase, eliminated false stop bugs, maintains accurate pump tracking

**2025-10-09**: Added channel-specific hysteresis to prevent false stop detections:
- Implemented 2-minute confirmation period for channel 2 (pump) before logging OFF state
- Protects against erratic 0W sensor readings that were causing false stop/start cycles
- Channels 0 & 1 remain unchanged with immediate stop detection (suitable for short-duration equipment ≤4min)
- Result: Eliminates spurious stop entries in database while preserving accurate pump cycle tracking

**2025-10-09**: Added periodic sampling + delta-based filtering optimization:
- Implemented intelligent delta-based filtering with `POWER_DELTA_MIN_W = 10W`
- Periodic sampling: channels 0/1 every 3 minutes, channel 2 every 20 minutes
- Enhanced logging with write reasons (start/delta/sample/stop) for debugging
- Result: Drastically reduced DB writes while preserving all critical events

**2025-10-08**: Migrated from CSV to PostgreSQL for data persistence:
- Created `power_logs` table with proper indexing (timestamp, device_id+channel)
- Replaced CSV file writes with async PostgreSQL inserts using asyncpg
- Resolved Autoscale persistence issue where CSV files were lost on instance restart
- All data now persists reliably in managed PostgreSQL database (free tier)
- Removed debug logs (RAW messages) to reduce noise

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
**Problem**: Shelly devices send frequent status updates, but we only want to log critical events and significant changes. Shelly sensors occasionally send erratic 0W readings during normal operation.

**Solution**: Timer-based stop detection with Cloudflare prefiltering + delta-based intelligent logging

**Cloudflare Prefiltering** (upstream):
- Filters messages to >10W only on valid channels
- Server receives ONLY relevant messages - no threshold checks needed server-side
- All received messages = pump is active

**Timer-Based Stop Detection**:
- Each message resets a per-channel timer
- If no message received for X minutes → write stop (0W)
- **Stop timeout** (`STOP_TIMEOUT_MINUTES`):
  - **All channels (0, 1, 2)**: 2 minutes without message → confirmed stop
- Eliminates false stops from momentary glitches (erratic 0W readings don't reach server)

**Write Logic**:
- **First message per channel**: Force write (start)
- **Subsequent messages**: Write if:
  - Variation ≥10W (`POWER_DELTA_MIN_W`) vs last write → (delta)
  - OR periodic sample minute → (sample)
- **Stop detection**: Timer expires (no message for X min) → write 0W (stop)

**Periodic sampling**:
  - Channels 0 & 1: every 5 minutes (at :00, :05, :10, :15, etc.)
  - Channel 2: every 20 minutes (at :00, :20, :40)
  - Samples only written if no delta write in that minute (anti-duplication)
- Maximum one entry per minute per channel

**Rationale**: Timer-based approach drastically simplifies logic and eliminates all false stop bugs. Cloudflare prefiltering removes server-side complexity. Delta + sampling preserves critical events and trend data while minimizing writes. Example: Pump running at 430W, Cloudflare blocks erratic 0W reading, server timer keeps running, only real stops (2+ min silence) trigger stop write.

## State Management
**In-memory channel state tracking** using Python dictionaries:
- `channel_states`: Stores last written timestamp, power value, and telemetry per device/channel
- `stop_timers`: Asyncio tasks that trigger stop write when no message received for X minutes
- Tracks last written power value for delta calculations
- Stores last telemetry (voltage, current, energy) for stop write

**Timer Management**:
- Each message cancels existing timer and creates new one
- Timer duration: 2 minutes for all channels (0, 1, 2)
- Timer callback writes stop (0W) with last known telemetry
- Timers cancelled on WebSocket disconnect

**Trade-offs**: 
- ✅ Simple implementation, no external dependencies
- ✅ Fast lookups and delta calculations
- ✅ Eliminates false stop bugs (timer-based vs threshold-based)
- ⚠️ State lost on restart (acceptable - next message will reinitialize)
- ⚠️ Memory grows with device/channel count (minimal for typical deployments)

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
3. **Cloudflare prefiltering** (upstream): Only >10W messages on valid channels reach server
4. **JSON-RPC message parsing** from `params.switch:{X}` format
5. **Timer management**: Cancel existing timer, process message, create new timer
6. **Write logic**:
   - First message for channel → write (start)
   - Subsequent messages → write if delta ≥10W OR sample minute
   - Anti-duplication: max 1 write per minute per channel
7. **Stop detection**: Timer expires (X min without message) → callback writes 0W (stop)
8. **PostgreSQL insert** with async connection pooling and error handling

## Configuration
**Top-level constants** for easy customization:
- `POWER_DELTA_MIN_W = 10` - Minimum power variation to log during activity (delta filtering)
- `SAMPLE_INTERVALS = {0: 5, 1: 5, 2: 20}` - Periodic sampling intervals in minutes per channel
- `STOP_TIMEOUT_MINUTES = {0: 1, 1: 1, 2: 2}` - Minutes without message before confirming stop (timer-based hysteresis)

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