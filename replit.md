# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to CSV files. The system accepts incoming WebSocket connections from Shelly smart switches, processes their status updates, and maintains minute-by-minute power consumption logs with intelligent activity-based filtering.

The primary goal is to monitor specific power channels (particularly switch:2 for a pump) and log data only when the device is actively consuming power above a configurable threshold, minimizing noise and storage while maintaining accurate historical records.

# Recent Changes

**2025-10-08 (Latest)**: Added RPC bootstrap commands to actively request data from Shelly upon WebSocket connection:
- `NotifyStatus` with `{"enable": true}` to activate streaming notifications
- `Shelly.GetStatus` to immediately retrieve full device status
- Temporarily set `POWER_THRESHOLD_W = 0` for testing (will return to 5W after validation)
- Expanded monitoring from channel [2] to all channels [0,1,2,3]

**2025-10-08**: Fixed critical bug in `fill_missing_minutes()` where backfilled CSV rows were incorrectly using the newest telemetry values instead of historical data for intermediate minutes. Now correctly uses `state['last_data']` for gap-filling and only applies new readings to the current minute.

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
**CSV file-based persistence** (`shelly_ws_log.csv`)
- Headers: `timestamp_iso, device_id, channel, apower_W, voltage_V, current_A, energy_total_Wh`
- UTC timestamps in ISO 8601 format
- Append-only writes for safety and simplicity
- Auto-creation if file doesn't exist

**Design choice rationale**:
- CSV chosen for simplicity, portability, and easy analysis in Excel/Python
- No database overhead for this logging-focused use case
- File-based approach works well with Replit's persistent storage
- Direct writes ensure data durability without buffering complexity

## Message Processing Pipeline
1. **WebSocket connection** accepted from Shelly device
2. **RPC bootstrap commands** sent immediately to activate data flow:
   - `NotifyStatus` with `enable: true` to start streaming
   - `Shelly.GetStatus` to retrieve immediate status dump
3. **JSON-RPC message parsing** from `params.device_status.switch:{X}` structure
4. **Threshold evaluation** to determine activity state
5. **Minute-based rate limiting** with gap-filling logic
6. **CSV append** with error handling for missing fields

## Configuration
**Top-level constants** for easy customization:
- `CHANNELS = [0, 1, 2, 3]` - Which switch channels to monitor
- `POWER_THRESHOLD_W = 0` - Activity threshold in watts (currently 0 for testing, normally 5)
- `WRITE_TZ = "UTC"` - Timezone for timestamps
- `CSV_FILE = "shelly_ws_log.csv"` - Output file path

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server for running FastAPI application
- **websockets** - WebSocket protocol implementation (dependency of FastAPI)

## External Services & Integrations
- **Shelly Smart Devices** - IoT switches/relays that initiate outbound WebSocket connections
  - Protocol: WebSocket (wss:// or ws://)
  - Message format: JSON-RPC NotifyStatus messages
  - Connection model: Device connects TO server (outbound from device perspective)
  
- **Replit Hosting Platform**
  - Provides SSL/TLS termination for wss:// connections
  - Public URL format: `wss://<repl-name>.<username>.repl.co/ws`
  - Requires "Always On" feature for 24/7 operation

## Deployment Commands
```bash
pip install fastapi uvicorn websockets
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Shelly Device Configuration
- Enable: Settings → Connectivity → Outbound Websocket
- Server address: `wss://<your-repl>.<your-user>.repl.co/ws`
- Alternative for testing: `ws://` (unencrypted)