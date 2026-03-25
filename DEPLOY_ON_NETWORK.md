# SHELDON On-Network Deployment

## What you need on the company laptop

### Prerequisites
1. **Python 3.10+** — https://www.python.org/downloads/
2. **ODBC Driver 17 for SQL Server** — https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
3. **SnowSQL** (for Snowflake queries) — https://docs.snowflake.com/en/user-guide/snowsql-install-config

### Install
```
cd "path\to\SHELDON Executive Interface"
pip install -r requirements.txt
```

### Files needed
Copy the entire `SHELDON Executive Interface` folder. Key files:
- `sheldon_api.py` — Flask API server (port 5000)
- `sheldon_brain.py` — AI chat engine
- `SHELDON.html` — Dashboard (open in browser)
- `.env` — OpenAI API key (do NOT commit)
- `start_sheldon.bat` — One-click startup

### Run
```
start_sheldon.bat
```
Then open `SHELDON.html` in Chrome/Edge.

## What lights up on-network

| Source | Off-network | On-network |
|---|---|---|
| Snowflake (Redzone) | Works (SnowSQL) | Works |
| Sage X3 | Works (Power Automate OAuth) | Works |
| CI (AQFDB6) | Fails | **35 KPI queries go live** |
| MANUFACTURING (AQFDB6) | Fails | **Attainment, EOP, labor** |
| AMMS (AQFAM1\AMMS) | Fails | **Supply + repair costs** |
| MANNINGS (AQFDB7\KRONWFC) | Fails | **Retort cycles, deviations** |
| Donna QA (localhost:5002) | Only if running | Only if running |

## Database connections (already configured in sheldon_api.py)

| Database | Server | User | Status |
|---|---|---|---|
| CI | AQFDB6 | SocialScaleReadOnly | Confirmed |
| MANUFACTURING | AQFDB6 | SocialScaleReadOnly | Confirmed |
| AMMS | AQFAM1\AMMS | AMMSro | Confirmed |
| MANNINGS | AQFDB7\KRONWFC | SocialScaleReadOnly | Confirmed (retort project) |

## Quick test (on-network)
```
curl http://localhost:5000/api/health
curl http://localhost:5000/api/kpi/departments
```

The `/api/kpi/departments` response will show which queries succeed vs fail. Any `"status": "error"` entries need investigation.

## For Ayden (server deployment)
Same setup but use waitress instead of Flask dev server. Add to `sheldon_api.py` bottom:
```python
if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
```
Then register as a Windows service or run via Task Scheduler.
