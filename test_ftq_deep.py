"""
FTQ Deep Dive — Intelligence Gathering
Run on company laptop (AmeriQual network).

Investigates:
  1. dateVal distribution — how often is data populated?
  2. Blank issue rows — what are they?
  3. The "ALL" contract row — how does it relate to individual contracts?
  4. Rework detail tables — what additional columns exist?
  5. Overdue releases — quality holds with financial impact
  6. Destroy orders — structured reason/category data
  7. Table freshness — when was each table last updated?

Usage:
    python test_ftq_deep.py
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


QUERIES = {

    # ── 1. dateVal distribution — how granular is the data? ──────────
    'dateval_distribution': {
        'label': 'dateVal distribution (KPI_QA_OverallQuality_Contract)',
        'why': 'Understand if data is daily, weekly, or monthly. Explains why weekly_calculated only returned 2 rows.',
        'sql': """
            SELECT
                dateVal,
                COUNT(*) AS row_count,
                COUNT(DISTINCT cont) AS contracts,
                SUM(prodPallets) AS total_pallets,
                SUM(badPallets) AS bad_pallets
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE dateVal >= DATEADD(month, -6, GETDATE())
            GROUP BY dateVal
            ORDER BY dateVal DESC
        """
    },

    # ── 2. dateVal distribution for Rework table ─────────────────────
    'dateval_rework': {
        'label': 'dateVal distribution (KPI_QA_OverallQuality_Rework)',
        'why': 'See when rework data gets populated. Explains why recent_detail returned 0 rows.',
        'sql': """
            SELECT
                dateVal,
                COUNT(*) AS row_count,
                COUNT(DISTINCT cont) AS contracts,
                SUM(issueQtyPal) AS issue_pallets
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            WHERE dateVal >= DATEADD(month, -6, GETDATE())
            GROUP BY dateVal
            ORDER BY dateVal DESC
        """
    },

    # ── 3. Blank issue rows — what products/contracts? ───────────────
    'blank_issues': {
        'label': 'Rows with blank or NULL issue field',
        'why': 'The 31 blank entries need classification. See what products they map to.',
        'sql': """
            SELECT
                dateVal, cont, item, lot,
                issueQtyPal, issueQtyEa, prodQtyPal, prodQtyEa,
                issue
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            WHERE dateVal >= DATEADD(month, -6, GETDATE())
              AND (issue IS NULL OR LTRIM(RTRIM(issue)) = '')
            ORDER BY dateVal DESC
        """
    },

    # ── 4. "ALL" row vs sum of individual contracts ──────────────────
    'all_vs_individual': {
        'label': 'Compare ALL row vs sum of individual contracts',
        'why': 'Determine if ALL is a pre-aggregated row or a separate entity. Needed to avoid double-counting.',
        'sql': """
            SELECT
                CASE WHEN cont = 'ALL' THEN 'ALL_row' ELSE 'sum_of_contracts' END AS source,
                SUM(prodPallets) AS total_pallets,
                SUM(badPallets) AS bad_pallets,
                SUM(prodEaches) AS total_eaches,
                SUM(badEaches) AS bad_eaches,
                CASE WHEN SUM(prodPallets) > 0
                     THEN ROUND((1.0 - CAST(SUM(badPallets) AS FLOAT) / SUM(prodPallets)) * 100, 2)
                     ELSE 100.0 END AS ftq_pct
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            WHERE dateVal >= DATEADD(month, -3, GETDATE())
            GROUP BY CASE WHEN cont = 'ALL' THEN 'ALL_row' ELSE 'sum_of_contracts' END
        """
    },

    # ── 5. Table freshness — when was each table last updated? ───────
    'table_freshness': {
        'label': 'Most recent data in each FTQ-related table',
        'why': 'Know how current each data source is.',
        'sql': """
            SELECT 'KPI_QA_OverallQuality_Contract' AS tbl, MAX(dateVal) AS latest_date, COUNT(*) AS total_rows
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            UNION ALL
            SELECT 'KPI_QA_OverallQuality_Rework', MAX(dateVal), COUNT(*)
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            UNION ALL
            SELECT 'KPI_QA_CalcWeekly', MAX(weekVal), COUNT(*)
            FROM db_accessadmin.KPI_QA_CalcWeekly
            UNION ALL
            SELECT 'KPI_QA_OverdueReleases', MAX(dateVal), COUNT(*)
            FROM db_accessadmin.KPI_QA_OverdueReleases
            UNION ALL
            SELECT 'QualityDestroyOrders', MAX(Date), COUNT(*)
            FROM db_accessadmin.QualityDestroyOrders
            UNION ALL
            SELECT 'AQFQualityReworkLog', MAX(RWDate), COUNT(*)
            FROM db_accessadmin.AQFQualityReworkLog
            UNION ALL
            SELECT 'AQFQualityReworkDefect', MAX(DateEntered), COUNT(*)
            FROM db_accessadmin.AQFQualityReworkDefect
        """
    },

    # ── 6. Overdue releases — quality holds with $ impact ────────────
    'overdue_releases_summary': {
        'label': 'Quality holds — recent with financial impact',
        'why': 'Shows what is sitting on hold and costing money. Good dashboard data.',
        'sql': """
            SELECT TOP 30
                dateVal, cont, item, lot,
                pallets, units, overdueMult,
                QttlCost, dailyCount
            FROM db_accessadmin.KPI_QA_OverdueReleases
            WHERE dateVal >= DATEADD(month, -2, GETDATE())
            ORDER BY QttlCost DESC
        """
    },

    # ── 7. Overdue releases — aggregate by contract ──────────────────
    'overdue_by_contract': {
        'label': 'Quality holds aggregated by contract',
        'why': 'Which contracts have the most product sitting on hold?',
        'sql': """
            SELECT
                cont,
                COUNT(*) AS hold_count,
                SUM(pallets) AS total_pallets_held,
                SUM(units) AS total_units_held,
                SUM(QttlCost) AS total_hold_cost,
                AVG(overdueMult) AS avg_days_overdue
            FROM db_accessadmin.KPI_QA_OverdueReleases
            WHERE dateVal >= DATEADD(month, -3, GETDATE())
            GROUP BY cont
            ORDER BY total_hold_cost DESC
        """
    },

    # ── 8. Destroy orders — structured categories ────────────────────
    'destroy_orders': {
        'label': 'Destroy orders with structured Reason/Category/SubCategory',
        'why': 'These have proper categorization — unlike the free-text issue field.',
        'sql': """
            SELECT TOP 30
                Date, Contract, SKU, Lot,
                Type, Reason, Category, SubCategory,
                Description
            FROM db_accessadmin.QualityDestroyOrders
            WHERE Date >= DATEADD(month, -6, GETDATE())
            ORDER BY Date DESC
        """
    },

    # ── 9. Destroy order categories — what buckets exist? ────────────
    'destroy_categories': {
        'label': 'Distinct destroy Reason/Category/SubCategory values',
        'why': 'The structured classification system that already exists.',
        'sql': """
            SELECT
                Reason, Category, SubCategory,
                COUNT(*) AS cnt
            FROM db_accessadmin.QualityDestroyOrders
            WHERE Date >= DATEADD(year, -1, GETDATE())
            GROUP BY Reason, Category, SubCategory
            ORDER BY cnt DESC
        """
    },

    # ── 10. Rework log detail — AQFQualityReworkLog ──────────────────
    'rework_log_detail': {
        'label': 'Rework orders from AQFQualityReworkLog (last 3 months)',
        'why': 'The actual rework order records with structured fields.',
        'sql': """
            SELECT TOP 30
                RWDate, ReworkNum, Lot, ItemNum,
                RWLocation, Priority,
                Pallets, Cases, Eaches,
                PayRWCode
            FROM db_accessadmin.AQFQualityReworkLog
            WHERE RWDate >= DATEADD(month, -3, GETDATE())
            ORDER BY RWDate DESC
        """
    },

    # ── 11. Rework defect detail — AQFQualityReworkDefect ────────────
    'rework_defect_detail': {
        'label': 'Individual defect records (pallet-level) from AQFQualityReworkDefect',
        'why': 'This is the pallet-level defect data — the most granular view.',
        'sql': """
            SELECT TOP 30
                d.PalletNum, d.SKU, d.Lot,
                d.Defect, d.NumDefect,
                d.Machine, d.HeadSide,
                d.DefPouchDate, d.PouchTime,
                d.DateEntered, d.EnteredBy
            FROM db_accessadmin.AQFQualityReworkDefect d
            WHERE d.DateEntered >= DATEADD(month, -3, GETDATE())
            ORDER BY d.DateEntered DESC
        """
    },

    # ── 12. Defect types — what defects are being logged? ────────────
    'defect_types': {
        'label': 'Distinct defect types from AQFQualityReworkDefect',
        'why': 'The structured defect classification — better than free text.',
        'sql': """
            SELECT
                Defect,
                COUNT(*) AS occurrences,
                SUM(CAST(NULLIF(NumDefect, '') AS INT)) AS total_defects,
                COUNT(DISTINCT SKU) AS products_affected
            FROM db_accessadmin.AQFQualityReworkDefect
            WHERE DateEntered >= DATEADD(year, -1, GETDATE())
              AND Defect IS NOT NULL AND Defect != ''
            GROUP BY Defect
            ORDER BY occurrences DESC
        """
    },

    # ── 13. Submittal rows — what are they? ──────────────────────────
    'submittal_rows': {
        'label': 'Rows where issue contains "Submittal" or "FSIS"',
        'why': 'Understand if Submittals are USDA testing (exclude from FTQ?) or actual failures.',
        'sql': """
            SELECT
                dateVal, cont, item, lot,
                issueQtyPal, issueQtyEa, prodQtyPal, prodQtyEa,
                issue
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            WHERE dateVal >= DATEADD(month, -6, GETDATE())
              AND (issue LIKE '%Submittal%' OR issue LIKE '%FSIS%')
            ORDER BY dateVal DESC
        """
    },

    # ── 14. Full column list for KPI_QA_OverallQuality_Contract ──────
    'contract_table_sample': {
        'label': 'Full sample row from KPI_QA_OverallQuality_Contract',
        'why': 'See ALL columns — there may be fields we are not using yet.',
        'sql': """
            SELECT TOP 5 *
            FROM db_accessadmin.KPI_QA_OverallQuality_Contract
            ORDER BY dateVal DESC
        """
    },

    # ── 15. Full column list for KPI_QA_OverallQuality_Rework ────────
    'rework_table_sample': {
        'label': 'Full sample row from KPI_QA_OverallQuality_Rework',
        'why': 'See ALL columns — there may be fields we are not using yet.',
        'sql': """
            SELECT TOP 5 *
            FROM db_accessadmin.KPI_QA_OverallQuality_Rework
            ORDER BY dateVal DESC
        """
    },

    # ── 16. CalcWeekly — all data (not just FTQ) ────────────────────
    'calc_weekly_all': {
        'label': 'ALL data in KPI_QA_CalcWeekly (not filtered to FTQ)',
        'why': 'See what other KPIs were being pre-calculated, and when it stopped.',
        'sql': """
            SELECT TOP 30
                weekVal, groupVal, valueStream, descr, numVal
            FROM db_accessadmin.KPI_QA_CalcWeekly
            ORDER BY weekVal DESC
        """
    },
}


def run_query(key, info):
    label = info['label']
    why = info['why']
    sql = info['sql']

    print(f'\n{"=" * 70}')
    print(f'  {key}')
    print(f'  {label}')
    print(f'  WHY: {why}')
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

        if rows:
            col_widths = []
            for i, col in enumerate(columns):
                max_val = max(len(str(row[i])[:50]) for row in rows[:25])
                col_widths.append(max(len(col), min(max_val, 50)))

            header = '  ' + ' | '.join(col.ljust(w) for col, w in zip(columns, col_widths))
            print(header)
            print('  ' + '-+-'.join('-' * w for w in col_widths))

            for row in rows[:25]:
                vals = []
                for i, val in enumerate(row):
                    s = str(val) if val is not None else '(NULL)'
                    vals.append(s[:50].ljust(col_widths[i]))
                print('  ' + ' | '.join(vals))

            if len(rows) > 25:
                print(f'\n  ... and {len(rows) - 25} more rows')

        return rows

    except Exception as e:
        print(f'  ERROR: {e}')
        return []


def main():
    print('=' * 70)
    print('  SHELDON FTQ Deep Dive — Intelligence Gathering')
    print(f'  Driver: {DRIVER}')
    print(f'  Server: AQFDB6 / Database: CI')
    print('=' * 70)

    print('\nTesting connection...')
    try:
        conn = pyodbc.connect(CONN_STR, timeout=15)
        conn.close()
        print('  Connected!\n')
    except Exception as e:
        print(f'  FAILED: {e}')
        print('  Make sure you are on the AmeriQual network.')
        sys.exit(1)

    for key, info in QUERIES.items():
        run_query(key, info)

    print('\n' + '=' * 70)
    print('  DONE — Copy this output and bring it back for analysis.')
    print('=' * 70)


if __name__ == '__main__':
    main()
