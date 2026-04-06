"""
Targeted discovery of Sage X3 Table 12008 + related quality tables
"""
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
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }).encode()
        req = urllib.request.Request(
            f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token',
            data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}
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

queries = [
    ("Table 12008 - All rows", """
        SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, A4_0, A5_0,
               N1_0, N2_0, ENAFLG_0, UPDDAT_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12008
        ORDER BY CODE_0
    """),
    ("Table 12000 - All rows", """
        SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, A4_0, A5_0,
               N1_0, N2_0, ENAFLG_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12000
        ORDER BY CODE_0
    """),
    ("Table 12005 - All rows", """
        SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, A4_0, A5_0,
               N1_0, N2_0, ENAFLG_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12005
        ORDER BY CODE_0
    """),
    ("Table 12006 - All rows", """
        SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, A4_0, A5_0,
               N1_0, N2_0, ENAFLG_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12006
        ORDER BY CODE_0
    """),
    ("Table 12007 - All rows", """
        SELECT NUMTAB_0, CODE_0, A1_0, A2_0, A3_0, A4_0, A5_0,
               N1_0, N2_0, ENAFLG_0
        FROM AMQ.ATABDIV
        WHERE NUMTAB_0 = 12007
        ORDER BY CODE_0
    """),
    ("CONTQUAL table", """
        SELECT TOP 20 * FROM AMQ.CONTQUAL
    """),
    ("STOQUAL table", """
        SELECT TOP 20 * FROM AMQ.STOQUAL
    """),
    ("ATEXTRA labels for 12008", """
        SELECT * FROM AMQ.ATEXTRA
        WHERE NUMTAB_0 = 12008
        ORDER BY CODE_0
    """),
    ("ATEXTRA labels for 12000-12008", """
        SELECT NUMTAB_0, CODE_0, TEXTE_0
        FROM AMQ.ATEXTRA
        WHERE NUMTAB_0 BETWEEN 12000 AND 12008
        ORDER BY NUMTAB_0, CODE_0
    """),
]

print("=" * 70)
print("SAGE X3 TABLE 12008 TARGETED DISCOVERY")
print("=" * 70)

for name, sql in queries:
    print(f"\n--- {name} ---")
    try:
        results = sage.query(sql)
        if results:
            print(f"  {len(results)} rows")
            if isinstance(results[0], dict):
                print(f"  Cols: {list(results[0].keys())}")
            for i, row in enumerate(results[:30]):
                print(f"  [{i}] {json.dumps(row, default=str)}")
            if len(results) > 30:
                print(f"  ... ({len(results) - 30} more)")
        else:
            print("  No results")
    except Exception as e:
        print(f"  Error: {e}")

print("\nDONE")
