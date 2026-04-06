"""
FTQ v2 — Corrected queries based on deep-dive findings.
Run on company laptop to validate before deploying to SHELDON.

Key corrections from v1:
  - Data is MONTHLY (not weekly) — grouped by dateVal directly
  - "ALL" rows excluded to avoid double-counting
  - Issue classifier refined based on actual issue_values in DB
  - "Corrected FTQ" subtracts Release/Customer/Submittal from bad pallets
  - Hold cost from OverdueReleases (daily data — most current source)

Usage:
    python test_ftq_v2.py
"""

import sys

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not installed. Run: pip install pyodbc")
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

MONTHS = 6

QUERIES = {

    # ── 1. Monthly plant-wide FTQ trend ──────────────────────────────
    'monthly_trend': """
        SELECT
            dateVal AS month,
            SUM(prodPallets) AS total_pallets,
            SUM(badPallets) AS bad_pallets,
            SUM(prodEaches) AS total_eaches,
            SUM(badEaches) AS bad_eaches,
            CASE WHEN SUM(prodPallets) > 0
                 THEN ROUND((1.0 - CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets)) * 100, 2)
                 ELSE 100.0 END AS ftq_pct
        FROM db_accessadmin.KPI_QA_OverallQuality_Contract
        WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
          AND cont != 'ALL'
        GROUP BY dateVal
        ORDER BY dateVal DESC
    """,

    # ── 2. Corrected FTQ — raw vs adjusted ──────────────────────────
    'monthly_corrected': """
        SELECT
            c.dateVal AS month,
            c.total_pallets,
            c.bad_pallets AS raw_bad_pallets,
            COALESCE(x.excluded_pallets, 0) AS excluded_pallets,
            c.bad_pallets - COALESCE(x.excluded_pallets, 0) AS corrected_bad_pallets,
            CASE WHEN c.total_pallets > 0
                 THEN ROUND((1.0 - CAST(c.bad_pallets AS FLOAT) / c.total_pallets) * 100, 2)
                 ELSE 100.0 END AS raw_ftq_pct,
            CASE WHEN c.total_pallets > 0
                 THEN ROUND((1.0 - CAST((c.bad_pallets - COALESCE(x.excluded_pallets, 0)) AS FLOAT) / c.total_pallets) * 100, 2)
                 ELSE 100.0 END AS corrected_ftq_pct
        FROM (
            SELECT dateVal,
                   SUM(prodPallets) AS total_pallets,
                   SUM(badPallets) AS bad_pallets
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
              AND cont != 'ALL'
            GROUP BY dateVal
        ) c
        LEFT JOIN (
            SELECT dateVal,
                   SUM(issueQtyPal) AS excluded_pallets
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
              AND cont != 'ALL'
              AND (
                  issue IN ('Release', 'Released')
                  OR issue LIKE '%CUSTOMER%%REQUEST%'
                  OR issue = 'Submittal'
                  OR issue = 'qa samples'
              )
            GROUP BY dateVal
        ) x ON c.dateVal = x.dateVal
        ORDER BY c.dateVal DESC
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
        WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
          AND cont != 'ALL'
        GROUP BY cont
        ORDER BY bad_pallets DESC
    """,

    # ── 4. Issue breakdown with FTQ flag ─────────────────────────────
    'issue_breakdown': """
        SELECT
            CASE
                WHEN issue LIKE '%DESTROY%' OR issue LIKE '%destroy%'
                     OR issue LIKE '%visual destroy%'                       THEN 'Destroy'
                WHEN issue LIKE 'Rework%' OR issue LIKE 'RW[0-9]%'         THEN 'Rework / QA Failure'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'Customer Requested'
                WHEN issue IN ('Release', 'Released')                       THEN 'Release'
                WHEN issue = 'Submittal' OR issue = 'qa samples'           THEN 'Submittal (routine)'
                WHEN issue LIKE 'Submittal%FAILURE%'                        THEN 'Submittal (USDA failure)'
                WHEN issue LIKE 'FSIS%'                                     THEN 'FSIS Testing'
                WHEN issue LIKE 'PRODUCT QUALITY%'                          THEN 'Product Quality'
                WHEN issue IS NULL OR LTRIM(RTRIM(issue)) = ''             THEN 'Unclassified (blank)'
                ELSE 'Other'
            END AS issue_category,
            CASE
                WHEN issue IN ('Release', 'Released')                       THEN 'EXCLUDE'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'EXCLUDE'
                WHEN issue = 'Submittal' OR issue = 'qa samples'           THEN 'EXCLUDE'
                ELSE 'COUNTS'
            END AS ftq_flag,
            COUNT(*) AS occurrences,
            SUM(issueQtyPal) AS issue_pallets,
            SUM(issueQtyEa) AS issue_eaches,
            COUNT(DISTINCT cont) AS contracts_affected
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
          AND cont != 'ALL'
        GROUP BY
            CASE
                WHEN issue LIKE '%DESTROY%' OR issue LIKE '%destroy%'
                     OR issue LIKE '%visual destroy%'                       THEN 'Destroy'
                WHEN issue LIKE 'Rework%' OR issue LIKE 'RW[0-9]%'         THEN 'Rework / QA Failure'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'Customer Requested'
                WHEN issue IN ('Release', 'Released')                       THEN 'Release'
                WHEN issue = 'Submittal' OR issue = 'qa samples'           THEN 'Submittal (routine)'
                WHEN issue LIKE 'Submittal%FAILURE%'                        THEN 'Submittal (USDA failure)'
                WHEN issue LIKE 'FSIS%'                                     THEN 'FSIS Testing'
                WHEN issue LIKE 'PRODUCT QUALITY%'                          THEN 'Product Quality'
                WHEN issue IS NULL OR LTRIM(RTRIM(issue)) = ''             THEN 'Unclassified (blank)'
                ELSE 'Other'
            END,
            CASE
                WHEN issue IN ('Release', 'Released')                       THEN 'EXCLUDE'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'                        THEN 'EXCLUDE'
                WHEN issue = 'Submittal' OR issue = 'qa samples'           THEN 'EXCLUDE'
                ELSE 'COUNTS'
            END
        ORDER BY issue_pallets DESC
    """,

    # ── 5. Worst items (only real quality failures) ──────────────────
    'worst_items': """
        SELECT TOP 15
            item, cont,
            COUNT(*) AS issue_count,
            SUM(issueQtyPal) AS total_bad_pallets,
            SUM(issueQtyEa) AS total_bad_eaches,
            SUM(prodQtyPal) AS total_prod_pallets
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -{months}, GETDATE())
          AND cont != 'ALL'
          AND issue NOT IN ('Release', 'Released')
          AND issue NOT LIKE '%CUSTOMER%REQUEST%'
          AND issue != 'Submittal'
          AND issue != 'qa samples'
          AND (issue IS NOT NULL AND LTRIM(RTRIM(issue)) != '')
        GROUP BY item, cont
        HAVING SUM(issueQtyPal) > 0
        ORDER BY total_bad_pallets DESC
    """,

    # ── 6. Recent detail with FTQ flag ───────────────────────────────
    'recent_detail': """
        SELECT TOP 40
            dateVal, cont, item, lot,
            issueQtyPal, issueQtyEa,
            issue,
            CASE
                WHEN issue IN ('Release', 'Released')      THEN 'EXCLUDE'
                WHEN issue LIKE '%CUSTOMER%REQUEST%'        THEN 'EXCLUDE'
                WHEN issue = 'Submittal'                    THEN 'EXCLUDE'
                WHEN issue = 'qa samples'                   THEN 'EXCLUDE'
                ELSE 'COUNTS'
            END AS ftq_flag
        FROM db_accessadmin.KPI_QA_OverallQuality_Rework
        WHERE dateVal >= DATEADD(month, -2, GETDATE())
          AND cont != 'ALL'
        ORDER BY dateVal DESC, issueQtyPal DESC
    """,

    # ── 7. Quality hold cost (last 7 days — daily data) ──────────────
    'hold_cost': """
        SELECT
            cont,
            COUNT(DISTINCT item) AS items_held,
            COUNT(DISTINCT lot) AS lots_held,
            SUM(pallets) AS total_pallet_days,
            MAX(QttlCost) AS max_single_hold_cost,
            AVG(overdueMult) AS avg_overdue_mult
        FROM db_accessadmin.KPI_QA_OverdueReleases
        WHERE dateVal >= DATEADD(day, -7, GETDATE())
        GROUP BY cont
        ORDER BY max_single_hold_cost DESC
    """,
}


def run_query(key, sql):
    rendered = sql.replace('{months}', str(MONTHS))
    print(f'\n{"=" * 70}')
    print(f'  {key}')
    print(f'{"=" * 70}')
    try:
        conn = pyodbc.connect(CONN_STR, timeout=30)
        cursor = conn.cursor()
        cursor.execute(rendered)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        print(f'  Columns: {columns}')
        print(f'  Rows: {len(rows)}')
        print()

        if rows:
            col_widths = []
            for i, col in enumerate(columns):
                max_val = max(len(str(row[i])[:45]) for row in rows[:25])
                col_widths.append(max(len(col), min(max_val, 45)))

            header = '  ' + ' | '.join(col.ljust(w) for col, w in zip(columns, col_widths))
            print(header)
            print('  ' + '-+-'.join('-' * w for w in col_widths))

            for row in rows[:25]:
                vals = []
                for i, val in enumerate(row):
                    s = str(val) if val is not None else '(NULL)'
                    vals.append(s[:45].ljust(col_widths[i]))
                print('  ' + ' | '.join(vals))

            if len(rows) > 25:
                print(f'\n  ... and {len(rows) - 25} more rows')

        return rows
    except Exception as e:
        print(f'  ERROR: {e}')
        return []


def main():
    print('=' * 70)
    print('  SHELDON FTQ v2 — Corrected Queries')
    print(f'  Driver: {DRIVER}')
    print(f'  Lookback: {MONTHS} months')
    print('=' * 70)

    print('\nTesting connection...')
    try:
        conn = pyodbc.connect(CONN_STR, timeout=15)
        conn.close()
        print('  Connected!\n')
    except Exception as e:
        print(f'  FAILED: {e}')
        sys.exit(1)

    for key, sql in QUERIES.items():
        run_query(key, sql)

    print('\n' + '=' * 70)
    print('  KEY: Compare raw_ftq_pct vs corrected_ftq_pct in monthly_corrected.')
    print('  The corrected number is what Brandon reports after manual scrubbing.')
    print('  If your corrected number aligns with what Quality presents,')
    print('  you have a fully automated FTQ pipeline.')
    print('=' * 70)


if __name__ == '__main__':
    main()
