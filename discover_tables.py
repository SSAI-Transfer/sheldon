"""
Database Table Discovery Script for SHELDON KPI Integration
Ayden granted CI + MANUFACTURING access on AQFDB6 (Mar 10, 2026)
IPs: AQFAM1 = 10.200.20.12, AQFDB7 = 10.200.20.110

Run on AmeriQual network: python discover_tables.py
"""

import pyodbc
import json
import sys
from datetime import datetime


CONNECTIONS = [
    # CI database on AQFDB6 — KPI tables live here
    {
        'label': 'CI on AQFDB6',
        'server': 'AQFDB6',
        'database': 'CI',
        'uid': 'SocialScaleReadOnly',
        'pwd': 'socialscale.25',
    },
    # MANUFACTURING database on AQFDB6 — EOP shift notes
    {
        'label': 'MANUFACTURING on AQFDB6',
        'server': 'AQFDB6',
        'database': 'MANUFACTURING',
        'uid': 'SocialScaleReadOnly',
        'pwd': 'socialscale.25',
    },
    # AMMS on AQFAM1\AMMS — named instance (per Ayden, Mar 10)
    {
        'label': 'AMMS on AQFAM1\\AMMS',
        'server': 'AQFAM1\\AMMS',
        'database': 'AMMS',
        'uid': 'AMMSro',
        'pwd': 'V1s3-Gr1p',
    },
    {
        'label': 'AMMS on AQFAM1\\AMMS (IP)',
        'server': '10.200.20.12\\AMMS',
        'database': 'AMMS',
        'uid': 'AMMSro',
        'pwd': 'V1s3-Gr1p',
    },
    # AQFDB7\KRONWFC — named instance for manning/headcount (per Ayden, Mar 10)
    {
        'label': 'AQFDB7\\KRONWFC',
        'server': 'AQFDB7\\KRONWFC',
        'database': '',
        'uid': 'SocialScaleReadOnly',
        'pwd': 'socialscale.25',
    },
    {
        'label': 'AQFDB7\\KRONWFC (IP)',
        'server': '10.200.20.110\\KRONWFC',
        'database': '',
        'uid': 'SocialScaleReadOnly',
        'pwd': 'socialscale.25',
    },
]

# KPI table names we're looking for
TARGET_KEYWORDS = [
    'kpi', 'eop', 'shift', 'notes', 'attainment', 'yield', 'defect',
    'quality', 'foreign', 'matter', 'overdue', 'release', 'rework',
    'reclean', 'clean', 'cost', 'glcost', 'repair', 'transaction',
    'cycle', 'count', 'capacity', 'inventory', 'sched', 'target',
    'actual', 'labor', 'manning', 'headcount', 'dashboard', 'dash',
]


def build_conn_string(config):
    parts = [
        f"DRIVER={{ODBC Driver 17 for SQL Server}}",
        f"SERVER={config['server']}",
        f"UID={config['uid']}",
        f"PWD={config['pwd']}",
        f"Connection Timeout=15",
        f"TrustServerCertificate=yes",
    ]
    if config.get('database'):
        parts.insert(2, f"DATABASE={config['database']}")
    return ';'.join(parts) + ';'


def try_connection(config):
    label = config['label']
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Server: {config['server']}  DB: {config.get('database','(default)')}")
    print(f"{'='*70}")

    result = {'label': label, 'status': 'unknown', 'databases': {}}

    try:
        conn = pyodbc.connect(build_conn_string(config), timeout=15)
        cursor = conn.cursor()
        result['status'] = 'connected'

        cursor.execute("SELECT DB_NAME() AS current_db")
        current_db = cursor.fetchone()[0]
        print(f"  Connected! Current database: {current_db}")

        # List databases
        try:
            cursor.execute("SELECT name FROM sys.databases ORDER BY name")
            dbs = [row[0] for row in cursor.fetchall()]
            print(f"  All databases: {', '.join(dbs)}")
            result['all_databases'] = dbs
        except:
            result['all_databases'] = [current_db]

        # Discover current database
        db_result = {'tables': [], 'kpi_matches': []}

        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        all_objects = cursor.fetchall()
        print(f"\n  {len(all_objects)} objects in {current_db}:")

        for schema, tname, ttype in all_objects:
            db_result['tables'].append({'schema': schema, 'name': tname, 'type': ttype.strip()})

            # Check relevance
            search_text = tname.lower()
            is_relevant = any(kw in search_text for kw in TARGET_KEYWORDS)

            if is_relevant:
                print(f"\n  *** [{ttype.strip()}] {schema}.{tname}")

                # Get columns
                columns = []
                try:
                    cursor.execute(f"""
                        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                        ORDER BY ORDINAL_POSITION
                    """, schema, tname)
                    for col_name, dtype, max_len in cursor.fetchall():
                        len_str = f"({max_len})" if max_len and max_len > 0 else ""
                        columns.append({'name': col_name, 'type': f"{dtype}{len_str}"})
                        print(f"      {col_name:40s} {dtype}{len_str}")
                except Exception as e:
                    print(f"      Error: {e}")

                # Row count
                row_count = None
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{tname}]")
                    row_count = cursor.fetchone()[0]
                    print(f"    Rows: {row_count:,}")
                except Exception as e:
                    print(f"    Cannot count: {e}")

                # Sample data
                sample = []
                try:
                    cursor.execute(f"SELECT TOP 3 * FROM [{schema}].[{tname}]")
                    col_names = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        sample.append({col_names[i]: str(row[i])[:80] for i in range(len(col_names))})
                    print(f"    Sample:")
                    for s in sample:
                        print(f"      {s}")
                except Exception as e:
                    print(f"    Cannot sample: {e}")

                db_result['kpi_matches'].append({
                    'schema': schema, 'name': tname, 'type': ttype.strip(),
                    'columns': columns, 'row_count': row_count, 'sample': sample
                })
            else:
                print(f"    [{ttype.strip():10s}] {schema}.{tname}")

        result['databases'][current_db] = db_result
        conn.close()

    except pyodbc.Error as e:
        result['status'] = 'failed'
        result['error'] = str(e)[:500]
        print(f"  CONNECTION FAILED: {str(e)[:300]}")

    return result


def main():
    print("=" * 70)
    print("  SHELDON KPI Table Discovery v3")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    drivers = pyodbc.drivers()
    sql_drivers = [d for d in drivers if 'SQL Server' in d]
    print(f"\n  ODBC Drivers: {sql_drivers}")

    all_results = {}
    for config in CONNECTIONS:
        all_results[config['label']] = try_connection(config)

    # Save
    output_path = 'kpi_table_discovery.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    # Summary
    print(f"\n\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    for label, res in all_results.items():
        status = res.get('status', '?')
        print(f"\n  {label}: {status}")
        for db_name, db_info in res.get('databases', {}).items():
            matches = len(db_info.get('kpi_matches', []))
            total = len(db_info.get('tables', []))
            print(f"    {db_name}: {total} objects, {matches} KPI-relevant")
            for m in db_info.get('kpi_matches', []):
                print(f"      -> {m['schema']}.{m['name']} ({m.get('row_count', '?')} rows, {len(m.get('columns',[]))} cols)")

    print(f"\n  Results saved to: {output_path}")


if __name__ == '__main__':
    main()
