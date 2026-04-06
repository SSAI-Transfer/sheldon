"""
Discover Sage X3 Table 12008 (Diverse/Miscellaneous Table)
Queries ATABDIV, ATEXTRA, and related views to find reason codes.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Reuse the SageX3Client from sheldon_api
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')

class SageX3Client:
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
        self._token = None
        self._token_expiry = None

    def _get_token(self):
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
        if not self._token or not self._token_expiry or datetime.now() >= self._token_expiry:
            self._token = self._get_token()

    def query(self, sql):
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
            body = e.read().decode() if e.fp else ''
            print(f"  HTTP {e.code}: {body[:500]}")
            return []

sage = SageX3Client()

queries = {
    # 1. Direct ATABDIV lookup for table 12008
    "ATABDIV (table 12008 entries)": """
        SELECT TOP 100 *
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12008
        ORDER BY LNGDIV_0, CODIV_0
    """,

    # 2. Try alternate column name
    "ATABDIV alt column": """
        SELECT TOP 100 *
        FROM AMQ.ATABDIV
        WHERE APTS_0 = '12008' OR NUMTAB_0 = '12008'
    """,

    # 3. ATEXTRA for descriptions/labels of table 12008
    "ATEXTRA (table 12008 labels)": """
        SELECT TOP 100 *
        FROM AMQ.ATEXTRA
        WHERE COESSION_0 = '12008' OR ESSION_0 = '12008'
    """,

    # 4. Check what columns ATABDIV has
    "ATABDIV columns": """
        SELECT TOP 1 *
        FROM AMQ.ATABDIV
    """,

    # 5. Check APLSTD (Sage local menu / diverse table definitions)
    "APLSTD table definitions": """
        SELECT TOP 50 *
        FROM AMQ.APLSTD
        WHERE NUMTAB_0 = 12008
    """,

    # 6. Try ATAESSION (diverse table headers)
    "ATABDIV all tables list": """
        SELECT DISTINCT NUMTAB_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 BETWEEN 12000 AND 12999
        ORDER BY NUMTAB_0
    """,

    # 7. Search for quality-related diverse tables
    "Quality diverse tables": """
        SELECT DISTINCT d.NUMTAB_0, d.CODIV_0, d.DESSION_0
        FROM AMQ.ATABDIV d
        WHERE d.DESSION_0 LIKE '%qual%'
           OR d.DESSION_0 LIKE '%reason%'
           OR d.DESSION_0 LIKE '%defect%'
           OR d.DESSION_0 LIKE '%reject%'
           OR d.DESSION_0 LIKE '%hold%'
           OR d.DESSION_0 LIKE '%rework%'
           OR d.CODIV_0 LIKE '%QUAL%'
           OR d.CODIV_0 LIKE '%REJ%'
           OR d.CODIV_0 LIKE '%DEF%'
        ORDER BY d.NUMTAB_0
    """,

    # 8. Try the Sage quality module tables directly
    "Sage quality tables": """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'AMQ'
          AND (TABLE_NAME LIKE '%QUAL%'
            OR TABLE_NAME LIKE '%REJECT%'
            OR TABLE_NAME LIKE '%PREJECT%'
            OR TABLE_NAME LIKE '%SREJECT%'
            OR TABLE_NAME LIKE '%NONCONF%'
            OR TABLE_NAME LIKE '%DEFECT%'
            OR TABLE_NAME LIKE '%ATABDIV%')
        ORDER BY TABLE_NAME
    """,
}

print("=" * 70)
print("SAGE X3 TABLE 12008 DISCOVERY")
print("=" * 70)

for name, sql in queries.items():
    print(f"\n{'-' * 60}")
    print(f"QUERY: {name}")
    print(f"{'-' * 60}")
    try:
        results = sage.query(sql)
        if results:
            print(f"  OK - {len(results)} rows returned")
            if isinstance(results[0], dict):
                print(f"  Columns: {list(results[0].keys())}")
            for i, row in enumerate(results[:25]):
                print(f"  [{i}] {json.dumps(row, default=str)}")
            if len(results) > 25:
                print(f"  ... ({len(results) - 25} more rows)")
        else:
            print("  No results")
    except Exception as e:
        print(f"  Error: {e}")

print(f"\n{'=' * 70}")
print("DONE")
print(f"{'=' * 70}")
