"""
FTQ Query Test Script
Run this on the company laptop (on AmeriQual network) to validate
all FTQ queries against the CI database before integrating into SHELDON.

Usage:
    python test_ftq.py
"""

import sys

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)

# Try ODBC Driver 17 first (company laptop), fall back to generic
DRIVERS = ['ODBC Driver 17 for SQL Server', 'SQL Server']
DRIVER = None
for d in DRIVERS:
    if d in pyodbc.drivers():
        DRIVER = d
        break

if not DRIVER:
    print(f"ERROR: No SQL Server ODBC driver found. Available: {pyodbc.drivers()}")
    sys.exit(1)

CONN_STR = (
    f'DRIVER={{{DRIVER}}};'
    'SERVER=AQFDB6;'
    'DATABASE=CI;'
    'UID=SocialScaleReadOnly;'
    'PWD=socialscale.25;'
    'TrustServerCertificate=yes;'
)

QUERIES = {

    # ── 1. Pre-calculated weekly FTQ (Nic's pipeline) ────────────────
    'weekly_precalc': """
        SELECT weekVal, valueStream, descr, numVal
        FROM db_accessadmin.KPI_QA_CalcWeekly
        WHERE weekVal >= DATEADD(month, -3, GETDATE())
          AND groupVal = 'FTQ'
        ORDER BY weekVal DESC
    """,

    # ── 2. Self-calculated plant-wide weekly FTQ ─────────────────────
    'weekly_calculated': """
        SELECT
            DATEADD(day, 1-DATEPART(weekday, dateVal), CAST(dateVal AS DATE)) AS week_start,
            SUM(prodPallets) AS total_pallets,
            SUM(badPallets) AS bad_pallets,
            SUM(prodEaches) AS total_eaches,
            SUM(badEaches) AS bad_eaches,
            CASE WHEN SUM(prodPallets) > 0
                 THEN ROUND((1.0 - CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets)) * 100, 2)
                 ELSE 100.0 END AS ftq_pct
        FROM db_accessadmin.KPI_QA_OverallQuality_Contract
        WHERE dateVal >= DATEADD(month, -3, GETDATE())
        GROUP BY DATEADD(day, 1-DATEPART(weekday, dateVal), CAST(dateVal AS DATE))
        ORDER BY week_start DESC
    """,

    # ── 3. FTQ by contract ───────────────────────────────────────────
    'by_contract': """
        SELECT
            cont,
            SUM(prodPallets) AS total_pallets,
            SUM(badPallets) AS bad_pallets,
            CASE WHEN SUM(prodPallets) > 0
                 THEN ROUND((1.0 - CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets)) * 100, 2)
                 ELSE 100.0 END AS ftq_pct,
            SUM(prodEaches) AS total_eaches,
            SUM(badEaches) AS bad_eaches
        FROM db_accessadmin.KPI_QA_OverallQuality_Contract
        WHERE dateVal >= DATEADD(month, -3, GETDATE())
        GROUP BY cont
        ORDER BY bad_pallets DESC
    """,

    # ── 4. Issue category breakdown (auto-classified) ────────────────
    'issue_breakdown': """
        SELECT
            CASE
                WHEN issue LIKE '%DESTROY%' OR issue LIKE '%destroy%'       THEN 'Destroy'
                WHEN issue LIKE '%REWORK%' OR issue LIKE '%rework%'         THEN 'Rework'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'Customer Requested'
                WHEN issue LIKE '%RELEASE%' OR issue LIKE '%release%'       THEN 'Release'
                WHEN issue LIKE '%NET WEIGHT%' OR issue LIKE '%net weight%' THEN 'Net Weight'
                WHEN issue LIKE '%LEAKER%' OR issue LIKE '%leaker%'         THEN 'Leakers'
                WHEN issue LIKE '%FOREIGN%' OR issue LIKE '%foreign%'       THEN 'Foreign Material'
                WHEN issue LIKE '%LABEL%' OR issue LIKE '%label%'           THEN 'Labeling'
                WHEN issue LIKE '%CODE%' OR issue LIKE '%code%'             THEN 'Coding'
                WHEN issue LIKE '%VISUAL%' OR issue LIKE '%visual%'         THEN 'Visual Defect'
                WHEN issue LIKE '%QUALITY%' OR issue LIKE '%quality%'       THEN 'Product Quality'
                ELSE 'Other'
            END AS issue_category,
            COUNT(*) AS occurrences,
            SUM(issueQtyPal) AS issue_pallets,
            SUM(issueQtyEa) AS issue_eaches,
            COUNT(DISTINCT cont) AS contracts_affected,
            COUNT(DISTINCT lot) AS lots_affected
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -3, GETDATE())
        GROUP BY CASE
                WHEN issue LIKE '%DESTROY%' OR issue LIKE '%destroy%'       THEN 'Destroy'
                WHEN issue LIKE '%REWORK%' OR issue LIKE '%rework%'         THEN 'Rework'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'Customer Requested'
                WHEN issue LIKE '%RELEASE%' OR issue LIKE '%release%'       THEN 'Release'
                WHEN issue LIKE '%NET WEIGHT%' OR issue LIKE '%net weight%' THEN 'Net Weight'
                WHEN issue LIKE '%LEAKER%' OR issue LIKE '%leaker%'         THEN 'Leakers'
                WHEN issue LIKE '%FOREIGN%' OR issue LIKE '%foreign%'       THEN 'Foreign Material'
                WHEN issue LIKE '%LABEL%' OR issue LIKE '%label%'           THEN 'Labeling'
                WHEN issue LIKE '%CODE%' OR issue LIKE '%code%'             THEN 'Coding'
                WHEN issue LIKE '%VISUAL%' OR issue LIKE '%visual%'         THEN 'Visual Defect'
                WHEN issue LIKE '%QUALITY%' OR issue LIKE '%quality%'       THEN 'Product Quality'
                ELSE 'Other'
            END
        ORDER BY issue_pallets DESC
    """,

    # ── 5. Every distinct issue string (Brandon's scrub list) ────────
    'issue_values': """
        SELECT issue, COUNT(*) AS cnt
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -3, GETDATE())
        GROUP BY issue
        ORDER BY cnt DESC
    """,

    # ── 6. Worst items (repeat offenders) ────────────────────────────
    'worst_items': """
        SELECT TOP 20
            item, cont,
            COUNT(*) AS issue_count,
            COUNT(DISTINCT lot) AS lots_affected,
            SUM(issueQtyPal) AS total_bad_pallets,
            SUM(prodQtyPal) AS total_prod_pallets,
            CASE WHEN SUM(prodQtyPal) > 0
                 THEN ROUND((1.0 - CAST(SUM(issueQtyPal) AS FLOAT) / SUM(prodQtyPal)) * 100, 2)
                 ELSE 100.0 END AS ftq_pct
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -3, GETDATE())
        GROUP BY item, cont
        HAVING SUM(issueQtyPal) > 0
        ORDER BY total_bad_pallets DESC
    """,

    # ── 7. Recent detail rows (drill-down) ───────────────────────────
    'recent_detail': """
        SELECT TOP 50
            dateVal, cont, item, lot,
            issueQtyPal, issueQtyEa, prodQtyPal, prodQtyEa,
            issue,
            CASE WHEN prodQtyPal > 0
                 THEN ROUND((1.0 - CAST(issueQtyPal AS FLOAT) / prodQtyPal) * 100, 2)
                 ELSE 100.0 END AS item_ftq_pct
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -1, GETDATE())
        ORDER BY dateVal DESC, issueQtyPal DESC
    """,
}


def run_query(label, sql):
    print(f'\n{"=" * 70}')
    print(f'  {label}')
    print(f'{"=" * 70}')
    try:
        conn = pyodbc.connect(CONN_STR, timeout=30)
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        print(f'  Columns: {columns}')
        print(f'  Rows: {len(rows)}')
        print()

        # Print as a simple table
        if rows:
            col_widths = []
            for i, col in enumerate(columns):
                max_val = max(len(str(row[i])) for row in rows[:20])
                col_widths.append(max(len(col), min(max_val, 40)))

            header = '  ' + ' | '.join(col.ljust(w) for col, w in zip(columns, col_widths))
            print(header)
            print('  ' + '-+-'.join('-' * w for w in col_widths))

            for row in rows[:20]:
                vals = []
                for i, val in enumerate(row):
                    s = str(val) if val is not None else ''
                    vals.append(s[:40].ljust(col_widths[i]))
                print('  ' + ' | '.join(vals))

            if len(rows) > 20:
                print(f'\n  ... and {len(rows) - 20} more rows')

        return rows

    except Exception as e:
        print(f'  ERROR: {e}')
        return []


def main():
    print('=' * 70)
    print('  SHELDON FTQ Query Test')
    print(f'  Driver: {DRIVER}')
    print(f'  Server: AQFDB6 / Database: CI')
    print('=' * 70)

    # Test connection first
    print('\nTesting connection...')
    try:
        conn = pyodbc.connect(CONN_STR, timeout=15)
        conn.close()
        print('  Connected successfully!\n')
    except Exception as e:
        print(f'  FAILED: {e}')
        print('\n  Make sure you are on the AmeriQual network.')
        sys.exit(1)

    # Run all queries
    for key, sql in QUERIES.items():
        run_query(key, sql)

    # Comparison check
    print('\n' + '=' * 70)
    print('  VALIDATION: Compare pre-calc vs self-calc FTQ')
    print('=' * 70)
    print('  Look at weekly_precalc (numVal) vs weekly_calculated (ftq_pct)')
    print('  for the same weeks. If they match closely, the raw data is')
    print('  already scrubbed and you can use either source.')
    print('  If they diverge, check issue_breakdown to see which categories')
    print('  need to be excluded from your calculation.')
    print()
    print('  The issue_values query shows every distinct reason string in')
    print('  the database — this is the complete list Brandon would have')
    print('  given you.')
    print()


if __name__ == '__main__':
    main()
