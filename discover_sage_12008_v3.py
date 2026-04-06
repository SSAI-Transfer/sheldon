"""Get remaining table 12008 rows + ATEXTRA labels with smaller queries"""
import sys, os, json, urllib.request, urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

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
            'grant_type': 'client_credentials', 'client_id': self.client_id,
            'client_secret': self.client_secret, 'scope': self.scope
        }).encode()
        req = urllib.request.Request(
            f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token',
            data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            self._token_expiry = datetime.now() + timedelta(seconds=result.get('expires_in', 3600) - 60)
            return result['access_token']

    def _ensure_token(self):
        if not self._token or not self._token_expiry or datetime.now() >= self._token_expiry:
            self._token = self._get_token()

    def query(self, sql):
        self._ensure_token()
        query_body = json.dumps({'server': self.server, 'database': self.database, 'sqlQuery': sql}).encode()
        req = urllib.request.Request(self.power_automate_url, data=query_body,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self._token}'})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                if isinstance(result, dict) and 'Table1' in result:
                    return result['Table1']
                elif isinstance(result, list):
                    return result
                return [result] if result else []
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ''
            print(f"  HTTP {e.code}: {body[:300]}")
            return []

sage = SageX3Client()

# Get remaining 12008 rows (after PACKAGECAPISSUE alphabetically)
print("=== TABLE 12008 REMAINING ROWS ===")
results = sage.query("""
    SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, ENAFLG_0
    FROM AMQ.ATABDIV
    WHERE NUMTAB_0 = 12008 AND CODE_0 > 'PACKAGECAPISSUE'
    ORDER BY CODE_0
""")
if results:
    print(f"{len(results)} rows")
    for i, row in enumerate(results):
        print(f"  {row['CODE_0']}")
else:
    print("No results")

# Try ATEXTRA with just table 12008
print("\n=== ATEXTRA LABELS (12008 only, limited columns) ===")
results = sage.query("""
    SELECT TOP 60 NUMTAB_0, CODE_0, TEXTE_0
    FROM AMQ.ATEXTRA
    WHERE NUMTAB_0 = 12008 AND LNG_0 = 'ENG'
    ORDER BY CODE_0
""")
if results:
    print(f"{len(results)} rows")
    for row in results:
        print(f"  {row['CODE_0']} -> {row.get('TEXTE_0', '?')}")
else:
    print("No results - trying without LNG filter...")
    results = sage.query("""
        SELECT TOP 10 * FROM AMQ.ATEXTRA WHERE NUMTAB_0 = 12008
    """)
    if results:
        print(f"Cols: {list(results[0].keys())}")
        for row in results[:5]:
            print(f"  {json.dumps(row, default=str)}")
    else:
        print("Still no results")

# Also get ATEXTRA for 12006 (the action/disposition codes)
print("\n=== ATEXTRA LABELS (12006 - actions/dispositions) ===")
results = sage.query("""
    SELECT TOP 30 CODE_0, TEXTE_0
    FROM AMQ.ATEXTRA
    WHERE NUMTAB_0 = 12006 AND LNG_0 = 'ENG'
    ORDER BY CODE_0
""")
if results:
    print(f"{len(results)} rows")
    for row in results:
        print(f"  {row['CODE_0']} -> {row.get('TEXTE_0', '?')}")
else:
    print("No results")

# Check where these codes are actually USED - STOQUAL or stock quality records
print("\n=== STOQUAL COLUMNS ===")
results = sage.query("SELECT TOP 1 * FROM AMQ.STOQUAL")
if results:
    print(f"Cols: {list(results[0].keys())}")
    print(json.dumps(results[0], default=str))
else:
    print("Empty or no access")

# Check if there's a quality request/order table that uses these codes
print("\n=== QUALITY REQUEST TABLE (QCLOT) ===")
results = sage.query("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = 'AMQ' AND (
        TABLE_NAME LIKE '%QCLOT%' OR TABLE_NAME LIKE '%QREQ%'
        OR TABLE_NAME LIKE '%STOJOU%' OR TABLE_NAME LIKE '%STOLOT%'
        OR TABLE_NAME LIKE '%QUALREQ%'
    )
""")
if results:
    for row in results:
        print(f"  {row['TABLE_NAME']}")
else:
    print("None found")

print("\nDONE")
