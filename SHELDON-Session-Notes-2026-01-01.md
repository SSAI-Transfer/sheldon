# SHELDON Development Session Notes
**Date:** January 1, 2026
**Status:** Direct Database Integration Complete

---

## REMINDER FOR NEXT SESSION
**Provide Claude with an Anthropic API key to enable AI chat responses directly from SHELDON (replacing Make.com chat webhook).**

---

## What Was Accomplished

### Migrated from Make.com Webhooks to Direct Database Connections

SHELDON now queries Snowflake and SQL Server directly via a local Python API server, eliminating dependency on Make.com for data retrieval.

### New Files Created

| File | Purpose |
|------|---------|
| `sheldon_api.py` | Flask API server - queries Snowflake & SQL Server |
| `requirements.txt` | Python dependencies (flask, flask-cors) |
| `start_sheldon_api.bat` | Windows batch file to start API server |

### Architecture

```
SHELDON.html (browser)
       │
       ▼ HTTP (localhost:5000)
sheldon_api.py (Flask API)
       │
       ├── Snowflake (SnowSQL CLI)
       │   └── OEE, Production, Downtime, Labor
       │
       └── SQL Server (Power Automate OAuth)
           └── Revenue, Inventory, AR, Finished Goods
```

---

## How to Start SHELDON

1. **Start the API server first:**
   - Double-click `start_sheldon_api.bat`
   - Or run: `python sheldon_api.py`
   - Server runs at http://localhost:5000

2. **Open SHELDON.html in browser**

3. Dashboard auto-refreshes every 60 seconds

---

## API Endpoints Available

### Operations (Snowflake)
- `GET /api/kpi/live` - Plant OEE, production, downtime
- `GET /api/redflags` - Lines below 70% OEE target
- `GET /api/operations/downtime` - Downtime breakdown
- `GET /api/operations/labor` - Labor productivity
- `GET /api/operations/trend` - Hourly OEE trend
- `GET /api/operations/active-lines` - Currently running lines

### Financial (Sage X3)
- `GET /api/financial/revenue` - Daily/MTD/YTD revenue
- `GET /api/financial/kpis` - Financial KPIs
- `GET /api/inventory/value` - Inventory value by facility
- `GET /api/inventory/kpis` - Inventory KPIs
- `GET /api/inventory/finished-goods` - FG value
- `GET /api/ar/days` - AR Days

### Combined
- `GET /api/briefing` - Executive briefing (all sources)
- `GET /api/health` - API health check

---

## Current Data Status

### Working (SQL Server / Sage X3)
- Total Inventory Value: $122.5M
- Finished Goods: $15.4M
- AR Days: 45
- Inventory by Facility (FD1, PK1, TP1)

### Awaiting Data (Snowflake)
- OEE metrics (no Jan 2026 production data yet)
- Downtime tracking
- Labor productivity
- Line status

### Still Using Make.com
- **Chat webhook** - AI responses still go through Make.com
- Next session: Replace with Anthropic API using provided key

---

## Database Credentials (Already Configured in sheldon_api.py)

### SQL Server (Sage X3)
- Server: `AQFDB1\X3`
- Database: `x3`
- Schema: `AMQ`
- Auth: Microsoft OAuth 2.0 via Power Automate

### Snowflake
- Connection: `ameriqual` (SnowSQL)
- Database: `ZGRZDCXCHH_DB`
- Schema: `ameriqual-org`
- Data: Redzone production metrics

---

## Files Modified

### SHELDON.html Changes
1. Updated webhook configuration to use local API (`localhost:5000`)
2. Updated all fetch functions to handle new API response formats
3. Enabled 60-second data polling (was disabled for Make.com credits)
4. Chat still uses Make.com webhook (pending API key)

---

## Next Steps

1. [ ] Get Anthropic API key for local AI chat
2. [ ] Add chat endpoint to sheldon_api.py using API key
3. [ ] Update SHELDON.html chat to use local endpoint
4. [ ] Test with live production data when available
5. [ ] Consider adding more financial KPIs (EBITDA, Gross Margin)

---

## Troubleshooting

### API Server Won't Start
- Ensure Python is installed
- Run: `pip install flask flask-cors`

### No Data Showing
- Check API server is running: http://localhost:5000/api/health
- Check browser console for errors
- Verify network connectivity to databases

### Snowflake Data Empty
- SnowSQL must be installed at `C:\Program Files\Snowflake SnowSQL\snowsql.exe`
- Connection "ameriqual" must be configured in SnowSQL
- Data only shows for dates with production activity

---

*Session completed: January 1, 2026*
