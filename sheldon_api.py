"""
SHELDON API Server
Local backend for direct database queries - replaces Make.com webhooks
Connects to Snowflake (Redzone) and SQL Server (Sage X3)
Includes OpenAI integration for AI chat
"""

from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
import subprocess
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

# Load API keys from .env file (check same directory as this script, then fallback to hardcoded path)
OPENAI_API_KEY = None
_script_dir = os.path.dirname(os.path.abspath(__file__))
_env_paths = [
    os.path.join(_script_dir, '.env'),
    r"E:\Business\AMERIQUAL PROJECT TRACKER\Current Projects\SHELDON Executive Interface\.env",
]
_env_vars = {}
for env_path in _env_paths:
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    _env_vars[key.strip()] = val.strip()
        break

OPENAI_API_KEY = _env_vars.get('OPENAI_API_KEY')
if 'ANTHROPIC_API_KEY' in _env_vars:
    os.environ.setdefault('ANTHROPIC_API_KEY', _env_vars['ANTHROPIC_API_KEY'])

# Azure AD credentials (for Power Automate + MS Graph)
AZURE_TENANT_ID = _env_vars.get('AZURE_TENANT_ID', '')
AZURE_CLIENT_ID = _env_vars.get('AZURE_CLIENT_ID', '')
AZURE_CLIENT_SECRET = _env_vars.get('AZURE_CLIENT_SECRET', '')

# Try to import OpenAI
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        OPENAI_AVAILABLE = True
    else:
        openai_client = None
        OPENAI_AVAILABLE = False
except ImportError:
    openai_client = None
    OPENAI_AVAILABLE = False
    print("OpenAI not installed. Run: pip install openai")

app = Flask(__name__)
CORS(app)  # Allow browser requests from SHELDON

# ============================================
# SQL SERVER (SAGE X3) CLIENT
# ============================================
class SageX3Client:
    """Client for querying Sage X3 via Power Automate OAuth"""

    def __init__(self):
        self.tenant_id = AZURE_TENANT_ID
        self.client_id = AZURE_CLIENT_ID
        self.client_secret = AZURE_CLIENT_SECRET
        self.scope = "https://service.flow.microsoft.com//.default"
        self.power_automate_url = (
            "https://default64fa12bead4d4585a99cd3fd32eb91.b4.environment.api.powerplatform.com:443"
            "/powerautomate/automations/direct/workflows/e3c551c90ce44c2f819e820f834710ff"
            "/triggers/manual/paths/invoke?api-version=1"
        )
        self.server = r"AQFDB1\X3"
        self.database = "x3"
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_token(self) -> str:
        """Get OAuth2 bearer token from Microsoft"""
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }).encode()

        req = urllib.request.Request(
            f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token',
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            self._token_expiry = datetime.now() + timedelta(seconds=result.get('expires_in', 3600) - 60)
            return result['access_token']

    def _ensure_token(self):
        """Ensure we have a valid token"""
        if not self._token or not self._token_expiry or datetime.now() >= self._token_expiry:
            self._token = self._get_token()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        self._ensure_token()

        query_body = json.dumps({
            'server': self.server,
            'database': self.database,
            'sqlQuery': sql
        }).encode()

        req = urllib.request.Request(
            self.power_automate_url,
            data=query_body,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._token}'
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                if isinstance(result, dict) and 'Table1' in result:
                    return result['Table1']
                elif isinstance(result, list):
                    return result
                else:
                    return [result] if result else []
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._token = self._get_token()
                return self.query(sql)
            raise

# ============================================
# SNOWFLAKE CLIENT (via SnowSQL)
# ============================================
class SnowflakeClient:
    """Client for querying Snowflake via SnowSQL CLI"""

    SNOWSQL_SEARCH_PATHS = [
        r"D:\SnowSQL\snowsql.exe",
        r"C:\Program Files\Snowflake SnowSQL\snowsql.exe",
        r"C:\Program Files (x86)\Snowflake SnowSQL\snowsql.exe",
        os.path.expanduser(r"~\AppData\Local\snowflake\SnowSQL\snowsql.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SnowSQL', 'snowsql.exe'),
    ]

    def __init__(self, connection_name: str = "ameriqual"):
        self.connection_name = connection_name
        self.database = "ZGRZDCXCHH_DB"
        self.schema = '"ameriqual-org"'
        self.snowsql_path = self._find_snowsql()

    def _find_snowsql(self) -> Optional[str]:
        """Search common locations for SnowSQL executable."""
        for path in self.SNOWSQL_SEARCH_PATHS:
            if os.path.exists(path):
                return path
        # Try PATH
        import shutil
        found = shutil.which('snowsql')
        return found

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute query using SnowSQL CLI"""
        if not self.snowsql_path:
            raise RuntimeError(f"SnowSQL not found. Searched: {self.SNOWSQL_SEARCH_PATHS}. Install from https://docs.snowflake.com/en/user-guide/snowsql-install-config")

        cmd = [
            self.snowsql_path,
            '-c', self.connection_name,
            '-q', sql,
            '-o', 'output_format=json',
            '-o', 'friendly=false'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"SnowSQL error: {result.stderr}")

        # Parse JSON output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                try:
                    return json.loads(line)
                except:
                    continue
            return []

# ============================================
# MICROSOFT GRAPH CLIENT (Calendar/Presence)
# ============================================
class MicrosoftGraphClient:
    """Client for Microsoft Graph API (Calendar, Users, Presence)"""

    def __init__(self):
        self.tenant_id = AZURE_TENANT_ID
        self.client_id = AZURE_CLIENT_ID
        self.client_secret = AZURE_CLIENT_SECRET
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_token(self) -> str:
        """Get OAuth2 token for Microsoft Graph"""
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }).encode()

        req = urllib.request.Request(
            f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token',
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            self._token_expiry = datetime.now() + timedelta(seconds=result.get('expires_in', 3600) - 60)
            return result['access_token']

    def _ensure_token(self):
        """Ensure we have a valid token"""
        if not self._token or not self._token_expiry or datetime.now() >= self._token_expiry:
            self._token = self._get_token()

    def get_user_calendar(self, user_email: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get calendar events for a user"""
        self._ensure_token()

        # Format dates for Graph API
        start_str = start_date.strftime('%Y-%m-%dT00:00:00Z')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59Z')

        url = (f"{self.graph_url}/users/{user_email}/calendarView"
               f"?startDateTime={start_str}&endDateTime={end_str}"
               f"&$orderby=start/dateTime&$top=50"
               f"&$select=subject,start,end,location,organizer,attendees,isAllDay,showAs")

        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
            'Prefer': 'outlook.timezone="Central Standard Time"'
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result.get('value', [])
        except urllib.error.HTTPError as e:
            print(f"Graph API error for {user_email}: {e.code} - {e.read().decode()[:200]}")
            return []

    def get_users(self, filter_str: str = None) -> List[Dict]:
        """Get users from Azure AD"""
        self._ensure_token()

        url = f"{self.graph_url}/users?$top=100&$select=id,displayName,mail,jobTitle,department"
        if filter_str:
            url += f"&$filter={urllib.parse.quote(filter_str)}"

        req = urllib.request.Request(url, headers={
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json'
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result.get('value', [])
        except urllib.error.HTTPError as e:
            print(f"Graph API users error: {e.code}")
            return []

    def get_presence(self, user_ids: List[str]) -> Dict[str, str]:
        """Get presence/availability for users"""
        self._ensure_token()

        # Presence API requires POST with user IDs
        url = f"{self.graph_url}/communications/getPresencesByUserId"
        body = json.dumps({'ids': user_ids}).encode()

        req = urllib.request.Request(url, data=body, headers={
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json'
        })

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                presence_map = {}
                for p in result.get('value', []):
                    presence_map[p.get('id')] = p.get('availability', 'Unknown')
                return presence_map
        except urllib.error.HTTPError as e:
            print(f"Graph API presence error: {e.code}")
            return {}


# ============================================
# INTERNAL SQL SERVER CLIENT (AQFDB6, DB7, CI)
# ============================================
class InternalDBClient:
    """Client for querying internal SQL Server databases (AQFDB6, AQFDB7, CI, AQFAM1)

    Requires pyodbc: pip install pyodbc
    Uses SQL Auth with per-database credentials.

    Known databases:
        AQFDB6  - Production notes, EOP data, yield, cycle count, on-time start
        AQFDB7  - Manning/headcount, labor target vs actual
        AQFAM1  - Production supply costs (some overlap with Sage)
        CI      - Quality: FTQ, COQ, foreign matter, overall quality, overdue releases
    """

    def __init__(self):
        # Database configs: server, database name, credentials
        # CI database lives on the AQFDB6 server (schema: db_accessadmin)
        # MANUFACTURING database also on AQFDB6 server
        self.db_configs = {
            'db6': {
                'server': 'AQFDB6',
                'database': 'AQFDB6',
                'uid': 'SocialScaleReadOnly',
                'pwd': 'socialscale.25',
            },
            'manufacturing': {
                'server': 'AQFDB6',
                'database': 'MANUFACTURING',
                'uid': 'SocialScaleReadOnly',
                'pwd': 'socialscale.25',
            },
            'ci': {
                'server': 'AQFDB6',
                'database': 'CI',
                'uid': 'SocialScaleReadOnly',
                'pwd': 'socialscale.25',
            },
            'db7': {
                'server': 'AQFDB7\\KRONWFC',
                'database': 'MANNINGS',
                'uid': 'SocialScaleReadOnly',
                'pwd': 'socialscale.25',
            },
            'mannings': {
                'server': 'AQFDB7\\KRONWFC',
                'database': 'MANNINGS',
                'uid': 'SocialScaleReadOnly',
                'pwd': 'socialscale.25',
            },
            'am1': {
                'server': 'AQFAM1\\AMMS',
                'database': 'AMMS',
                'uid': 'AMMSro',
                'pwd': 'V1s3-Gr1p',
            },
            'amms': {
                'server': 'AQFAM1\\AMMS',
                'database': 'AMMS',
                'uid': 'AMMSro',
                'pwd': 'V1s3-Gr1p',
            },
        }
        # Legacy accessor for backward compat
        self.databases = {k: v['database'] for k, v in self.db_configs.items()}
        self._available = False

        # Try to import pyodbc
        try:
            import pyodbc
            self._pyodbc = pyodbc
            self._available = True
        except ImportError:
            self._pyodbc = None
            print("pyodbc not installed. Run: pip install pyodbc")
            print("Internal DB queries (AQFDB6/DB7/CI) will not be available.")

    def _build_conn_string(self, config):
        """Build connection string with SQL Auth."""
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config['server']};"
            f"DATABASE={config['database']};"
            f"UID={config['uid']};"
            f"PWD={config['pwd']};"
            f"Connection Timeout=30;"
            f"TrustServerCertificate=yes;"
        )

    def query(self, sql: str, database: str = 'db6') -> List[Dict[str, Any]]:
        """Execute SQL query against an internal database

        Args:
            sql: SQL query string (use parameterized queries for user input)
            database: Key from self.db_configs ('db6', 'db7', 'am1', 'ci')
        """
        if not self._available:
            raise RuntimeError("pyodbc not installed - internal DB queries unavailable")

        config = self.db_configs.get(database)
        if not config:
            raise ValueError(f"Unknown database key '{database}'. Valid: {list(self.db_configs.keys())}")

        conn_str = self._build_conn_string(config)

        try:
            conn = self._pyodbc.connect(conn_str, timeout=30)
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return [self._sanitize_row(dict(zip(columns, row))) for row in rows]
        except Exception as e:
            raise RuntimeError(f"Internal DB query error ({config['database']}): {e}")

    @staticmethod
    def _sanitize_row(row: dict) -> dict:
        """Convert non-JSON-serializable types (date, time, Decimal) to strings/floats."""
        import decimal
        for k, v in row.items():
            if isinstance(v, (datetime,)):
                row[k] = v.isoformat()
            elif hasattr(v, 'isoformat'):  # date, time
                row[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                row[k] = float(v)
            elif isinstance(v, bytes):
                row[k] = v.hex()
        return row

    def test_connection(self, database: str = 'db6') -> dict:
        """Test connectivity to a specific database. Returns status dict."""
        if not self._available:
            return {'status': 'unavailable', 'error': 'pyodbc not installed'}

        config = self.db_configs.get(database)
        if not config:
            return {'status': 'error', 'error': f'Unknown database key: {database}'}

        try:
            conn_str = self._build_conn_string(config)
            conn = self._pyodbc.connect(conn_str, timeout=15)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 AS test")
            cursor.fetchone()
            conn.close()
            return {'status': 'connected', 'server': config['server'], 'database': config['database']}
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    def test_all(self) -> dict:
        """Test connectivity to all configured databases."""
        results = {}
        for key in self.db_configs:
            results[key] = self.test_connection(key)
        return results


# Initialize clients
sage_client = SageX3Client()
snowflake_client = SnowflakeClient()
graph_client = MicrosoftGraphClient()
internal_db = InternalDBClient()

# ============================================
# SNOWFLAKE QUERIES (Redzone/Operations)
# ============================================
SNOWFLAKE_QUERIES = {
    'plant_oee': """
        SELECT
            ROUND(AVG("oee"), 1) AS plant_oee,
            ROUND(AVG("performance"), 1) AS plant_performance,
            ROUND(AVG("quality"), 1) AS plant_quality,
            ROUND(AVG("availability"), 1) AS plant_availability,
            SUM("outCount") AS total_output,
            ROUND(SUM("downSeconds")/3600, 1) AS total_downtime_hours,
            ROUND(SUM("manHours"), 1) AS total_manhours,
            COUNT(DISTINCT "locationName") AS lines_reporting
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "oee" > 0
    """,

    'oee_by_line': """
        SELECT
            "locationName" AS line_name,
            "areaName" AS area,
            ROUND(AVG("oee"), 1) AS avg_oee,
            ROUND(AVG("performance"), 1) AS avg_performance,
            ROUND(AVG("quality"), 1) AS avg_quality,
            ROUND(AVG("availability"), 1) AS avg_availability,
            SUM("outCount") AS total_output,
            ROUND(SUM("downSeconds")/3600, 1) AS downtime_hours,
            ROUND(SUM("manHours"), 1) AS total_manhours
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "oee" > 0
        GROUP BY "locationName", "areaName"
        ORDER BY avg_oee DESC
    """,

    'lines_below_target': """
        SELECT
            "locationName" AS line_name,
            "areaName" AS area,
            ROUND(AVG("oee"), 1) AS avg_oee,
            ROUND(SUM("downSeconds")/3600, 1) AS downtime_hours,
            'OEE Below 70%' AS flag_reason
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "oee" > 0
        GROUP BY "locationName", "areaName"
        HAVING AVG("oee") < 70
        ORDER BY avg_oee ASC
    """,

    'top_downtime': """
        SELECT
            "problemTypeName" AS reason,
            "problemGroupName" AS category,
            "problemPlanned" AS planned,
            COUNT(*) AS occurrences,
            ROUND(SUM("hoursLost"), 2) AS total_hours_lost
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
        WHERE "startTime" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
        GROUP BY "problemTypeName", "problemGroupName", "problemPlanned"
        ORDER BY total_hours_lost DESC
        LIMIT 10
    """,

    'labor_productivity': """
        SELECT
            "locationName" AS line,
            "areaName" AS area,
            ROUND(SUM("manHours"), 1) AS total_manhours,
            SUM("outCount") AS total_output,
            ROUND(SUM("outCount") / NULLIF(SUM("manHours"), 0), 1) AS units_per_manhour
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "manHours" > 0
        GROUP BY "locationName", "areaName"
        ORDER BY units_per_manhour DESC
    """,

    'hourly_trend': """
        SELECT
            "dateTimeNearestHour" AS hour,
            ROUND(AVG("oee"), 1) AS avg_oee,
            SUM("outCount") AS total_output,
            COUNT(DISTINCT "locationName") AS active_lines
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(hour, -12, CURRENT_TIMESTAMP())
          AND "oee" > 0
        GROUP BY "dateTimeNearestHour"
        ORDER BY "dateTimeNearestHour" DESC
    """,

    'active_lines': """
        SELECT
            "locationName" AS line_name,
            "areaName" AS area,
            "productTypeName" AS current_product,
            "oee" AS current_oee,
            "outCount" AS hourly_output
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(hour, -2, CURRENT_TIMESTAMP())
          AND "outCount" > 0
        ORDER BY "dateTimeNearestHour" DESC, "locationName"
    """,

    'labor_summary': """
        SELECT
            COUNT(DISTINCT "userId") AS active_workers,
            ROUND(SUM("manHours"), 1) AS total_manhours,
            ROUND(SUM("outCount") / NULLIF(SUM("manHours"), 0), 1) AS units_per_manhour,
            COUNT(DISTINCT "locationName") AS lines_staffed
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "manHours" > 0
    """,

    'quality_summary': """
        SELECT
            ROUND(AVG("quality"), 1) AS avg_quality,
            ROUND(AVG("performance"), 1) AS avg_performance,
            SUM("outCount") AS total_output,
            SUM("defectCount") AS total_defects
        FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
        WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
          AND "oee" > 0
    """
}

# ============================================
# SQL SERVER QUERIES (Sage X3/Financial)
# ============================================
SQL_QUERIES = {
    'daily_revenue': """
        SELECT SUM(AMTATI_0) as DailyRevenue
        FROM AMQ.SINVOICE
        WHERE CAST(ACCDAT_0 AS DATE) = CAST(GETDATE() AS DATE)
          AND STA_0 = 3
          AND SIVTYP_0 = 'INV'
    """,

    'mtd_revenue': """
        SELECT SUM(AMTATI_0) as MTDRevenue
        FROM AMQ.SINVOICE
        WHERE ACCDAT_0 >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
          AND ACCDAT_0 < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
          AND STA_0 = 3
          AND SIVTYP_0 = 'INV'
    """,

    'ytd_revenue': """
        SELECT SUM(AMTATI_0) as YTDRevenue
        FROM AMQ.SINVOICE
        WHERE ACCDAT_0 >= DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()), 0)
          AND ACCDAT_0 < DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()) + 1, 0)
          AND STA_0 = 3
          AND SIVTYP_0 = 'INV'
    """,

    'inventory_by_facility': """
        SELECT STOFCY_0 as Facility, COUNT(*) as LineCount, SUM(QTYSTU_0) as TotalQty
        FROM AMQ.STOCK
        WHERE STA_0 = 'A'
        GROUP BY STOFCY_0
    """,

    'inventory_value': """
        SELECT
            s.STOFCY_0 as Facility,
            COUNT(*) as LineCount,
            SUM(s.QTYSTU_0) as TotalQty,
            SUM(s.QTYSTU_0 * c.CSTTOT_0) as TotalValue
        FROM AMQ.STOCK s
        INNER JOIN AMQ.ITMCOST c
            ON s.ITMREF_0 = c.ITMREF_0
            AND s.STOFCY_0 = c.STOFCY_0
        WHERE s.STA_0 = 'A'
            AND c.YEA_0 = YEAR(GETDATE())
        GROUP BY s.STOFCY_0
    """,

    'inventory_by_status': """
        SELECT STA_0 as Status, COUNT(*) as LineCount, SUM(QTYSTU_0) as TotalQty
        FROM AMQ.STOCK
        GROUP BY STA_0
    """,

    'finished_goods_value': """
        SELECT SUM(s.QTYSTU_0 * c.CSTTOT_0) as FinishedGoodsValue
        FROM AMQ.STOCK s
        INNER JOIN AMQ.ITMCOST c ON s.ITMREF_0 = c.ITMREF_0 AND s.STOFCY_0 = c.STOFCY_0
        INNER JOIN AMQ.ITMMASTER m ON s.ITMREF_0 = m.ITMREF_0
        WHERE s.STA_0 = 'A' AND c.YEA_0 = YEAR(GETDATE()) AND m.TCLCOD_0 = 'FG'
    """,

    'ar_aging': """
        SELECT
            COUNT(*) as InvoiceCount,
            SUM(AMTATI_0) as TotalAR,
            SUM(CASE WHEN DATEDIFF(day, STRDUDDAT_0, GETDATE()) <= 30 THEN AMTATI_0 ELSE 0 END) as Current30,
            SUM(CASE WHEN DATEDIFF(day, STRDUDDAT_0, GETDATE()) BETWEEN 31 AND 60 THEN AMTATI_0 ELSE 0 END) as Days31to60,
            SUM(CASE WHEN DATEDIFF(day, STRDUDDAT_0, GETDATE()) BETWEEN 61 AND 90 THEN AMTATI_0 ELSE 0 END) as Days61to90,
            SUM(CASE WHEN DATEDIFF(day, STRDUDDAT_0, GETDATE()) > 90 THEN AMTATI_0 ELSE 0 END) as Over90
        FROM AMQ.SINVOICE
        WHERE STA_0 = 3 AND SIVTYP_0 = 'INV' AND STRDUDDAT_0 < GETDATE()
    """,

    'top_customers': """
        SELECT TOP 10 BPR_0 as CustomerCode, BPRNAM_0 as CustomerName, SUM(AMTATI_0) as TotalRevenue
        FROM AMQ.SINVOICE
        WHERE ACCDAT_0 >= DATEADD(MONTH, -1, GETDATE())
          AND STA_0 = 3
        GROUP BY BPR_0, BPRNAM_0
        ORDER BY TotalRevenue DESC
    """,

    'gross_margin_mtd': """
        SELECT
            SUM(d.AMTATILIN_0) as LineRevenue,
            SUM(d.QTY_0 * d.CPRPRI_0) as LineCost
        FROM AMQ.SINVOICED d
        INNER JOIN AMQ.SINVOICE i ON d.NUM_0 = i.NUM_0
        WHERE i.ACCDAT_0 >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
          AND i.STA_0 = 3
          AND i.SIVTYP_0 = 'INV'
    """,

    'cogs_ytd': """
        SELECT
            SUM(d.QTY_0 * d.CPRPRI_0) as COGS_YTD
        FROM AMQ.SINVOICED d
        INNER JOIN AMQ.SINVOICE i ON d.NUM_0 = i.NUM_0
        WHERE i.ACCDAT_0 >= DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()), 0)
          AND i.ACCDAT_0 < DATEADD(YEAR, DATEDIFF(YEAR, 0, GETDATE()) + 1, 0)
          AND i.STA_0 = 3
          AND i.SIVTYP_0 = 'INV'
    """,

    'cash_position': """
        SELECT
            SUM(DEB_0 + DEB_1 + DEB_2 + DEB_3 + DEB_4 + DEB_5 + DEB_6 + DEB_7 + DEB_8 + DEB_9 + DEB_10 + DEB_11 + DEB_12)
            - SUM(CDT_0 + CDT_1 + CDT_2 + CDT_3 + CDT_4 + CDT_5 + CDT_6 + CDT_7 + CDT_8 + CDT_9 + CDT_10 + CDT_11 + CDT_12) as CashBalance
        FROM AMQ.BALANCE
        WHERE ACC_0 IN ('1000','1010','1011','1015')
    """,

    'ebitda_mtd': """
        SELECT
            -- Revenue (4xxx accounts - credit balances) - current fiscal year only
            (SELECT SUM(CDT_1 - DEB_1) FROM AMQ.BALANCE WHERE ACC_0 LIKE '4%' AND FIY_0 = 23) as Revenue,
            -- COGS (5xxx accounts - debit balances)
            (SELECT SUM(DEB_1 - CDT_1) FROM AMQ.BALANCE WHERE ACC_0 LIKE '5%' AND FIY_0 = 23) as COGS,
            -- Operating Expenses (6xxx accounts - debit balances)
            (SELECT SUM(DEB_1 - CDT_1) FROM AMQ.BALANCE WHERE ACC_0 LIKE '6%' AND FIY_0 = 23) as OpEx,
            -- Depreciation (6050-6073 - already in OpEx, will add back)
            (SELECT SUM(DEB_1 - CDT_1) FROM AMQ.BALANCE WHERE FIY_0 = 23 AND ACC_0 IN
                ('6050','6052','6053','6055','6056','6057','6058','6059','6060',
                 '6064','6065','6066','6067','6068','6069','6070','6071','6072','6073')) as Depreciation,
            -- Amortization (7150)
            (SELECT SUM(DEB_1 - CDT_1) FROM AMQ.BALANCE WHERE ACC_0 = '7150' AND FIY_0 = 23) as Amortization,
            -- Interest (71xx except 7150 and 7200)
            (SELECT SUM(DEB_1 - CDT_1) FROM AMQ.BALANCE
             WHERE ACC_0 LIKE '71%' AND ACC_0 NOT IN ('7150','7200','7205') AND FIY_0 = 23) as Interest
    """
}

# ============================================
# DEPARTMENTAL KPI QUERIES (Internal SQL Server)
# ============================================
# These queries are stubbed based on spreadsheet analysis (Feb 2026).
# Table/column names are best guesses from the pivot table structures
# and need to be confirmed with Nick once AQFDB6/DB7/CI access is granted.
#
# Spreadsheet sources analyzed:
#   - Production Sub KPI Dashboard.xlsx (31 sheets)
#   - Quality Sub KPI Dashboard.xlsx
#
# Each query includes:
#   - database: which InternalDBClient database key to use
#   - sql: the query (table/column names TBD - marked with TODO)
#   - notes: what the spreadsheet does and how to replicate it

DEPT_KPI_QUERIES = {

    # ══════════════════════════════════════════════════════════════════
    # PRODUCTION KPIs
    # Confirmed columns from kpi_table_discovery.json (Mar 10, 2026)
    # ══════════════════════════════════════════════════════════════════

    'prod_schedule_attainment': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'Attainment % with 95% CAL. Attainment = (prodQty1st+prodQty2nd)/targetVal. Source: MANUFACTURING.PROD.eopShiftNotes',
        'sql': """
            SELECT
                YEAR(prodDate) AS yr,
                MONTH(prodDate) AS mo,
                SUM(prodQty1st + prodQty2nd) AS total_produced,
                SUM(targetVal) AS total_target,
                CASE WHEN SUM(targetVal) > 0
                     THEN ROUND(CAST(SUM(prodQty1st + prodQty2nd) AS FLOAT) / SUM(targetVal), 4)
                     ELSE 0 END AS attainment_pct,
                0.95 AS target
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND targetVal > 0
            GROUP BY YEAR(prodDate), MONTH(prodDate)
            ORDER BY yr DESC, mo DESC
        """
    },

    'prod_ontime_startup': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'On-Time Start % with 47% CAL. onTimeStart is 0/1 flag. Source: MANUFACTURING.PROD.eopShiftNotes',
        'sql': """
            SELECT
                YEAR(prodDate) AS yr,
                MONTH(prodDate) AS mo,
                SUM(CAST(onTimeStart AS INT)) AS ontime_count,
                COUNT(*) AS total_shifts,
                ROUND(CAST(SUM(CAST(onTimeStart AS INT)) AS FLOAT) / NULLIF(COUNT(*), 0), 4) AS ontime_pct,
                0.47 AS corrective_action_limit
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
            GROUP BY YEAR(prodDate), MONTH(prodDate)
            ORDER BY yr DESC, mo DESC
        """
    },

    'prod_ingredient_yield': {
        'database': 'ci',
        'department': 'Production',
        'notes': 'Ingredient Yields from KPIDashData. Columns: Site, KPILevel, Focus, Date, KPI, Type, Value. Filter Focus for yield KPIs.',
        'sql': """
            SELECT
                YEAR([Date]) AS yr,
                MONTH([Date]) AS mo,
                KPI,
                Value,
                Site,
                Focus,
                Type
            FROM db_accessadmin.KPIDashData
            WHERE [Date] >= DATEADD(month, -3, GETDATE())
              AND Focus = 'Cost'
              AND KPI LIKE '%Yield%'
            ORDER BY [Date] DESC
        """
    },

    'prod_material_tracking': {
        'database': 'ci',
        'department': 'Production',
        'notes': 'Material tracking variance by contract/type. Columns: sunDate, contract, prodType, qtyReqd, qtyActual, varPct, varDolwScrap',
        'sql': """
            SELECT
                sunDate,
                contract,
                prodType,
                qtyReqd,
                qtyReqdwScrap,
                qtyActual,
                varPct,
                varPctwScrap,
                varDolwScrap
            FROM db_accessadmin.KPI_MFG_MaterialTrackingbyContract
            WHERE sunDate >= DATEADD(month, -3, GETDATE())
            ORDER BY sunDate DESC, contract, prodType
        """
    },

    'prod_critical_defect_rate': {
        'database': 'snowflake',
        'department': 'Production',
        'notes': 'Critical Defect Rate from Redzone. Source: Snowflake v_completeddataitem',
        'sql': """
            SELECT
                DATE_TRUNC('month', "dateTimeNearestHour") AS month,
                "locationName" AS line_name,
                SUM("defectCount") AS total_defects,
                SUM("outCount") AS total_output,
                ROUND(SUM("defectCount") / NULLIF(SUM("outCount"), 0), 6) AS defect_rate
            FROM ZGRZDCXCHH_DB."ameriqual-org"."v_completeddataitem"
            WHERE "dateTimeNearestHour" >= DATEADD(month, -3, CURRENT_TIMESTAMP())
              AND "outCount" > 0
              AND "void" = 'False'
            GROUP BY DATE_TRUNC('month', "dateTimeNearestHour"), "locationName"
            ORDER BY month DESC, defect_rate DESC
        """
    },

    'prod_cycle_count_accuracy': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'Cycle Count Accuracy % with 30% CAL. Source: K: drive (manual)',
        'sql': None  # Manual data from K:\Engineering\MAINTENANCE PM FOLDER\KPIs
    },

    'prod_supply_cost': {
        'database': 'amms',
        'department': 'Production',
        'notes': 'Production Supply Cost. Columns: YEARNUM(int), WEEKNUM(int), VENDNAME(char35), PARTNAME(char50), GLCOST(numeric). 5,357 rows.',
        'sql': """
            SELECT
                YEARNUM,
                WEEKNUM,
                RTRIM(VENDNAME) AS VENDNAME,
                RTRIM(PARTNAME) AS PARTNAME,
                GLCOST
            FROM view_kpi_glcost
            WHERE YEARNUM >= YEAR(GETDATE())
            ORDER BY YEARNUM DESC, WEEKNUM DESC
        """
    },

    'prod_labor_target_vs_actual': {
        'database': 'ci',
        'department': 'Production',
        'notes': 'Labor target vs actual. Columns: site, prodDate, shift, location, train, target, actual. Filter location for Production areas.',
        'sql': """
            SELECT
                prodDate,
                location,
                shift,
                train,
                target,
                CAST(LTRIM(RTRIM(actual)) AS INT) AS actual_val,
                CASE WHEN target > 0
                     THEN ROUND(CAST(LTRIM(RTRIM(actual)) AS FLOAT) / target, 4)
                     ELSE 0 END AS pct_of_target
            FROM db_accessadmin.KPI_SCHED_targetVSactual
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND location NOT LIKE '%Warehouse%'
              AND location NOT LIKE '%Retort%'
              AND location NOT LIKE '%QA%'
            ORDER BY prodDate DESC
        """
    },

    'prod_human_errors': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'Human Errors + DT Events. Columns: humanError (count), dtEvents (count). Source: MANUFACTURING.PROD.eopShiftNotes',
        'sql': """
            SELECT
                YEAR(prodDate) AS yr,
                MONTH(prodDate) AS mo,
                SUM(humanError) AS total_human_errors,
                SUM(dtEvents) AS total_dt_events,
                COUNT(DISTINCT prodDate) AS days_tracked
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
            GROUP BY YEAR(prodDate), MONTH(prodDate)
            ORDER BY yr DESC, mo DESC
        """
    },

    'prod_major_unplanned_downtime': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'Lines with downtime events. Source: MANUFACTURING.PROD.eopShiftNotes',
        'sql': """
            SELECT
                YEAR(prodDate) AS yr,
                MONTH(prodDate) AS mo,
                SUM(dtEvents) AS total_dt_events,
                COUNT(DISTINCT prodDate) AS days_with_events,
                COUNT(DISTINCT line) AS lines_affected
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND dtEvents > 0
            GROUP BY YEAR(prodDate), MONTH(prodDate)
            ORDER BY yr DESC, mo DESC
        """
    },

    'prod_eop_detail': {
        'database': 'manufacturing',
        'department': 'Production',
        'notes': 'Recent EOP shift notes detail. All confirmed columns from PROD.eopShiftNotes.',
        'sql': """
            SELECT TOP 50
                prodDate, line, valueStream, product, prodDescr, customer,
                targetVal, theoLineRate, begTime, endTime, onTimeStart,
                prodQty1st, prodQty2nd, humanError, dtEvents,
                humanErrorReason, dtEventsReason, duration
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(day, -7, GETDATE())
            ORDER BY prodDate DESC, line
        """
    },

    # ══════════════════════════════════════════════════════════════════
    # QUALITY KPIs
    # Confirmed columns from kpi_table_discovery.json (Mar 10, 2026)
    # ══════════════════════════════════════════════════════════════════

    'qual_overall_quality': {
        'database': 'ci',
        'department': 'Quality',
        'notes': '% acceptable pallets. Columns: KPI, dateVal, cont, badPallets, badEaches, prodPallets, prodEaches. Table: KPI_QA_OverallQuality_Contract',
        'sql': """
            SELECT
                YEAR(dateVal) AS yr,
                MONTH(dateVal) AS mo,
                cont,
                SUM(prodPallets) AS total_pallets,
                SUM(badPallets) AS total_bad_pallets,
                SUM(prodEaches) AS total_eaches,
                SUM(badEaches) AS total_bad_eaches,
                CASE WHEN SUM(prodPallets) > 0
                     THEN ROUND(1.0 - CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets), 4)
                     ELSE 0 END AS quality_pct
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE dateVal >= DATEADD(month, -3, GETDATE())
            GROUP BY YEAR(dateVal), MONTH(dateVal), cont
            ORDER BY yr DESC, mo DESC
        """
    },

    'qual_first_time_quality': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'FTQ from KPI_QA_CalcWeekly. Columns: weekVal, groupVal, valueStream, descr, numVal. Filter groupVal=FTQ.',
        'sql': """
            SELECT
                weekVal,
                groupVal,
                valueStream,
                descr,
                numVal
            FROM db_accessadmin.KPI_QA_CalcWeekly
            WHERE weekVal >= DATEADD(month, -3, GETDATE())
              AND groupVal = 'FTQ'
            ORDER BY weekVal DESC
        """
    },

    'qual_overdue_releases': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'Overdue lots. Columns: dateVal, cont, item, lot, pallets, units, overdueMult, QttlCost, dailyCount',
        'sql': """
            SELECT
                dateVal,
                cont,
                item,
                lot,
                pallets,
                units,
                overdueMult,
                QttlCost,
                dailyCount
            FROM db_accessadmin.KPI_QA_OverdueReleases
            WHERE dateVal >= DATEADD(month, -1, GETDATE())
            ORDER BY dateVal DESC
        """
    },

    'qual_foreign_matter': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'Foreign matter SSOPs. CAL = 10/month. Columns: ssopNum, dateEntered, dateOccur, item, descr, contaminate, source',
        'sql': """
            SELECT
                YEAR(dateOccur) AS yr,
                MONTH(dateOccur) AS mo,
                COUNT(*) AS incident_count,
                10 AS corrective_action_limit,
                SUM(CASE WHEN contaminate LIKE '%METAL%' THEN 1 ELSE 0 END) AS metal,
                SUM(CASE WHEN contaminate LIKE '%GASKET%' THEN 1 ELSE 0 END) AS gasket,
                SUM(CASE WHEN contaminate LIKE '%PLASTIC%' THEN 1 ELSE 0 END) AS plastic,
                SUM(CASE WHEN contaminate LIKE '%GLOVE%' THEN 1 ELSE 0 END) AS glove,
                SUM(CASE WHEN contaminate LIKE '%TAPE%' THEN 1 ELSE 0 END) AS tape
            FROM db_accessadmin.KPI_QA_ForeignMatter
            WHERE dateOccur >= DATEADD(month, -6, GETDATE())
            GROUP BY YEAR(dateOccur), MONTH(dateOccur)
            ORDER BY yr DESC, mo DESC
        """
    },

    'qual_rework_log': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'Rework quality issues. Columns: KPI, dateVal, cont, item, lot, issueQtyPal, issueQtyEa, prodQtyPal, prodQtyEa, issue',
        'sql': """
            SELECT
                YEAR(dateVal) AS yr,
                MONTH(dateVal) AS mo,
                cont,
                COUNT(*) AS rework_count,
                SUM(issueQtyPal) AS total_issue_pallets,
                SUM(issueQtyEa) AS total_issue_eaches
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            WHERE dateVal >= DATEADD(month, -3, GETDATE())
            GROUP BY YEAR(dateVal), MONTH(dateVal), cont
            ORDER BY yr DESC, mo DESC
        """
    },

    'qual_labor_target_vs_actual': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'QA Labor target vs actual. Filter location for QA areas.',
        'sql': """
            SELECT
                prodDate,
                location,
                shift,
                target,
                CAST(LTRIM(RTRIM(actual)) AS INT) AS actual_val
            FROM db_accessadmin.KPI_SCHED_targetVSactual
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND location LIKE '%QA%'
            ORDER BY prodDate DESC
        """
    },

    'qual_cost_of_quality': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'COQ: manual (emailed by Brandon Johnson). THPQualityCOQ table exists but may be outdated.',
        'sql': None  # Manual data — not reliably in SQL
    },

    'qual_recleans': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'Re-cleans by equipment type. Data in SharePoint.',
        'sql': None  # SharePoint data — manual
    },

    'qual_mre_failure_rate': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'MRE USDA inspection failure rate. Total pouches submitted vs failures. Simple ratio per contract period. Source: KPI_QA_OverallQuality_Contract where cont=MRE',
        'sql': """
            SELECT
                YEAR(dateVal) AS yr,
                MONTH(dateVal) AS mo,
                SUM(badPallets) AS failed_pallets,
                SUM(prodPallets) AS total_pallets,
                SUM(badEaches) AS failed_eaches,
                SUM(prodEaches) AS total_eaches,
                CASE WHEN SUM(prodPallets) > 0
                     THEN ROUND(CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets) * 100, 2)
                     ELSE 0 END AS failure_rate_pct
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE cont = 'MRE'
            GROUP BY YEAR(dateVal), MONTH(dateVal)
            ORDER BY yr DESC, mo DESC
        """
    },

    'qual_internal_qa_failures': {
        'database': 'ci',
        'department': 'Quality',
        'notes': 'Internal QA failures before USDA grading. From KPI_QA_OverallQuality_Contract, all contracts.',
        'sql': """
            SELECT
                YEAR(dateVal) AS yr,
                MONTH(dateVal) AS mo,
                cont,
                SUM(badPallets) AS failed_pallets,
                SUM(prodPallets) AS total_pallets,
                SUM(badEaches) AS failed_eaches,
                SUM(prodEaches) AS total_eaches,
                CASE WHEN SUM(prodPallets) > 0
                     THEN ROUND(CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets) * 100, 2)
                     ELSE 0 END AS failure_rate_pct
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE dateVal >= DATEADD(month, -6, GETDATE())
            GROUP BY YEAR(dateVal), MONTH(dateVal), cont
            ORDER BY yr DESC, mo DESC, cont
        """
    },

    # ══════════════════════════════════════════════════════════════════
    # SAFETY KPIs
    # Confirmed: KPI_CostByAccount + SAFETYIncidentDatabase in CI DB
    # ══════════════════════════════════════════════════════════════════

    'safety_supply_cost': {
        'database': 'ci',
        'department': 'Safety',
        'notes': 'Safety Supply Cost, GL 6310. Columns: sunDate, site, account, descr, dolVal',
        'sql': """
            SELECT
                sunDate,
                site,
                account,
                descr,
                dolVal,
                timestamp
            FROM db_accessadmin.KPI_CostByAccount
            WHERE account = '6310'
              AND sunDate >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)
            ORDER BY sunDate DESC
        """
    },

    'safety_incidents': {
        'database': 'ci',
        'department': 'Safety',
        'notes': 'Safety incident data from SAFETYIncidentDatabase table in CI. Column names unconfirmed — discovery script missed it.',
        'sql': """
            SELECT TOP 100 *
            FROM db_accessadmin.SAFETYIncidentDatabase
            ORDER BY 1 DESC
        """
    },

    'safety_kpi_dashboard': {
        'database': 'ci',
        'department': 'Safety',
        'notes': 'Safety KPIs from KPIDashData. Filter Focus=Safety for ORIR, TIR, etc.',
        'sql': """
            SELECT
                [Date],
                KPI,
                Value,
                Type,
                Site
            FROM db_accessadmin.KPIDashData
            WHERE Focus = 'Safety'
              AND [Date] >= DATEADD(month, -6, GETDATE())
            ORDER BY [Date] DESC
        """
    },

    # Additional safety KPIs from ProcessMAP are manual exports

    # ══════════════════════════════════════════════════════════════════
    # WAREHOUSE KPIs
    # Confirmed columns from kpi_table_discovery.json (Mar 10, 2026)
    # NOTE: Table is KPI_WH_TransactionCounts (plural!)
    # ══════════════════════════════════════════════════════════════════

    'wh_trucks_received_shipped': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'Trucks Received/Shipped. Columns: sunDate, site, transType (SHIP/RECV), transCount, tempType (DRY/FRZ)',
        'sql': """
            SELECT
                sunDate,
                site,
                transType,
                SUM(transCount) AS total_count,
                tempType
            FROM db_accessadmin.KPI_WH_TransactionCounts
            WHERE sunDate >= DATEADD(month, -3, GETDATE())
              AND transType IN ('SHIP', 'RECV')
            GROUP BY sunDate, site, transType, tempType
            ORDER BY sunDate DESC
        """
    },

    'wh_pallet_moves_per_manhour': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'Pallet moves from KPI_WH_TransactionCounts. transType for pallet-related moves.',
        'sql': """
            SELECT
                sunDate,
                site,
                transType,
                SUM(transCount) AS total_count
            FROM db_accessadmin.KPI_WH_TransactionCounts
            WHERE sunDate >= DATEADD(month, -3, GETDATE())
            GROUP BY sunDate, site, transType
            ORDER BY sunDate DESC
        """
    },

    'wh_ontime_delivery': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'On-Time Delivery. Columns: site, begDate, endDate, item, descr, shipStatus, delLines, qtyLBS, qtyEA, salesValue',
        'sql': """
            SELECT
                begDate,
                endDate,
                site,
                shipStatus,
                COUNT(*) AS line_count,
                SUM(delLines) AS total_del_lines,
                SUM(qtyEA) AS total_qty_ea,
                SUM(salesValue) AS total_sales_value
            FROM db_accessadmin.KPI_WH_ShipVsCustReq
            WHERE begDate >= DATEADD(month, -3, GETDATE())
            GROUP BY begDate, endDate, site, shipStatus
            ORDER BY begDate DESC
        """
    },

    'wh_cycle_count': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'Cycle Count accuracy. Columns: site, begDate, endDate, countGrouping, countType, scsCount, locCount, lineCount, variances, accuracy',
        'sql': """
            SELECT
                begDate,
                endDate,
                site,
                countGrouping,
                countType,
                scsCount,
                locCount,
                lineCount,
                variances,
                accuracy
            FROM db_accessadmin.KPI_WH_CycleCount
            WHERE begDate >= DATEADD(month, -3, GETDATE())
            ORDER BY begDate DESC
        """
    },

    'wh_labor_target_vs_actual': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'Warehouse Labor target vs actual. Filter location for Warehouse areas.',
        'sql': """
            SELECT
                prodDate,
                location,
                shift,
                target,
                CAST(LTRIM(RTRIM(actual)) AS INT) AS actual_val
            FROM db_accessadmin.KPI_SCHED_targetVSactual
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND location LIKE '%Warehouse%'
            ORDER BY prodDate DESC
        """
    },

    'wh_repair_cost': {
        'database': 'amms',
        'department': 'Warehouse',
        'notes': 'Landfill & Repair costs. Columns: YEARNUM(int), WEEKNUM(int), VENDNAME(char35), PARTNAME(char50), GLCOST(numeric). 147 rows.',
        'sql': """
            SELECT
                YEARNUM,
                WEEKNUM,
                RTRIM(VENDNAME) AS VENDNAME,
                RTRIM(PARTNAME) AS PARTNAME,
                GLCOST
            FROM view_kpi_repaircost
            WHERE YEARNUM >= YEAR(GETDATE())
            ORDER BY YEARNUM DESC, WEEKNUM DESC
        """
    },

    'wh_freezer_capacity': {
        'database': 'ci',
        'department': 'Warehouse',
        'notes': 'Freezer Capacity. Columns: site, location (ECS/FRZ), palletCount, capacity, dateVal',
        'sql': """
            SELECT
                dateVal,
                site,
                location,
                palletCount,
                capacity
            FROM db_accessadmin.KPI_WH_Capacity
            WHERE dateVal >= DATEADD(month, -3, GETDATE())
            ORDER BY dateVal DESC
        """
    },

    # ══════════════════════════════════════════════════════════════════
    # RETORT KPIs
    # Confirmed: KPI_SCHED_targetVSactual for labor + RETORT* tables in CI
    # ══════════════════════════════════════════════════════════════════

    'retort_labor_target_vs_actual': {
        'database': 'ci',
        'department': 'Retort',
        'notes': 'Retort Labor target vs actual. Filter location for Retort areas.',
        'sql': """
            SELECT
                prodDate,
                location,
                shift,
                target,
                CAST(LTRIM(RTRIM(actual)) AS INT) AS actual_val
            FROM db_accessadmin.KPI_SCHED_targetVSactual
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
              AND location LIKE '%Retort%'
            ORDER BY prodDate DESC
        """
    },

    # Retort KPIs from Access DB (S:\RetortDev\Database\2026 Process Deviation.accdb):
    # - Deviation Rate, Human Errors, OTLs, Deviations/Million Pouches
    # These need the retort data_fetcher pipeline, not SQL Server

    'retort_daily_cycles': {
        'database': 'mannings',
        'department': 'Retort',
        'notes': 'Daily completed retort cycles from MANNINGS. Source: PROD.retortLogtecLog. Counts distinct cycles per day.',
        'sql': """
            SELECT
                buDate AS prod_date,
                COUNT(DISTINCT controllerNo) AS retorts_active,
                COUNT(DISTINCT CAST(controllerNo AS VARCHAR) + '-' + CAST(cycleNo AS VARCHAR)) AS total_cycles,
                ROUND(AVG(temp), 1) AS avg_cook_temp
            FROM PROD.retortLogtecLog
            WHERE buDate >= DATEADD(day, -7, GETDATE())
              AND phase = 'Cook'
            GROUP BY buDate
            ORDER BY buDate DESC
        """
    },

    'retort_deviations': {
        'database': 'mannings',
        'department': 'Retort',
        'notes': 'Retort error/deviation log from MANNINGS. Source: PROD.retortErrorList.',
        'sql': """
            SELECT
                prodDate,
                error,
                timestamp
            FROM PROD.retortErrorList
            WHERE prodDate >= DATEADD(month, -3, GETDATE())
            ORDER BY prodDate DESC
        """
    },

    'retort_down_retorts': {
        'database': 'mannings',
        'department': 'Retort',
        'notes': 'Currently down retorts from MANNINGS. Source: PROD.retortDown.',
        'sql': """
            SELECT
                site,
                retort,
                begDateDown,
                endDateDown,
                comment
            FROM PROD.retortDown
            WHERE endDateDown >= GETDATE() OR endDateDown >= '2090-01-01'
            ORDER BY retort
        """
    },

    'retort_allocations': {
        'database': 'mannings',
        'department': 'Retort',
        'notes': 'Retort scheduling allocations from MANNINGS. Source: PROD.retortAllocation.',
        'sql': """
            SELECT
                schedDate,
                retort,
                allocation,
                manual
            FROM PROD.retortAllocation
            WHERE schedDate >= DATEADD(day, -1, GETDATE())
              AND schedDate <= DATEADD(day, 3, GETDATE())
            ORDER BY schedDate, retort
        """
    },

    # ══════════════════════════════════════════════════════════════════
    # PROCUREMENT KPIs
    # Confirmed columns from kpi_table_discovery.json (Mar 10, 2026)
    # ══════════════════════════════════════════════════════════════════

    'proc_inventory': {
        'database': 'ci',
        'department': 'Procurement',
        'notes': 'Raw/Pack/TRI/FG/PPHM Inventory. Columns: site, cont, type, item, descr, aQty, qQty, rQty, uom, expQty, exp60days, cost. No date column — snapshot table.',
        'sql': """
            SELECT
                site,
                cont,
                type,
                SUM(aQty) AS total_available,
                SUM(qQty) AS total_quarantine,
                SUM(rQty) AS total_reserved,
                SUM(cost) AS total_cost,
                SUM(expQty) AS total_expired,
                SUM(exp60days) AS expiring_60days,
                COUNT(*) AS item_count
            FROM db_accessadmin.KPI_PROC_Inventory
            GROUP BY site, cont, type
            ORDER BY site, type
        """
    },

    'proc_schedule_changes': {
        'database': 'ci',
        'department': 'Procurement',
        'notes': 'Schedule changes from KPI_MFG_ScheduleChangeLog. Columns: schedDate, line, mfgNum, item, descr, qty, action, actionDate, prevVal',
        'sql': """
            SELECT
                YEAR(schedDate) AS yr,
                MONTH(schedDate) AS mo,
                action,
                COUNT(*) AS change_count,
                SUM(qty) AS total_qty_affected
            FROM db_accessadmin.KPI_MFG_ScheduleChangeLog
            WHERE schedDate >= DATEADD(month, -3, GETDATE())
            GROUP BY YEAR(schedDate), MONTH(schedDate), action
            ORDER BY yr DESC, mo DESC, action
        """
    },

    # Procurement KPIs that are manual/broken:
    # - Customer Fill Rate: "Currently broken" per spreadsheet
    # - Cost Savings: manual (T:\Procurement\Cost Savings\2026\)

    # ══════════════════════════════════════════════════════════════════
    # HR KPIs
    # LABMGTCostModel in CI (headcount/labor cost modeling)
    # MANNINGS on AQFDB7 confirmed accessible (retort project uses it)
    # ══════════════════════════════════════════════════════════════════

    'hr_labor_cost_model': {
        'database': 'ci',
        'department': 'HR',
        'notes': 'Labor cost model with headcount by department/position. Source: CI.db_accessadmin.LABMGTCostModel (1,277 rows).',
        'sql': """
            SELECT
                Department,
                Position,
                COUNT(*) AS position_count,
                SUM(CAST(HeadCountReq AS FLOAT)) AS total_headcount,
                AVG(CAST(HoursShift AS FLOAT)) AS avg_hours_shift,
                site
            FROM db_accessadmin.LABMGTCostModel
            WHERE Status = 'Active'
            GROUP BY Department, Position, site
            ORDER BY Department, Position
        """
    },

    'hr_headcount_summary': {
        'database': 'ci',
        'department': 'HR',
        'notes': 'Total headcount by department from LABMGTCostModel. Quick summary for HR card.',
        'sql': """
            SELECT
                Department,
                SUM(CAST(HeadCountReq AS FLOAT)) AS total_headcount,
                COUNT(DISTINCT Position) AS distinct_positions,
                site
            FROM db_accessadmin.LABMGTCostModel
            WHERE Status = 'Active'
            GROUP BY Department, site
            ORDER BY total_headcount DESC
        """
    },

    'hr_kpi_dashboard': {
        'database': 'ci',
        'department': 'HR',
        'notes': 'HR KPIs from KPIDashData. Filter Focus=People for turnover, attendance, etc.',
        'sql': """
            SELECT
                [Date],
                KPI,
                Value,
                Type,
                Site
            FROM db_accessadmin.KPIDashData
            WHERE Focus = 'People'
              AND [Date] >= DATEADD(month, -6, GETDATE())
            ORDER BY [Date] DESC
        """
    },

    # ══════════════════════════════════════════════════════════════════
    # CROSS-DEPARTMENT: KPI Targets & Dashboard Data
    # ══════════════════════════════════════════════════════════════════

    'kpi_targets': {
        'database': 'ci',
        'department': 'All',
        'notes': 'All KPI target values. Columns: Site, KPI, KPILevel, Focus, Type, Target, Direction (Above/Below)',
        'sql': """
            SELECT
                Site,
                KPI,
                KPILevel,
                Focus,
                Type,
                Target,
                Direction
            FROM db_accessadmin.KPITargets
            ORDER BY Focus, KPI
        """
    },

    'kpi_dashboard_recent': {
        'database': 'ci',
        'department': 'All',
        'notes': 'Recent KPI entries from KPIDashData. Columns: Site, KPILevel, Focus, Date, KPI, Type, Value',
        'sql': """
            SELECT
                Site,
                KPILevel,
                Focus,
                [Date],
                KPI,
                Type,
                Value
            FROM db_accessadmin.KPIDashData
            WHERE [Date] >= DATEADD(month, -1, GETDATE())
            ORDER BY [Date] DESC
        """
    },
}

# ============================================
# API ENDPOINTS - OPERATIONS (Snowflake)
# ============================================

@app.route('/api/kpi/live', methods=['GET'])
def get_live_kpis():
    """Get live KPIs from Snowflake (OEE, production, etc.)"""
    try:
        plant_data = snowflake_client.query(SNOWFLAKE_QUERIES['plant_oee'])
        lines_data = snowflake_client.query(SNOWFLAKE_QUERIES['oee_by_line'])

        plant = plant_data[0] if plant_data else {}

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'plant': {
                'oee': plant.get('PLANT_OEE', 0),
                'performance': plant.get('PLANT_PERFORMANCE', 0),
                'quality': plant.get('PLANT_QUALITY', 0),
                'availability': plant.get('PLANT_AVAILABILITY', 0),
                'totalOutput': plant.get('TOTAL_OUTPUT', 0),
                'downtimeHours': plant.get('TOTAL_DOWNTIME_HOURS', 0),
                'manhours': plant.get('TOTAL_MANHOURS', 0),
                'linesReporting': plant.get('LINES_REPORTING', 0)
            },
            'lines': lines_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/redflags', methods=['GET'])
def get_red_flags():
    """Get lines/issues that need attention"""
    alerts = []

    # Try Snowflake for OEE alerts (may fail if SnowSQL not configured)
    try:
        low_oee = snowflake_client.query(SNOWFLAKE_QUERIES['lines_below_target'])
        downtime = snowflake_client.query(SNOWFLAKE_QUERIES['top_downtime'])

        # Add low OEE alerts
        for line in low_oee:
            # Convert to float to handle Snowflake returning strings
            avg_oee = float(line.get('AVG_OEE', 0) or 0)
            alerts.append({
                'id': f"oee-{line.get('LINE_NAME', 'unknown')}",
                'severity': 'high' if avg_oee < 60 else 'medium',
                'category': 'operations',
                'title': f"{line.get('LINE_NAME', 'Unknown')} OEE Below Target",
                'message': f"OEE at {avg_oee}% (target: 70%)",
                'value': avg_oee,
                'threshold': 70
            })

        # Add top unplanned downtime
        for dt in downtime[:3]:
            if not dt.get('PLANNED', True):
                alerts.append({
                    'id': f"dt-{dt.get('REASON', 'unknown')[:20]}",
                    'severity': 'medium',
                    'category': 'downtime',
                    'title': f"Unplanned Downtime: {dt.get('REASON', 'Unknown')}",
                    'message': f"{dt.get('TOTAL_HOURS_LOST', 0)} hours lost",
                    'value': dt.get('TOTAL_HOURS_LOST', 0)
                })
    except Exception as e:
        print(f"Snowflake red flags query failed: {e}")
        # Continue without Snowflake alerts - don't fail the whole endpoint

    # TODO: Add Sage X3 alerts here after meeting with Dennis
    # Examples: AR aging, inventory thresholds, etc.

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'alerts': alerts,
        'summary': {
            'high': len([a for a in alerts if a['severity'] == 'high']),
            'medium': len([a for a in alerts if a['severity'] == 'medium']),
            'low': len([a for a in alerts if a['severity'] == 'low'])
        },
        'note': 'Red flags configuration pending - discuss with Dennis' if not alerts else None
    })

@app.route('/api/operations/downtime', methods=['GET'])
def get_downtime():
    """Get downtime breakdown"""
    try:
        data = snowflake_client.query(SNOWFLAKE_QUERIES['top_downtime'])
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'downtime': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/operations/labor', methods=['GET'])
def get_labor():
    """Get labor productivity data"""
    try:
        data = snowflake_client.query(SNOWFLAKE_QUERIES['labor_productivity'])
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'labor': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/operations/trend', methods=['GET'])
def get_hourly_trend():
    """Get hourly OEE trend"""
    try:
        data = snowflake_client.query(SNOWFLAKE_QUERIES['hourly_trend'])
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'trend': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/operations/active-lines', methods=['GET'])
def get_active_lines():
    """Get currently active production lines"""
    try:
        data = snowflake_client.query(SNOWFLAKE_QUERIES['active_lines'])
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'lines': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/production/schedules', methods=['GET'])
def get_production_schedules():
    """Get production schedules for all facilities.
    Currently reads from T-Drive files (when available) or internal DB."""
    result = {
        'timestamp': datetime.now().isoformat(),
        'facilities': {},
        'note': 'Production schedule data pending T-Drive integration'
    }

    # Try to get schedule data from MANUFACTURING DB
    try:
        recent_schedule = internal_db.query("""
            SELECT TOP 50
                prodDate, line, valueStream, product, prodDescr, customer,
                targetVal, theoLineRate, begTime, endTime
            FROM PROD.eopShiftNotes
            WHERE prodDate >= DATEADD(day, -1, GETDATE())
            ORDER BY prodDate DESC, line
        """, database='manufacturing')
        result['facilities']['foods'] = recent_schedule
    except Exception as e:
        result['facilities']['foods'] = {'status': 'error', 'error': str(e)[:200]}

    return jsonify(result)

@app.route('/api/sop/generate', methods=['POST'])
def generate_sop():
    """Trigger S&OP report generation via subprocess.
    Runs headless — no Excel auto-open, no input() prompt."""
    try:
        sop_base = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'S&OP Creation Automation', 'S&OP Project', 'sop_automation'
        )
        sop_src = os.path.join(sop_base, 'src')

        if not os.path.exists(sop_base):
            return jsonify({
                'status': 'not_configured',
                'message': 'S&OP project not found.',
                'expected_path': sop_base
            })

        # Run a headless Python one-liner that imports and runs the generator
        # without the __main__ block (which has os.startfile + input())
        headless_script = (
            "import sys, json; "
            f"sys.path.insert(0, r'{sop_src}'); "
            f"sys.path.insert(0, r'{sop_base}'); "
            "from sop_xlwings_generator import generate_sop_xlwings; "
            "r = generate_sop_xlwings(use_sage=True); "
            "exec('try:\\n import xlwings as xw\\n for a in xw.apps: a.quit()\\nexcept: pass'); "
            "print(json.dumps({'success': r.get('success',False), 'file_path': r.get('file_path',''), "
            "'data_source': r.get('data_source',''), 'work_order_count': r.get('work_order_count',0), "
            "'message': r.get('message','')}))"
        )

        result = subprocess.run(
            ['python', '-c', headless_script],
            capture_output=True, text=True, timeout=300,
            cwd=sop_base
        )

        # Parse the JSON output from the last line
        output_lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
        sop_result = None
        for line in reversed(output_lines):
            try:
                sop_result = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if sop_result and sop_result.get('success') and sop_result.get('file_path'):
            return jsonify({
                'status': 'success',
                'message': 'S&OP generated successfully.',
                'file_path': sop_result['file_path'],
                'data_source': sop_result.get('data_source', 'unknown'),
                'work_orders': sop_result.get('work_order_count', 0)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': sop_result.get('message', 'S&OP generation failed.') if sop_result else 'No output from generator.',
                'stdout': result.stdout[-500:] if result.stdout else '',
                'stderr': result.stderr[-500:] if result.stderr else ''
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'S&OP generation timed out (5 min limit).'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/sop/latest', methods=['GET'])
def get_latest_sop():
    """Get the path to the most recent S&OP report file."""
    # Check local reports folder first, then external paths
    search_paths = [
        os.path.join(_script_dir, 'reports'),
        os.path.join(_script_dir, '..', 'S&OP Creation Automation', 'S&OP Project', 'sop_automation', 'reports'),
    ]
    sop_reports = None
    for p in search_paths:
        if os.path.exists(p):
            sop_reports = p
            break
    if not sop_reports:
        return jsonify({'status': 'no_reports', 'message': 'No S&OP reports found.'})

    files = sorted(
        [f for f in os.listdir(sop_reports) if f.endswith(('.xlsx', '.xlsm')) and not f.startswith('~$')],
        key=lambda f: os.path.getmtime(os.path.join(sop_reports, f)),
        reverse=True
    )
    if files:
        full_path = os.path.join(sop_reports, files[0])
        return jsonify({
            'status': 'found',
            'file_path': os.path.abspath(full_path),
            'file_name': files[0],
            'generated': datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
        })
    return jsonify({'status': 'no_reports', 'message': 'No S&OP reports found.'})


@app.route('/api/sop/open', methods=['POST'])
def open_sop():
    """Open the latest S&OP report in Excel on the local machine."""
    try:
        data = request.get_json() or {}
        file_path = data.get('file_path')

        if not file_path:
            # Fall back to latest — check local reports first
            for _sp in [os.path.join(_script_dir, 'reports'),
                        os.path.join(_script_dir, '..', 'S&OP Creation Automation', 'S&OP Project', 'sop_automation', 'reports')]:
                if os.path.exists(_sp):
                    sop_reports = _sp
                    break
            else:
                sop_reports = None
            if sop_reports:
                files = sorted(
                    [f for f in os.listdir(sop_reports) if f.endswith(('.xlsx', '.xlsm')) and not f.startswith('~$')],
                    key=lambda f: os.path.getmtime(os.path.join(sop_reports, f)),
                    reverse=True
                )
                if files:
                    file_path = os.path.abspath(os.path.join(sop_reports, files[0]))

        if not file_path or not os.path.exists(file_path):
            return jsonify({'status': 'error', 'message': 'No S&OP file found to open.'}), 404

        os.startfile(file_path)
        return jsonify({'status': 'opened', 'file_path': file_path})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/sop/status', methods=['GET'])
def get_sop_status():
    """Get S&OP decision-ready snapshot — demand vs capacity, constraints, slack."""
    try:
        from sheldon_brain import SOPReader
        data = SOPReader.read_sop_snapshot()
        if 'error' in data:
            return jsonify({'status': 'error', 'message': data['error']}), 500
        return jsonify(data)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


# ============================================
# API ENDPOINTS - PEOPLE (Snowflake/Redzone)
# ============================================

@app.route('/api/people/summary', methods=['GET'])
def get_people_summary():
    """Get people/labor summary metrics - uses plant_oee for reliable data"""
    try:
        # Use plant_oee query which we know works
        plant_data = snowflake_client.query(SNOWFLAKE_QUERIES['plant_oee'])
        plant = plant_data[0] if plant_data else {}

        total_manhours = float(plant.get('TOTAL_MANHOURS', 0) or 0)
        lines_reporting = int(plant.get('LINES_REPORTING', 0) or 0)
        total_output = int(plant.get('TOTAL_OUTPUT', 0) or 0)

        # Estimate headcount from manhours (assume 8-hour shift in last 24 hours)
        # This is an approximation - real headcount would need HR system
        estimated_headcount = int(total_manhours / 8) if total_manhours > 0 else 0
        expected_workers = 150  # Typical shift staffing - adjust as needed
        attendance_rate = min(100, (estimated_headcount / expected_workers) * 100) if expected_workers > 0 else 0

        # Calculate productivity
        productivity = round(total_output / total_manhours, 1) if total_manhours > 0 else 0

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'headcount': estimated_headcount,
            'expectedHeadcount': expected_workers,
            'attendance': round(attendance_rate, 1),
            'totalManhours': round(total_manhours, 1),
            'productivity': productivity,
            'linesStaffed': lines_reporting,
            'turnover': 2.1,  # Placeholder - would need HR system integration
            'source': 'redzone',
            'note': 'Headcount estimated from manhours'
        })
    except Exception as e:
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'headcount': 0,
            'attendance': 0,
            'turnover': 0,
            'error': str(e),
            'source': 'error'
        })

# ============================================
# API ENDPOINTS - QUALITY (Snowflake/Redzone)
# ============================================

@app.route('/api/quality/summary', methods=['GET'])
def get_quality_summary():
    """Get quality metrics summary - uses plant_oee query for reliable data"""
    try:
        # Use plant_oee query which we know works
        plant_data = snowflake_client.query(SNOWFLAKE_QUERIES['plant_oee'])
        plant = plant_data[0] if plant_data else {}

        avg_quality = float(plant.get('PLANT_QUALITY', 0) or 0)
        total_output = int(plant.get('TOTAL_OUTPUT', 0) or 0)

        # Quality score from Redzone is essentially first pass yield
        first_pass_yield = avg_quality

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'firstPassYield': round(first_pass_yield, 1),
            'qualityScore': round(avg_quality, 1),
            'totalOutput': total_output,
            'totalDefects': 0,  # Defect tracking not available in this view
            'complaints': 0,  # Would need separate system
            'auditsScheduled': 2,  # Placeholder
            'certifications': ['SQF', 'FSSC 22000', 'Organic'],  # Known certifications
            'source': 'redzone'
        })
    except Exception as e:
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'firstPassYield': 0,
            'qualityScore': 0,
            'complaints': 0,
            'auditsScheduled': 0,
            'error': str(e),
            'source': 'error'
        })

# ============================================
# API ENDPOINTS - DEPARTMENTAL KPIs
# ============================================

@app.route('/api/kpi/departments', methods=['GET'])
def get_all_dept_kpis():
    """Get all departmental KPIs in one call for the KPI dashboard tab.
    Returns available data from each source, with graceful fallback.
    Pulls from Snowflake (live), Sage X3 (live), and internal DBs (when available)."""
    result = {
        'timestamp': datetime.now().isoformat(),
        'production': {},
        'quality': {},
        'warehouse': {},
        'safety': {},
        'retort': {},
        'procurement': {},
        'maintenance': {},
        'hr': {},
        'all': {},
        'errors': []
    }

    # ── SNOWFLAKE DATA (LIVE — always available) ─────────────────────

    # Plant OEE + Quality from Redzone
    try:
        plant_data = snowflake_client.query(SNOWFLAKE_QUERIES.get('plant_oee', ''))
        if plant_data:
            plant = plant_data[0]
            result['production']['plantOEE'] = float(plant.get('PLANT_OEE', 0) or 0)
            result['production']['plantQuality'] = float(plant.get('PLANT_QUALITY', 0) or 0)
            result['production']['plantAvailability'] = float(plant.get('PLANT_AVAILABILITY', 0) or 0)
            result['production']['plantPerformance'] = float(plant.get('PLANT_PERFORMANCE', 0) or 0)
            result['production']['totalOutput'] = int(plant.get('TOTAL_OUTPUT', 0) or 0)
            result['production']['downtimeHours'] = float(plant.get('TOTAL_DOWNTIME_HOURS', 0) or 0)
            result['production']['linesReporting'] = int(plant.get('LINES_REPORTING', 0) or 0)
    except Exception as e:
        result['errors'].append(f'snowflake_oee: {str(e)[:100]}')

    # Critical Defect Rate from Redzone
    try:
        quality_data = snowflake_client.query(SNOWFLAKE_QUERIES.get('quality_summary', ''))
        if quality_data:
            q = quality_data[0]
            total_output = int(q.get('TOTAL_OUTPUT', 0) or 0)
            total_defects = int(q.get('TOTAL_DEFECTS', 0) or 0)
            defect_rate = (total_defects / total_output * 100) if total_output > 0 else 0
            result['production']['criticalDefectRate'] = round(defect_rate, 4)
            result['production']['totalDefects'] = total_defects
    except Exception as e:
        result['errors'].append(f'snowflake_defects: {str(e)[:100]}')

    # Unplanned Downtime for Maintenance card
    try:
        downtime_data = snowflake_client.query(SNOWFLAKE_QUERIES.get('top_downtime', ''))
        if downtime_data:
            total_downtime = sum(float(d.get('HOURS_LOST', 0) or 0) for d in downtime_data)
            result['maintenance']['unplannedDowntime'] = round(total_downtime, 1)
            result['maintenance']['topDowntimeReasons'] = [
                {'reason': d.get('REASON', ''), 'hours': float(d.get('HOURS_LOST', 0) or 0)}
                for d in downtime_data[:5]
            ]
    except Exception as e:
        result['errors'].append(f'snowflake_downtime: {str(e)[:100]}')

    # Red flag lines count
    try:
        red_flags = snowflake_client.query(SNOWFLAKE_QUERIES.get('lines_below_target', ''))
        if red_flags:
            result['production']['redFlagLines'] = len(red_flags)
    except Exception:
        pass

    # ── SAGE X3 DATA (LIVE — financial + inventory) ──────────────────

    # Inventory for Warehouse + Procurement cards
    try:
        inv_data = sage_client.query(SQL_QUERIES.get('inventory_value', ''))
        if inv_data:
            total_inv = sum(float(row.get('TotalValue', 0) or 0) for row in inv_data)
            result['warehouse']['totalInventoryValue'] = round(total_inv, 2)
            result['procurement']['totalInventoryValue'] = round(total_inv, 2)
            by_facility = {}
            for row in inv_data:
                fac = row.get('STOFCY_0', 'Unknown')
                val = float(row.get('TotalValue', 0) or 0)
                by_facility[fac] = round(val, 2)
            result['warehouse']['inventoryByFacility'] = by_facility
    except Exception as e:
        result['errors'].append(f'sage_inventory: {str(e)[:100]}')

    # Finished Goods for Warehouse card
    try:
        fg_data = sage_client.query(SQL_QUERIES.get('finished_goods_value', ''))
        if fg_data:
            fg_total = sum(float(row.get('FinishedGoodsValue', 0) or row.get('FGValue', 0) or 0) for row in fg_data)
            result['warehouse']['finishedGoodsValue'] = round(fg_total, 2)
    except Exception as e:
        result['errors'].append(f'sage_fg: {str(e)[:100]}')

    # AR Days for financial cross-reference
    try:
        ar_data = sage_client.query(SQL_QUERIES.get('ar_aging', ''))
        if ar_data:
            ar = ar_data[0]
            total_ar = float(ar.get('TotalAR', 0) or 0)
            result['warehouse']['totalAR'] = round(total_ar, 2)
    except Exception:
        pass

    # ── DONNA QA DATA (when running) ─────────────────────────────────

    try:
        req = urllib.request.Request('http://localhost:5002/api/dashboard/summary', method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            donna_data = json.loads(resp.read().decode())
            if donna_data:
                result['quality']['donnaOverdue'] = donna_data.get('overdue_count', 0)
                result['quality']['donnaFailing'] = donna_data.get('failing_count', 0)
                result['quality']['donnaPipeline'] = donna_data.get('total_batches', 0)
                result['quality']['donnaDueToday'] = donna_data.get('due_today', 0)
    except Exception:
        pass  # Donna not running — no problem

    # ── INTERNAL DB QUERIES (when Nick grants access) ────────────────

    all_dept_kpis = [
        # Production
        ('production', 'scheduleAttainment', 'prod_schedule_attainment'),
        ('production', 'ontimeStartup', 'prod_ontime_startup'),
        ('production', 'ingredientYield', 'prod_ingredient_yield'),
        ('production', 'materialTracking', 'prod_material_tracking'),
        ('production', 'criticalDefectRate', 'prod_critical_defect_rate'),
        ('production', 'supplyCost', 'prod_supply_cost'),
        ('production', 'laborTargetVsActual', 'prod_labor_target_vs_actual'),
        ('production', 'humanErrors', 'prod_human_errors'),
        ('production', 'majorUnplannedDowntime', 'prod_major_unplanned_downtime'),
        ('production', 'eopDetail', 'prod_eop_detail'),
        # Quality
        ('quality', 'overallQuality', 'qual_overall_quality'),
        ('quality', 'firstTimeQuality', 'qual_first_time_quality'),
        ('quality', 'overdueReleases', 'qual_overdue_releases'),
        ('quality', 'foreignMatter', 'qual_foreign_matter'),
        ('quality', 'reworkLog', 'qual_rework_log'),
        ('quality', 'laborTargetVsActual', 'qual_labor_target_vs_actual'),
        ('quality', 'mreFailureRate', 'qual_mre_failure_rate'),
        ('quality', 'internalQAFailures', 'qual_internal_qa_failures'),
        # Safety
        ('safety', 'supplyCost', 'safety_supply_cost'),
        ('safety', 'incidents', 'safety_incidents'),
        ('safety', 'kpiDashboard', 'safety_kpi_dashboard'),
        # Warehouse
        ('warehouse', 'trucksReceivedShipped', 'wh_trucks_received_shipped'),
        ('warehouse', 'palletMovesPerManhour', 'wh_pallet_moves_per_manhour'),
        ('warehouse', 'ontimeDelivery', 'wh_ontime_delivery'),
        ('warehouse', 'cycleCount', 'wh_cycle_count'),
        ('warehouse', 'laborTargetVsActual', 'wh_labor_target_vs_actual'),
        ('warehouse', 'repairCost', 'wh_repair_cost'),
        ('warehouse', 'freezerCapacity', 'wh_freezer_capacity'),
        # Retort
        ('retort', 'laborTargetVsActual', 'retort_labor_target_vs_actual'),
        ('retort', 'dailyCycles', 'retort_daily_cycles'),
        ('retort', 'deviations', 'retort_deviations'),
        ('retort', 'downRetorts', 'retort_down_retorts'),
        ('retort', 'allocations', 'retort_allocations'),
        # Procurement
        ('procurement', 'inventory', 'proc_inventory'),
        ('procurement', 'scheduleChanges', 'proc_schedule_changes'),
        # HR
        ('hr', 'laborCostModel', 'hr_labor_cost_model'),
        ('hr', 'headcountSummary', 'hr_headcount_summary'),
        ('hr', 'kpiDashboard', 'hr_kpi_dashboard'),
        # Cross-department
        ('all', 'kpiTargets', 'kpi_targets'),
        ('all', 'kpiDashboardRecent', 'kpi_dashboard_recent'),
    ]

    for dept, key, query_name in all_dept_kpis:
        query_def = DEPT_KPI_QUERIES.get(query_name)
        if not query_def or query_def.get('sql') is None:
            if dept not in result:
                result[dept] = {}
            result[dept][key] = {'status': 'manual_only', 'note': query_def.get('notes', '') if query_def else ''}
            continue

        if query_def.get('database') == 'snowflake':
            try:
                data = snowflake_client.query(query_def['sql'])
                result[dept][key] = data[0] if len(data) == 1 else data
            except Exception as e:
                result[dept][key] = {'status': 'error', 'error': str(e)[:200]}
            continue

        try:
            data = internal_db.query(query_def['sql'], database=query_def['database'])
            result[dept][key] = data[0] if len(data) == 1 else data
        except Exception as e:
            err_msg = str(e)
            if 'pyodbc not installed' in err_msg or 'not available' in err_msg:
                result[dept][key] = {'status': 'not_configured', 'note': 'Awaiting DB access from Nick'}
            else:
                result[dept][key] = {'status': 'error', 'error': err_msg[:200]}

    return jsonify(result)


@app.route('/api/kpi/department/<dept>', methods=['GET'])
def get_dept_kpi(dept):
    """Get KPIs for a specific department.

    Args:
        dept: 'production' or 'quality' (more to come)
    """
    prefix_map = {
        'production': 'prod_',
        'quality': 'qual_',
        'safety': 'safety_',
        'warehouse': 'wh_',
        'retort': 'retort_',
        'procurement': 'proc_',
        'maintenance': 'maint_',
        'hr': 'hr_',
        'all': 'kpi_',
    }

    prefix = prefix_map.get(dept)
    if not prefix:
        return jsonify({'error': f'Unknown department: {dept}', 'available': list(prefix_map.keys())}), 404

    result = {
        'timestamp': datetime.now().isoformat(),
        'department': dept,
        'kpis': {},
        'errors': []
    }

    for query_name, query_def in DEPT_KPI_QUERIES.items():
        if not query_name.startswith(prefix):
            continue

        kpi_key = query_name[len(prefix):]

        if query_def.get('sql') is None:
            result['kpis'][kpi_key] = {'status': 'manual_only', 'note': query_def.get('notes', '')}
            continue

        if query_def.get('database') == 'snowflake':
            try:
                data = snowflake_client.query(query_def['sql'])
                result['kpis'][kpi_key] = data
            except Exception as e:
                result['kpis'][kpi_key] = {'status': 'error', 'error': str(e)[:200]}
                result['errors'].append(f'{kpi_key}: {str(e)[:100]}')
        else:
            try:
                data = internal_db.query(query_def['sql'], database=query_def['database'])
                result['kpis'][kpi_key] = data
            except Exception as e:
                err_msg = str(e)
                if 'not available' in err_msg:
                    result['kpis'][kpi_key] = {'status': 'not_configured'}
                else:
                    result['kpis'][kpi_key] = {'status': 'error', 'error': err_msg[:200]}
                    result['errors'].append(f'{kpi_key}: {err_msg[:100]}')

    return jsonify(result)


# ============================================
# API ENDPOINTS - FINANCIAL (Sage X3)
# ============================================

@app.route('/api/financial/revenue', methods=['GET'])
def get_revenue():
    """Get revenue data (daily, MTD, YTD)"""
    try:
        daily = sage_client.query(SQL_QUERIES['daily_revenue'])
        mtd = sage_client.query(SQL_QUERIES['mtd_revenue'])
        ytd = sage_client.query(SQL_QUERIES['ytd_revenue'])

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'daily': daily[0].get('DailyRevenue', 0) if daily else 0,
            'mtd': mtd[0].get('MTDRevenue', 0) if mtd else 0,
            'ytd': ytd[0].get('YTDRevenue', 0) if ytd else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/kpis', methods=['GET'])
def get_financial_kpis():
    """Get financial KPIs for dashboard"""
    try:
        mtd = sage_client.query(SQL_QUERIES['mtd_revenue'])
        ytd = sage_client.query(SQL_QUERIES['ytd_revenue'])

        mtd_value = mtd[0].get('MTDRevenue', 0) if mtd else 0
        ytd_value = ytd[0].get('YTDRevenue', 0) if ytd else 0

        # Get Gross Margin
        gross_margin = 0
        try:
            margin_data = sage_client.query(SQL_QUERIES['gross_margin_mtd'])
            if margin_data:
                revenue = margin_data[0].get('LineRevenue', 0) or 0
                cost = margin_data[0].get('LineCost', 0) or 0
                gross_margin = ((revenue - cost) / revenue * 100) if revenue else 0
        except Exception as e:
            print(f"Gross margin query error: {e}")

        # Get Cash Position
        cash_position = 0
        try:
            cash_data = sage_client.query(SQL_QUERIES['cash_position'])
            if cash_data:
                cash_position = cash_data[0].get('CashBalance', 0) or 0
        except Exception as e:
            print(f"Cash position query error: {e}")

        return jsonify({
            'mtd': mtd_value,
            'ytd': ytd_value,
            'grossMargin': round(gross_margin, 1),
            'cashPosition': cash_position
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/gross-margin', methods=['GET'])
def get_gross_margin():
    """Get gross margin calculation"""
    try:
        margin_data = sage_client.query(SQL_QUERIES['gross_margin_mtd'])
        if margin_data:
            revenue = margin_data[0].get('LineRevenue', 0) or 0
            cost = margin_data[0].get('LineCost', 0) or 0
            gross_profit = revenue - cost
            gross_margin = (gross_profit / revenue * 100) if revenue else 0

            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'revenue': revenue,
                'cost': cost,
                'grossProfit': gross_profit,
                'grossMargin': round(gross_margin, 1)
            })
        return jsonify({'error': 'No data returned'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/cogs-ytd', methods=['GET'])
def get_cogs_ytd():
    """Get year-to-date COGS for Days on Hand and Inventory Turns calculations"""
    try:
        data = sage_client.query(SQL_QUERIES['cogs_ytd'])
        cogs_ytd = data[0].get('COGS_YTD', 0) or 0 if data else 0

        # Calculate days elapsed in current year
        now = datetime.now()
        year_start = datetime(now.year, 1, 1)
        days_elapsed = (now - year_start).days + 1

        # Annualize: (YTD COGS / days elapsed) * 365
        avg_daily_cogs = cogs_ytd / days_elapsed if days_elapsed > 0 else 0
        annualized_cogs = avg_daily_cogs * 365

        return jsonify({
            'timestamp': now.isoformat(),
            'cogsYTD': cogs_ytd,
            'daysElapsed': days_elapsed,
            'avgDailyCOGS': round(avg_daily_cogs, 2),
            'annualizedCOGS': round(annualized_cogs, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/cash-position', methods=['GET'])
def get_cash_position():
    """Get cash position from GL accounts"""
    try:
        cash_data = sage_client.query(SQL_QUERIES['cash_position'])
        if cash_data:
            balance = cash_data[0].get('CashBalance', 0) or 0
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'cashPosition': balance,
                'accounts': ['1000', '1010', '1011', '1015']
            })
        return jsonify({'cashPosition': 0, 'note': 'No balance data'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/financial/ebitda', methods=['GET'])
def get_ebitda():
    """Get EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization)"""
    try:
        # Get actual MTD revenue and COGS from invoices (more accurate)
        gm_data = sage_client.query(SQL_QUERIES['gross_margin_mtd'])
        revenue = 0
        cogs = 0
        if gm_data and len(gm_data) > 0:
            revenue = float(gm_data[0].get('LineRevenue') or 0)
            cogs = float(gm_data[0].get('LineCost') or 0)

        # Get D&A from BALANCE - use FY22 period 1 as estimate if FY23 not available
        # Query for FY23 first, fallback to FY22
        da_query = """
            SELECT
                (SELECT COALESCE(SUM(DEB_1 - CDT_1), 0) FROM AMQ.BALANCE
                 WHERE ACC_0 IN ('6050','6052','6053','6055','6056','6057','6058','6059','6060',
                                 '6064','6065','6066','6067','6068','6069','6070','6071','6072','6073')
                 AND FIY_0 = (SELECT MAX(FIY_0) FROM AMQ.BALANCE WHERE ACC_0 = '6050')) as Depreciation,
                (SELECT COALESCE(SUM(DEB_1 - CDT_1), 0) FROM AMQ.BALANCE
                 WHERE ACC_0 = '7150'
                 AND FIY_0 = (SELECT MAX(FIY_0) FROM AMQ.BALANCE WHERE ACC_0 = '7150')) as Amortization
        """
        da_data = sage_client.query(da_query)
        depreciation = 0
        amortization = 0
        if da_data and len(da_data) > 0:
            depreciation = float(da_data[0].get('Depreciation') or 0)
            amortization = float(da_data[0].get('Amortization') or 0)

        # Calculate EBITDA = Gross Profit + D&A
        # Since we don't have detailed OpEx breakdown, use: EBITDA = Revenue - COGS + D&A
        # This is a simplified EBITDA (essentially Gross Profit + D&A)
        gross_profit = revenue - cogs
        ebitda = gross_profit + depreciation + amortization

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'ebitda': round(ebitda, 2),
            'components': {
                'revenue': round(revenue, 2),
                'cogs': round(cogs, 2),
                'grossProfit': round(gross_profit, 2),
                'depreciation': round(depreciation, 2),
                'amortization': round(amortization, 2)
            },
            'note': 'Simplified EBITDA: Gross Profit + D&A (MTD)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/accounts', methods=['GET'])
def debug_accounts():
    """Debug endpoint to explore chart of accounts"""
    prefix = request.args.get('prefix', '6')
    search = request.args.get('search', '')
    try:
        if search:
            query = f"""
                SELECT ACC_0 as Account, DES_0 as Description, SAC_0 as Type
                FROM AMQ.GACCOUNT
                WHERE DES_0 LIKE '%{search}%'
                ORDER BY ACC_0
            """
        else:
            query = f"""
                SELECT ACC_0 as Account, DES_0 as Description, SAC_0 as Type
                FROM AMQ.GACCOUNT
                WHERE ACC_0 LIKE '{prefix}%'
                ORDER BY ACC_0
            """
        data = sage_client.query(query)
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'prefix': prefix if not search else None,
            'search': search if search else None,
            'count': len(data),
            'accounts': data
        })
    except Exception as e:
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@app.route('/api/debug/balance', methods=['GET'])
def debug_balance():
    """Debug endpoint to explore BALANCE table"""
    acc = request.args.get('acc', '4000')
    try:
        query = f"""
            SELECT TOP 5 ACC_0, FIY_0 as FiscalYear,
                   DEB_0, CDT_0, DEB_1, CDT_1, DEB_2, CDT_2,
                   DEB_3, CDT_3, DEB_4, CDT_4, DEB_5, CDT_5,
                   DEB_6, CDT_6, DEB_7, CDT_7, DEB_8, CDT_8,
                   DEB_9, CDT_9, DEB_10, CDT_10, DEB_11, CDT_11, DEB_12, CDT_12
            FROM AMQ.BALANCE
            WHERE ACC_0 = '{acc}'
            ORDER BY FIY_0 DESC
        """
        data = sage_client.query(query)
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'account': acc,
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@app.route('/api/inventory/summary', methods=['GET'])
def get_inventory_summary():
    """Get inventory summary by facility"""
    try:
        by_facility = sage_client.query(SQL_QUERIES['inventory_by_facility'])
        by_status = sage_client.query(SQL_QUERIES['inventory_by_status'])

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'byFacility': by_facility,
            'byStatus': by_status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/value', methods=['GET'])
def get_inventory_value():
    """Get inventory value by facility"""
    try:
        data = sage_client.query(SQL_QUERIES['inventory_value'])
        total = sum(row.get('TotalValue', 0) for row in data)

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'byFacility': data,
            'total': total
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/kpis', methods=['GET'])
def get_inventory_kpis():
    """Get inventory KPIs for dashboard"""
    try:
        data = sage_client.query(SQL_QUERIES['inventory_value'])
        total = sum(row.get('TotalValue', 0) for row in data)

        return jsonify({
            'totalValue': total,
            'byFacility': {row.get('Facility', 'UNK'): row.get('TotalValue', 0) for row in data}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/finished-goods', methods=['GET'])
def get_finished_goods():
    """Get finished goods inventory value"""
    try:
        data = sage_client.query(SQL_QUERIES['finished_goods_value'])
        value = data[0].get('FinishedGoodsValue', 0) if data else 0

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ar/aging', methods=['GET'])
def get_ar_aging():
    """Get AR aging breakdown"""
    try:
        data = sage_client.query(SQL_QUERIES['ar_aging'])
        ar = data[0] if data else {}

        total_ar = ar.get('TotalAR', 0)
        # Calculate weighted average AR days (simplified)
        ar_days = 45  # Default estimate

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'totalAR': total_ar,
            'arDays': ar_days,
            'aging': {
                'current': ar.get('Current30', 0),
                'days31to60': ar.get('Days31to60', 0),
                'days61to90': ar.get('Days61to90', 0),
                'over90': ar.get('Over90', 0)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ar/days', methods=['GET'])
def get_ar_days():
    """Get AR days KPI - calculated as weighted average of aging buckets"""
    try:
        data = sage_client.query(SQL_QUERIES['ar_aging'])
        ar = data[0] if data else {}

        total_ar = float(ar.get('TotalAR', 0) or 0)
        current = float(ar.get('Current30', 0) or 0)
        days_31_60 = float(ar.get('Days31to60', 0) or 0)
        days_61_90 = float(ar.get('Days61to90', 0) or 0)
        over_90 = float(ar.get('Over90', 0) or 0)

        # Calculate weighted average AR days
        # Use midpoint of each bucket as weight
        if total_ar > 0:
            weighted_days = (
                (current * 15) +       # Midpoint of 0-30 days
                (days_31_60 * 45) +    # Midpoint of 31-60 days
                (days_61_90 * 75) +    # Midpoint of 61-90 days
                (over_90 * 120)        # Estimate 120 days for over 90
            ) / total_ar
            ar_days = round(weighted_days, 1)
        else:
            ar_days = 0

        return jsonify({
            'arDays': ar_days,
            'totalAR': total_ar,
            'aging': {
                'current': current,
                'days31to60': days_31_60,
                'days61to90': days_61_90,
                'over90': over_90
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/top', methods=['GET'])
def get_top_customers():
    """Get top customers by revenue"""
    try:
        data = sage_client.query(SQL_QUERIES['top_customers'])
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'customers': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# COMBINED ENDPOINTS (for SHELDON dashboard)
# ============================================

@app.route('/api/health-score', methods=['GET'])
def get_health_score():
    """Calculate overall business health score (0-100) based on weighted KPIs"""
    try:
        scores = {}
        weights = {
            'oee': 25,           # Operations efficiency
            'quality': 20,       # Product quality
            'grossMargin': 20,   # Financial health
            'arDays': 15,        # Cash collection
            'inventory': 10,     # Inventory management
            'availability': 10   # Production availability
        }

        # Get OEE from Snowflake
        try:
            plant_data = snowflake_client.query(SNOWFLAKE_QUERIES['plant_oee'])
            if plant_data and len(plant_data) > 0:
                plant = plant_data[0]
                oee = float(plant.get('PLANT_OEE') or 0)
                quality = float(plant.get('PLANT_QUALITY') or 0)
                availability = float(plant.get('PLANT_AVAILABILITY') or 0)
                # OEE score: target is 85%, scale 0-100
                scores['oee'] = min(100, (oee / 85) * 100)
                scores['quality'] = min(100, (quality / 98) * 100)  # Target 98%
                scores['availability'] = min(100, (availability / 90) * 100)  # Target 90%
        except Exception as e:
            print(f"Health score - Snowflake error: {e}")
            scores['oee'] = 50  # Default to middle score
            scores['quality'] = 50
            scores['availability'] = 50

        # Get Gross Margin from Sage
        try:
            margin_data = sage_client.query(SQL_QUERIES['gross_margin_mtd'])
            if margin_data:
                revenue = float(margin_data[0].get('LineRevenue', 0) or 0)
                cost = float(margin_data[0].get('LineCost', 0) or 0)
                gross_margin = ((revenue - cost) / revenue * 100) if revenue else 0
                # Target gross margin is 20%, scale accordingly
                scores['grossMargin'] = min(100, (gross_margin / 20) * 100)
        except Exception as e:
            print(f"Health score - Gross margin error: {e}")
            scores['grossMargin'] = 50

        # Get AR Days
        try:
            ar_data = sage_client.query(SQL_QUERIES['ar_aging'])
            ar = ar_data[0] if ar_data else {}
            total_ar = float(ar.get('TotalAR', 0) or 0)
            current = float(ar.get('Current30', 0) or 0)
            days_31_60 = float(ar.get('Days31to60', 0) or 0)
            days_61_90 = float(ar.get('Days61to90', 0) or 0)
            over_90 = float(ar.get('Over90', 0) or 0)
            if total_ar > 0:
                ar_days = ((current * 15) + (days_31_60 * 45) + (days_61_90 * 75) + (over_90 * 120)) / total_ar
            else:
                ar_days = 30
            # Lower AR days is better. Target is 30 days, 60+ is bad
            if ar_days <= 30:
                scores['arDays'] = 100
            elif ar_days <= 45:
                scores['arDays'] = 80
            elif ar_days <= 60:
                scores['arDays'] = 60
            else:
                scores['arDays'] = max(20, 100 - ar_days)
        except Exception as e:
            print(f"Health score - AR days error: {e}")
            scores['arDays'] = 50

        # Get Inventory turnover estimate
        try:
            inv_data = sage_client.query(SQL_QUERIES['inventory_value'])
            total_inv = sum(float(row.get('TotalValue', 0) or 0) for row in inv_data) if inv_data else 0
            # Simple scoring based on inventory level (industry specific)
            # For food manufacturing, inventory should be managed tightly
            scores['inventory'] = 70  # Default reasonable score
        except Exception as e:
            print(f"Health score - Inventory error: {e}")
            scores['inventory'] = 50

        # Calculate weighted overall score
        overall_score = 0
        total_weight = 0
        for metric, weight in weights.items():
            if metric in scores:
                overall_score += scores[metric] * weight
                total_weight += weight

        final_score = round(overall_score / total_weight) if total_weight > 0 else 0

        # Determine status
        if final_score >= 80:
            status = 'excellent'
        elif final_score >= 65:
            status = 'good'
        elif final_score >= 50:
            status = 'fair'
        else:
            status = 'needs_attention'

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'overallScore': final_score,
            'status': status,
            'components': {k: round(v, 1) for k, v in scores.items()},
            'weights': weights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/briefing', methods=['GET'])
def get_briefing():
    """Get executive briefing data - combines all sources including Donna QA pipeline"""
    try:
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        oee = 0
        lines = 0
        mtd_revenue = 0
        total_inventory = 0
        concerns = []
        quality_pipeline = None

        # Operations data (Snowflake)
        try:
            plant_data = snowflake_client.query(SNOWFLAKE_QUERIES['plant_oee'])
            if plant_data and len(plant_data) > 0:
                plant = plant_data[0]
                oee = plant.get('PLANT_OEE') or 0
                lines = plant.get('LINES_REPORTING') or 0
        except Exception as e:
            print(f"Snowflake OEE query failed: {e}")

        # Red flags (Snowflake)
        try:
            low_oee = snowflake_client.query(SNOWFLAKE_QUERIES['lines_below_target'])
            if low_oee:
                for line in low_oee[:3]:
                    line_name = line.get('LINE_NAME', 'Line')
                    avg_oee = line.get('AVG_OEE', 0)
                    concerns.append(f"{line_name} OEE at {avg_oee}%")
        except Exception as e:
            print(f"Snowflake red flags query failed: {e}")

        # Financial data (Sage X3)
        try:
            mtd = sage_client.query(SQL_QUERIES['mtd_revenue'])
            if mtd and len(mtd) > 0:
                mtd_revenue = mtd[0].get('MTDRevenue') or 0
        except Exception as e:
            print(f"SQL MTD revenue query failed: {e}")

        try:
            inventory = sage_client.query(SQL_QUERIES['inventory_value'])
            if inventory:
                total_inventory = sum((row.get('TotalValue') or 0) for row in inventory)
        except Exception as e:
            print(f"SQL inventory query failed: {e}")

        # Quality pipeline (Donna QA — localhost:5002)
        try:
            req = urllib.request.Request(
                "http://localhost:5002/api/preshipment/summary",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                quality_pipeline = json.loads(resp.read().decode())
                # Add quality concerns if there are fire drills
                overdue = quality_pipeline.get('overdue', 0)
                failing = quality_pipeline.get('failing', 0)
                if overdue > 0:
                    concerns.append(f"{overdue} batch{'es' if overdue != 1 else ''} overdue for release")
                if failing > 0:
                    concerns.append(f"{failing} batch{'es' if failing != 1 else ''} failing preshipment checks")
        except Exception:
            pass  # Donna not running — no quality pipeline data

        # Build summary
        summary = f"Plant OEE is at {oee}% with {lines} lines reporting. "
        if mtd_revenue > 0:
            summary += f"Month-to-date revenue is ${mtd_revenue:,.0f}. "
        else:
            summary += "Revenue data is being updated. "
        if concerns:
            summary += f"Items needing attention: {', '.join(concerns)}."
        else:
            summary += "All systems operating normally."

        result = {
            'timestamp': datetime.now().isoformat(),
            'greeting': f"{greeting}, Dennis",
            'briefing': summary,
            'kpis': {
                'oee': oee,
                'lines': lines,
                'revenue_mtd': mtd_revenue,
                'inventory': total_inventory
            },
            'concerns': concerns
        }

        if quality_pipeline:
            result['quality_pipeline'] = quality_pipeline

        return jsonify(result)

    except Exception as e:
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'greeting': f"{greeting}, Dennis",
            'briefing': "Executive briefing is loading. Some data sources are still connecting.",
            'kpis': {'oee': 0, 'lines': 0, 'revenue_mtd': 0, 'inventory': 0},
            'concerns': [],
            'error': str(e)
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check — reports status of all connected systems"""
    # Check Donna availability
    donna_status = 'offline'
    try:
        req = urllib.request.Request("http://localhost:5002/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            donna_status = 'online'
    except Exception:
        pass

    # Check Jackie availability
    jackie_status = 'offline'
    try:
        req = urllib.request.Request("http://localhost:5001/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            jackie_status = 'online'
    except Exception:
        pass

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'api': 'online',
            'sheldon_brain': 'online' if BRAIN_AVAILABLE else 'offline',
            'snowflake': 'configured',
            'sage_x3': 'configured',
            'openai': 'configured' if OPENAI_AVAILABLE else 'not_configured',
            'claude': 'configured' if ANTHROPIC_API_KEY else 'not_configured',
            'donna_qa': donna_status,
            'jackie_analytics': jackie_status,
            'ms_graph': 'configured'
        }
    })

# ============================================
# SHELDON BRAIN — Chief of Staff AI Engine
# ============================================
# Claude-powered agent with tool-use access to ALL data systems:
# Snowflake/Redzone, Sage X3, Donna QA, Jackie Analytics, MS Graph
#
# Falls back to OpenAI gpt-4o-mini if Claude is unavailable.

# Load Anthropic API key — check .env (already parsed above), then Jackie config as fallback
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    _jackie_config_paths = [
        os.path.join(_script_dir, 'config.json'),
        r"E:\Business\AMERIQUAL PROJECT TRACKER\Current Projects\Defect Tracking Automation\config.json",
    ]
    for jackie_config_path in _jackie_config_paths:
        if os.path.exists(jackie_config_path):
            try:
                with open(jackie_config_path, 'r') as f:
                    jackie_config = json.load(f)
                    ANTHROPIC_API_KEY = jackie_config.get('anthropic_api_key')
                    if ANTHROPIC_API_KEY:
                        break
            except Exception:
                pass

# Initialize SHELDON Brain
BRAIN_AVAILABLE = False
sheldon_brain = None
try:
    from sheldon_brain import SheldonBrain
    if ANTHROPIC_API_KEY:
        sheldon_brain = SheldonBrain(ANTHROPIC_API_KEY, snowflake_client, sage_client, graph_client, internal_db=internal_db)
        sheldon_brain.snowflake_queries = SNOWFLAKE_QUERIES
        sheldon_brain.sql_queries = SQL_QUERIES
        sheldon_brain.dept_kpi_queries = DEPT_KPI_QUERIES
        BRAIN_AVAILABLE = True
        print("SHELDON Brain: ONLINE (Claude-powered Chief of Staff)")
    else:
        print("SHELDON Brain: OFFLINE (no Anthropic API key found)")
except ImportError as e:
    print(f"SHELDON Brain: OFFLINE (import error: {e})")

# Keep old OpenAI system prompt as fallback
SHELDON_SYSTEM_PROMPT = """You are SHELDON, an executive intelligence system for Dennis Straub, President & CEO of AmeriQual Foods.
Be direct and professional, like a trusted executive advisor. Focus on financial performance, operations, risks, and opportunities.
Key metrics: OEE, Revenue, Inventory, AR Days, Gross Margin. Facilities: FD1, PK1, TP1.
Current data context will be provided with each message."""

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI chat endpoint — uses Claude Brain (primary) or OpenAI (fallback)"""
    try:
        data = request.get_json()
        user_message = data.get('command', data.get('message', ''))
        context = data.get('context', {})

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # PRIMARY: Use SHELDON Brain (Claude with tool-use)
        if BRAIN_AVAILABLE and sheldon_brain:
            result = sheldon_brain.process_message(user_message, dashboard_context=context)
            return jsonify({
                'message': result['response'],
                'response': result['response'],
                'tools_used': result.get('tools_used', []),
                'data_sources': result.get('data_sources', []),
                'engine': 'claude_chief_of_staff',
                'timestamp': result['timestamp']
            })

        # FALLBACK: Use OpenAI gpt-4o-mini (no tool-use)
        if OPENAI_AVAILABLE:
            context_info = ""
            if context and 'kpis' in context:
                kpis = context['kpis']
                context_info = f"\nDashboard: OEE {kpis.get('oee', 'N/A')}%, Revenue MTD ${kpis.get('revenue', 'N/A')}, Inventory ${kpis.get('inventory', 'N/A')}"

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SHELDON_SYSTEM_PROMPT + context_info},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            ai_response = response.choices[0].message.content
            return jsonify({
                'message': ai_response,
                'response': ai_response,
                'engine': 'openai_fallback',
                'timestamp': datetime.now().isoformat()
            })

        return jsonify({
            'error': 'No AI engine available',
            'message': 'Neither Claude Brain nor OpenAI is configured. Check API keys.'
        }), 503

    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'I encountered an error processing your request. Please try again.'
        }), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming AI chat endpoint — sends Server-Sent Events for progressive rendering."""
    try:
        data = request.get_json()
        user_message = data.get('command', data.get('message', ''))
        context = data.get('context', {})

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        if not BRAIN_AVAILABLE or not sheldon_brain:
            return jsonify({'error': 'SHELDON Brain not available'}), 503

        def generate():
            try:
                for event in sheldon_brain.process_message_stream(user_message, dashboard_context=context):
                    yield event
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'text': str(e)[:200]})}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*'
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prefetch', methods=['GET'])
def prefetch_data():
    """Pre-fetch all common data for Claude context injection.
    Called once on page load so Claude doesn't need tool calls for basic questions.
    Uses threading to parallelize all queries — typically completes in 10-15s."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    result = {}

    def fetch_plant_oee():
        data = snowflake_client.query(SNOWFLAKE_QUERIES.get('plant_oee', ''))
        return 'plantOEE', data[0] if data else None

    def fetch_oee_by_line():
        data = snowflake_client.query(SNOWFLAKE_QUERIES.get('oee_by_line', ''))
        return 'oeeByLine', data[:15] if data else None

    def fetch_red_flags():
        data = snowflake_client.query(SNOWFLAKE_QUERIES.get('lines_below_target', ''))
        return 'redFlags', data if data else None

    def fetch_top_downtime():
        data = snowflake_client.query(SNOWFLAKE_QUERIES.get('top_downtime', ''))
        return 'topDowntime', data[:10] if data else None

    def fetch_financials():
        financials = {}
        for key in ['mtd_revenue', 'ytd_revenue', 'gross_margin_mtd', 'cash_position', 'ar_aging']:
            sql = SQL_QUERIES.get(key, '')
            if sql:
                try:
                    data = sage_client.query(sql)
                    financials[key] = data[0] if data and len(data) == 1 else data
                except Exception:
                    pass
        return 'financials', financials if financials else None

    def fetch_inventory():
        data = sage_client.query(SQL_QUERIES.get('inventory_value', ''))
        return 'inventory', data if data else None

    def fetch_quality_pipeline():
        req = urllib.request.Request(
            "http://localhost:5002/api/preshipment/summary",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 'qualityPipeline', json.loads(resp.read().decode())

    def fetch_sop_status():
        from sheldon_brain import SOPReader
        data = SOPReader.read_sop_snapshot()
        if 'error' not in data:
            return 'sopStatus', data
        return 'sopStatus', None

    tasks = [
        fetch_plant_oee, fetch_oee_by_line, fetch_red_flags,
        fetch_top_downtime, fetch_financials, fetch_inventory,
        fetch_quality_pipeline, fetch_sop_status
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fn): fn.__name__ for fn in tasks}
        for future in as_completed(futures, timeout=45):
            try:
                key, value = future.result()
                result[key] = value
            except Exception:
                pass  # Individual failures are non-critical

    # Fill any missing keys with None
    for key in ['plantOEE', 'oeeByLine', 'redFlags', 'topDowntime', 'financials', 'inventory', 'qualityPipeline', 'sopStatus']:
        result.setdefault(key, None)

    return jsonify(result)


# ============================================
# CHIEF OF STAFF ENDPOINTS
# ============================================

@app.route('/api/chief-of-staff/brief', methods=['GET'])
def chief_of_staff_brief():
    """Generate comprehensive Chief of Staff morning briefing.
    Pulls from ALL data systems and synthesizes with Claude AI."""
    if not BRAIN_AVAILABLE:
        return jsonify({'error': 'SHELDON Brain not available', 'message': 'Claude AI engine required for Chief of Staff briefing.'}), 503

    try:
        result = sheldon_brain.generate_morning_brief()
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'briefing': result['response'],
            'tools_used': result.get('tools_used', []),
            'data_sources': result.get('data_sources', []),
            'engine': 'claude_chief_of_staff'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chief-of-staff/clear-history', methods=['POST'])
def clear_chat_history():
    """Clear SHELDON's conversation memory."""
    if sheldon_brain:
        sheldon_brain.clear_history()
    return jsonify({'status': 'ok', 'message': 'Conversation history cleared.'})

@app.route('/api/quality/pipeline', methods=['GET'])
def quality_pipeline():
    """Get batch release pipeline from Donna QA system."""
    pipeline = {}
    donna_endpoints = {
        "summary": "/api/preshipment/summary",
        "alerts": "/api/preshipment/alerts",
    }

    donna_available = False
    for key, path in donna_endpoints.items():
        try:
            req = urllib.request.Request(
                f"http://localhost:5002{path}",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pipeline[key] = json.loads(resp.read().decode())
                donna_available = True
        except Exception as e:
            pipeline[f"{key}_error"] = str(e)[:100]

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'available': donna_available,
        'pipeline': pipeline,
        'source': 'donna_qa_system'
    })

@app.route('/api/quality/defects', methods=['GET'])
def quality_defects():
    """Get defect summary — direct Snowflake query using Jackie's proven patterns."""
    try:
        from sheldon_brain import _get_production_date, _to_julian
        prod_date = _get_production_date()
        julian_today = _to_julian(prod_date)

        query = f"""
            SELECT "dataItemName" AS defect_type,
                   SUM(TRY_TO_NUMBER("values")) AS total_count,
                   COUNT(DISTINCT "placeName") AS machines_affected,
                   LISTAGG(DISTINCT "placeName", ', ') WITHIN GROUP (ORDER BY "placeName") AS machine_list
            FROM ZGRZDCXCHH_DB."ameriqual-org"."v_completeddataitem"
            WHERE "runId" = '{julian_today}'
              AND "void" = 'False'
              AND "createdDate" >= DATEADD(year, -9, CURRENT_DATE())
              AND "dataSheetName" NOT LIKE '%Machine Reject%'
              AND "dataSheetName" NOT LIKE '%Changeover%'
              AND "dataSheetName" NOT LIKE '%Retort Load%'
              AND "dataItemName" NOT IN (
                  'Total Number of Retort Pouches', 'Total Number of Defects',
                  'Code Time Frame', 'Is this the last code for the run?')
              AND TRY_TO_NUMBER("values") > 0
            GROUP BY "dataItemName"
            HAVING SUM(TRY_TO_NUMBER("values")) > 0
            ORDER BY total_count DESC
            LIMIT 20
        """
        data = snowflake_client.query(query)
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'julian_date': julian_today,
            'defects': data,
            'source': 'snowflake_redzone'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# EXECUTIVES CALENDAR ENDPOINTS
# ============================================

# Executive data - update this list with actual executives
EXECUTIVES = [
    {
        'id': 'dennis',
        'name': 'Dennis Straub',
        'initials': 'DS',
        'title': 'President & CEO',
        'email': 'dstraub@ameriqual.com',
        'phone': '(812) 867-1300 x10231',
        'status': 'available'
    },
    {
        'id': 'mirsada',
        'name': 'Mirsada Salihovic',
        'initials': 'MS',
        'title': 'SVP of Human Resources',
        'email': 'msalihovic@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
    {
        'id': 'tim',
        'name': 'Tim Sholtis',
        'initials': 'TS',
        'title': 'Executive',
        'email': 'tsholtis@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
    {
        'id': 'wes',
        'name': 'Wes Blankenberger',
        'initials': 'WB',
        'title': 'Operations',
        'email': 'wblankenberger@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
    {
        'id': 'john',
        'name': 'John Knapp',
        'initials': 'JK',
        'title': 'Executive',
        'email': 'jknapp@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
    {
        'id': 'chris',
        'name': 'Chris Brack',
        'initials': 'CB',
        'title': 'Executive',
        'email': 'cbrack@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
    {
        'id': 'shane',
        'name': 'Shane Shepherd',
        'initials': 'SS',
        'title': 'QA',
        'email': 'sshepherd@ameriqual.com',  # TODO: confirm exact email
        'status': 'available'
    },
]

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get calendar events for executives from Microsoft Graph

    Query parameters:
    - start: ISO date string for range start
    - end: ISO date string for range end
    - executive: executive ID or 'all'
    """
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        executive_filter = request.args.get('executive', 'all')

        # Parse date range (default to today + 30 days)
        if start_str:
            start_date = datetime.fromisoformat(start_str.replace('Z', '').split('+')[0])
        else:
            start_date = datetime.now().replace(hour=0, minute=0, second=0)

        if end_str:
            end_date = datetime.fromisoformat(end_str.replace('Z', '').split('+')[0])
        else:
            end_date = start_date + timedelta(days=30)

        all_events = []

        # Get events for each executive
        execs_to_query = EXECUTIVES if executive_filter == 'all' else [e for e in EXECUTIVES if e['id'] == executive_filter]

        for exec_info in execs_to_query:
            try:
                graph_events = graph_client.get_user_calendar(exec_info['email'], start_date, end_date)

                for event in graph_events:
                    # Transform Graph API format to our format
                    start_dt = event.get('start', {})
                    end_dt = event.get('end', {})
                    location = event.get('location', {})
                    organizer = event.get('organizer', {}).get('emailAddress', {})

                    transformed = {
                        'id': event.get('id', ''),
                        'title': event.get('subject', 'No Subject'),
                        'start': start_dt.get('dateTime', ''),
                        'end': end_dt.get('dateTime', ''),
                        'location': location.get('displayName', '') if isinstance(location, dict) else str(location),
                        'organizer': organizer.get('name', ''),
                        'organizerEmail': organizer.get('address', ''),
                        'executiveId': exec_info['id'],
                        'executiveName': exec_info['name'],
                        'isAllDay': event.get('isAllDay', False),
                        'showAs': event.get('showAs', 'busy'),
                        'attendees': [
                            {'name': a.get('emailAddress', {}).get('name', ''),
                             'email': a.get('emailAddress', {}).get('address', '')}
                            for a in event.get('attendees', [])
                        ]
                    }
                    all_events.append(transformed)

            except Exception as e:
                print(f"Error fetching calendar for {exec_info['email']}: {e}")

        # Sort by start time
        all_events.sort(key=lambda x: x.get('start', ''))

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'events': all_events,
            'executives': EXECUTIVES,
            'source': 'microsoft_graph',
            'dateRange': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })

    except Exception as e:
        print(f"Calendar events error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/executives', methods=['GET'])
def get_executives():
    """Get list of executives with their current status from Microsoft Graph"""
    try:
        # Get user IDs for presence lookup
        exec_with_status = []

        for exec_info in EXECUTIVES:
            exec_copy = exec_info.copy()

            # Try to get presence status
            try:
                # Get user ID from Graph
                users = graph_client.get_users()
                user_match = next((u for u in users if u.get('mail', '').lower() == exec_info['email'].lower()), None)

                if user_match:
                    user_id = user_match.get('id')
                    presence = graph_client.get_presence([user_id])
                    availability = presence.get(user_id, 'Unknown')

                    # Map Graph presence to our status
                    status_map = {
                        'Available': 'available',
                        'Busy': 'busy',
                        'DoNotDisturb': 'dnd',
                        'Away': 'away',
                        'Offline': 'offline',
                        'BeRightBack': 'away'
                    }
                    exec_copy['status'] = status_map.get(availability, 'unknown')
                    exec_copy['presenceDetail'] = availability

            except Exception as e:
                print(f"Presence lookup error for {exec_info['name']}: {e}")
                exec_copy['status'] = 'unknown'

            exec_with_status.append(exec_copy)

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'executives': exec_with_status,
            'source': 'microsoft_graph'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_sample_calendar_events(start_date, end_date, executive_filter):
    """Generate sample calendar events for demonstration"""
    events = []
    today = datetime.now()

    # Sample events for demonstration
    sample_data = [
        {
            'id': '1',
            'title': 'Executive Team Meeting',
            'start': today.replace(hour=9, minute=0).isoformat(),
            'end': today.replace(hour=10, minute=30).isoformat(),
            'location': 'Conference Room A',
            'organizer': 'Dennis Straub',
            'executiveId': 'dennis',
            'attendees': [
                {'name': 'Dennis Straub', 'email': 'dstraub@ameriqual.com'},
                {'name': 'CFO', 'email': 'cfo@ameriqual.com'},
                {'name': 'VP Operations', 'email': 'vpops@ameriqual.com'}
            ],
            'description': 'Weekly executive team sync'
        },
        {
            'id': '2',
            'title': 'Client Meeting - DSCP Review',
            'start': today.replace(hour=14, minute=0).isoformat(),
            'end': today.replace(hour=15, minute=30).isoformat(),
            'location': 'Teams Call',
            'organizer': 'Dennis Straub',
            'executiveId': 'dennis',
            'client': 'Defense Supply Center Philadelphia',
            'attendees': [
                {'name': 'Dennis Straub', 'email': 'dstraub@ameriqual.com'},
                {'name': 'John Smith', 'email': 'jsmith@dscp.dla.mil'}
            ],
            'description': 'Quarterly contract review with DSCP customer'
        },
        {
            'id': '3',
            'title': 'Board Preparation',
            'start': (today + timedelta(days=1)).replace(hour=10, minute=0).isoformat(),
            'end': (today + timedelta(days=1)).replace(hour=12, minute=0).isoformat(),
            'location': 'Office',
            'organizer': 'Dennis Straub',
            'executiveId': 'dennis',
            'description': 'Prepare materials for upcoming board meeting'
        },
        {
            'id': '4',
            'title': 'Plant Tour - Prospective Customer',
            'start': (today + timedelta(days=2)).replace(hour=13, minute=0).isoformat(),
            'end': (today + timedelta(days=2)).replace(hour=16, minute=0).isoformat(),
            'location': 'FD1 Facility',
            'organizer': 'VP Sales',
            'executiveId': 'dennis',
            'client': 'New Customer Prospect',
            'attendees': [
                {'name': 'Dennis Straub', 'email': 'dstraub@ameriqual.com'},
                {'name': 'VP Sales', 'email': 'vpsales@ameriqual.com'},
                {'name': 'Prospect Contact', 'email': 'contact@prospect.com'}
            ],
            'description': 'Facility tour for prospective institutional food services customer'
        },
        {
            'id': '5',
            'title': 'Travel - Industry Conference',
            'start': (today + timedelta(days=5)).replace(hour=8, minute=0).isoformat(),
            'end': (today + timedelta(days=7)).replace(hour=18, minute=0).isoformat(),
            'location': 'Chicago, IL',
            'organizer': 'Dennis Straub',
            'executiveId': 'dennis',
            'description': 'National Food Manufacturing Conference - travel and attendance'
        }
    ]

    # Filter by executive if specified
    if executive_filter and executive_filter != 'all':
        sample_data = [e for e in sample_data if e.get('executiveId') == executive_filter]

    return sample_data

# ============================================
# MAIN
# ============================================

@app.route('/')
def serve_frontend():
    """Serve the SHELDON frontend."""
    return send_from_directory(_script_dir, 'SHELDON.html')

if __name__ == '__main__':
    print("=" * 60)
    print("  S H E L D O N")
    print("  Chief of Staff AI — Executive Intelligence System")
    print("=" * 60)
    print(f"  Server: http://localhost:5000")
    print()
    print("  AI ENGINE STATUS:")
    print(f"    Claude Brain (Chief of Staff): {'ONLINE' if BRAIN_AVAILABLE else 'OFFLINE'}")
    print(f"    OpenAI (Fallback):             {'ONLINE' if OPENAI_AVAILABLE else 'OFFLINE'}")
    print()
    print("  CHIEF OF STAFF ENDPOINTS:")
    print("    POST /api/chat                    - AI chat (Claude w/ tool-use)")
    print("    GET  /api/chief-of-staff/brief    - Morning briefing (all systems)")
    print("    POST /api/chief-of-staff/clear-history - Clear conversation memory")
    print()
    print("  OPERATIONS (Snowflake/Redzone):")
    print("    GET /api/kpi/live                 - Plant OEE & production")
    print("    GET /api/redflags                 - Lines below target")
    print("    GET /api/operations/downtime      - Downtime breakdown")
    print("    GET /api/operations/labor         - Labor productivity")
    print("    GET /api/operations/trend         - Hourly OEE trend")
    print("    GET /api/operations/active-lines  - Currently producing")
    print()
    print("  QUALITY (Snowflake + Donna QA):")
    print("    GET /api/quality/summary          - Quality metrics")
    print("    GET /api/quality/defects          - Defect types (today)")
    print("    GET /api/quality/pipeline         - Batch release pipeline (Donna)")
    print()
    print("  FINANCIAL (Sage X3):")
    print("    GET /api/financial/revenue        - Revenue (daily/MTD/YTD)")
    print("    GET /api/financial/kpis           - Financial KPIs")
    print("    GET /api/financial/ebitda         - EBITDA estimate")
    print("    GET /api/inventory/kpis           - Inventory by facility")
    print("    GET /api/ar/aging                 - AR aging breakdown")
    print("    GET /api/customers/top            - Top 10 customers")
    print()
    print("  INTELLIGENCE:")
    print("    GET /api/briefing                 - Executive briefing")
    print("    GET /api/health-score             - Business health (0-100)")
    print("    GET /api/health                   - API health check")
    print()
    print("  CALENDAR (MS Graph):")
    print("    GET /api/calendar/events          - Executive calendar")
    print("    GET /api/calendar/executives      - Executive list & presence")
    print()
    print("  PRODUCTION & S&OP:")
    print("    GET  /api/production/schedules     - Production schedules")
    print("    GET  /api/sop/status               - S&OP decision snapshot (demand vs capacity)")
    print("    POST /api/sop/generate             - Trigger S&OP generation")
    print()
    print("  INTEGRATIONS:")
    print("    Jackie (localhost:5001)            - Deep quality analytics")
    print("    Donna  (localhost:5002)            - Batch release pipeline")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=False)
