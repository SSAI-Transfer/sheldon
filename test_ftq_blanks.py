"""
FTQ Blank Issues — Full detail of pallets with no reason entered.
Run on company laptop.
"""

import sys

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not installed")
    sys.exit(1)

DRIVERS = ['ODBC Driver 17 for SQL Server', 'SQL Server']
DRIVER = next((d for d in DRIVERS if d in pyodbc.drivers()), None)
if not DRIVER:
    print(f"ERROR: No SQL Server ODBC driver. Available: {pyodbc.drivers()}")
    sys.exit(1)

CONN_STR = (
    f'DRIVER={{{DRIVER}}};'
    'SERVER=AQFDB6;'
    'DATABASE=CI;'
    'UID=SocialScaleReadOnly;'
    'PWD=socialscale.25;'
    'TrustServerCertificate=yes;'
)

SQL = """
    SELECT
        dateVal,
        cont,
        item,
        lot,
        issueQtyPal,
        issueQtyEa,
        prodQtyPal,
        prodQtyEa,
        CASE WHEN issue IS NULL THEN '(NULL)' ELSE '(BLANK)' END AS issue_status,
        timestamp
    FROM db_accessadmin.KPI_QA_OverallQuality_Rework
    WHERE dateVal >= DATEADD(month, -6, GETDATE())
      AND cont != 'ALL'
      AND (issue IS NULL OR LTRIM(RTRIM(issue)) = '')
    ORDER BY dateVal DESC, issueQtyPal DESC
"""

try:
    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()
    cursor.execute(SQL)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    print(f'BLANK/NULL ISSUE ROWS — {len(rows)} total')
    print(f'Columns: {columns}')
    print()

    col_widths = []
    for i, col in enumerate(columns):
        max_val = max(len(str(row[i])[:40]) for row in rows) if rows else 0
        col_widths.append(max(len(col), min(max_val, 40)))

    header = '  ' + ' | '.join(col.ljust(w) for col, w in zip(columns, col_widths))
    print(header)
    print('  ' + '-+-'.join('-' * w for w in col_widths))

    total_pallets = 0
    total_eaches = 0
    for row in rows:
        vals = []
        for i, val in enumerate(row):
            s = str(val) if val is not None else '(NULL)'
            vals.append(s[:40].ljust(col_widths[i]))
        print('  ' + ' | '.join(vals))
        if row[4]:  # issueQtyPal
            total_pallets += int(row[4])
        if row[5]:  # issueQtyEa
            total_eaches += int(row[5])

    print()
    print(f'  TOTAL: {total_pallets} pallets, {total_eaches} eaches across {len(rows)} rows')

    # Summary by contract
    print()
    print('  SUMMARY BY CONTRACT:')
    by_cont = {}
    for row in rows:
        cont = str(row[1])
        pal = int(row[4]) if row[4] else 0
        if cont not in by_cont:
            by_cont[cont] = {'rows': 0, 'pallets': 0}
        by_cont[cont]['rows'] += 1
        by_cont[cont]['pallets'] += pal
    for cont, vals in sorted(by_cont.items(), key=lambda x: -x[1]['pallets']):
        print(f'    {cont}: {vals["pallets"]} pallets across {vals["rows"]} rows')

except Exception as e:
    print(f'ERROR: {e}')
