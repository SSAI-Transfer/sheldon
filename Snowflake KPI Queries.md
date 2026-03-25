# SHELDON Snowflake KPI Queries

## Connection Details
- **Database:** `ZGRZDCXCHH_DB`
- **Schema:** `"ameriqual-org"`
- **Source:** Redzone production data
- **Tested:** December 17, 2024

---

## Key Views

| View | Purpose | Tested |
|------|---------|--------|
| `v_hourlyperformancesummary` | OEE, production, labor metrics by hour | ✅ |
| `v_losses` | Downtime events with reasons | ✅ |

---

## OEE Queries

### 1. Current OEE by Line (Last 24 Hours)

```sql
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
ORDER BY avg_oee DESC;
```

### 2. Overall Plant OEE Summary (Last 24 Hours)

```sql
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
  AND "oee" > 0;
```

### 3. OEE by Area (Last 24 Hours)

```sql
SELECT
    "areaName" AS area,
    ROUND(AVG("oee"), 1) AS avg_oee,
    ROUND(AVG("performance"), 1) AS avg_performance,
    ROUND(AVG("quality"), 1) AS avg_quality,
    ROUND(AVG("availability"), 1) AS avg_availability,
    SUM("outCount") AS total_output,
    COUNT(DISTINCT "locationName") AS line_count
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0
GROUP BY "areaName"
ORDER BY avg_oee DESC;
```

### 4. Lines Below OEE Threshold (Red Flags)

```sql
SELECT
    "locationName" AS line_name,
    "areaName" AS area,
    ROUND(AVG("oee"), 1) AS avg_oee,
    ROUND(AVG("availability"), 1) AS avg_availability,
    ROUND(SUM("downSeconds")/3600, 1) AS downtime_hours
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0
GROUP BY "locationName", "areaName"
HAVING AVG("oee") < 70
ORDER BY avg_oee ASC;
```

### 5. Hourly OEE Trend (Last 12 Hours)

```sql
SELECT
    "dateTimeNearestHour" AS hour,
    ROUND(AVG("oee"), 1) AS avg_oee,
    SUM("outCount") AS total_output,
    COUNT(DISTINCT "locationName") AS active_lines
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(hour, -12, CURRENT_TIMESTAMP())
  AND "oee" > 0
GROUP BY "dateTimeNearestHour"
ORDER BY "dateTimeNearestHour" DESC;
```

---

## Production Queries

### 6. Total Production Output (Last 24 Hours)

```sql
SELECT
    "siteName" AS site,
    SUM("outCount") AS total_output,
    SUM("inCount") AS total_input,
    ROUND(SUM("manHours"), 1) AS total_manhours,
    ROUND(SUM("outCount") / NULLIF(SUM("manHours"), 0), 1) AS units_per_manhour
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY "siteName";
```

### 7. Production by Product Type (Last 24 Hours)

```sql
SELECT
    "productTypeName" AS product,
    "locationName" AS line,
    SUM("outCount") AS total_output,
    ROUND(AVG("oee"), 1) AS avg_oee
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "productTypeName" IS NOT NULL
GROUP BY "productTypeName", "locationName"
ORDER BY total_output DESC
LIMIT 20;
```

### 8. Lines Currently Active (Most Recent Hour)

```sql
SELECT
    "locationName" AS line_name,
    "areaName" AS area,
    "productTypeName" AS current_product,
    "oee" AS current_oee,
    "outCount" AS hourly_output
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(hour, -2, CURRENT_TIMESTAMP())
  AND "outCount" > 0
ORDER BY "dateTimeNearestHour" DESC, "locationName";
```

---

## Downtime Queries

### 9. Top Downtime Reasons (Last 24 Hours)

```sql
SELECT
    "problemTypeName" AS reason,
    "problemGroupName" AS category,
    "problemPlanned" AS planned,
    COUNT(*) AS occurrences,
    ROUND(SUM("minutesLost"), 1) AS total_minutes_lost,
    ROUND(SUM("hoursLost"), 2) AS total_hours_lost
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
WHERE "startTime" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY "problemTypeName", "problemGroupName", "problemPlanned"
ORDER BY total_minutes_lost DESC
LIMIT 10;
```

### 10. Unplanned Downtime Only (Red Flags)

```sql
SELECT
    "problemTypeName" AS reason,
    "problemGroupName" AS category,
    "locationName" AS line,
    COUNT(*) AS occurrences,
    ROUND(SUM("hoursLost"), 2) AS total_hours_lost
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
WHERE "startTime" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "problemPlanned" = FALSE
GROUP BY "problemTypeName", "problemGroupName", "locationName"
ORDER BY total_hours_lost DESC
LIMIT 15;
```

### 11. Downtime by Line (Last 24 Hours)

```sql
SELECT
    "locationName" AS line,
    "areaName" AS area,
    COUNT(*) AS downtime_events,
    ROUND(SUM("hoursLost"), 2) AS total_hours_lost,
    SUM(CASE WHEN "problemPlanned" = FALSE THEN 1 ELSE 0 END) AS unplanned_events
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
WHERE "startTime" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY "locationName", "areaName"
ORDER BY total_hours_lost DESC;
```

### 12. Downtime by Category (Last 24 Hours)

```sql
SELECT
    "problemGroupName" AS category,
    "problemPlanned" AS planned,
    COUNT(*) AS occurrences,
    ROUND(SUM("hoursLost"), 2) AS total_hours_lost,
    ROUND(AVG("minutesLost"), 1) AS avg_minutes_per_event
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
WHERE "startTime" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY "problemGroupName", "problemPlanned"
ORDER BY total_hours_lost DESC;
```

### 13. Recent Downtime Events (Last 4 Hours)

```sql
SELECT
    "startTime" AS start_time,
    "endTime" AS end_time,
    "locationName" AS line,
    "problemTypeName" AS reason,
    "problemGroupName" AS category,
    ROUND("minutesLost", 1) AS minutes_lost,
    "problemPlanned" AS planned
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_losses"
WHERE "startTime" >= DATEADD(hour, -4, CURRENT_TIMESTAMP())
ORDER BY "startTime" DESC
LIMIT 20;
```

---

## Labor Queries

### 14. Labor Productivity by Line (Last 24 Hours)

```sql
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
ORDER BY units_per_manhour DESC;
```

### 15. Total Labor Hours by Area (Last 24 Hours)

```sql
SELECT
    "areaName" AS area,
    ROUND(SUM("manHours"), 1) AS total_manhours,
    COUNT(DISTINCT "locationName") AS line_count,
    ROUND(SUM("manHours") / COUNT(DISTINCT "locationName"), 1) AS avg_manhours_per_line
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
GROUP BY "areaName"
ORDER BY total_manhours DESC;
```

---

## Composite Queries for SHELDON Webhooks

### kpiLive - Dashboard Summary

```sql
SELECT
    -- Overall metrics
    ROUND(AVG("oee"), 1) AS plant_oee,
    ROUND(AVG("performance"), 1) AS plant_performance,
    ROUND(AVG("quality"), 1) AS plant_quality,
    ROUND(AVG("availability"), 1) AS plant_availability,

    -- Production
    SUM("outCount") AS total_output_24h,
    ROUND(SUM("manHours"), 1) AS total_manhours_24h,

    -- Downtime
    ROUND(SUM("downSeconds")/3600, 1) AS total_downtime_hours,

    -- Line counts
    COUNT(DISTINCT "locationName") AS lines_reporting,
    COUNT(DISTINCT CASE WHEN "outCount" > 0 THEN "locationName" END) AS lines_producing

FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0;
```

### redFlags - Lines Needing Attention

```sql
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
ORDER BY avg_oee ASC;
```

---

## Notes

- All queries use `DATEADD(day, -1, CURRENT_TIMESTAMP())` for last 24 hours - adjust as needed
- Column names are case-sensitive and must be quoted with double quotes
- Schema name contains a hyphen and must be quoted: `"ameriqual-org"`
- OEE values > 100 indicate exceeding target (not an error)
- `problemPlanned = FALSE` filters for unplanned downtime only

---

*Created: December 17, 2024*
*Tested with SnowSQL v1.4.5*
