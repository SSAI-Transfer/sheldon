# Snowflake Data Exploration - AmeriQual

## Overview
**Date Explored:** December 22, 2024
**Connection:** snowsql -c ameriqual
**Purpose:** Document all available data in Snowflake for SHELDON and future projects

---

## Connection Details

### SnowSQL Config
- **Connection Name:** ameriqual
- **Account:** redzone-prod_direct_access_reader
- **Username:** ZGRZDCXCHH_USER
- **Config Location:** ~/.snowsql/config

### Database Info
| Property | Value |
|----------|-------|
| Database | ZGRZDCXCHH_DB |
| Schema | ameriqual-org |
| Origin | REDZONE.PROD.PROD_ZGRZDCXCHH_SHARE |
| Type | IMPORTED DATABASE (Data Share) |

---

## What This Data IS

This is **RedZone MES (Manufacturing Execution System)** data - NOT raw Ignition historian data.

**Contains:**
- Production runs, shifts, cycles
- OEE metrics and performance summaries
- Downtime/losses with reasons
- Operator actions and comments
- Quality checks and datasheets
- Training and skills tracking
- Meeting records

**Does NOT Contain:**
- Raw Ignition historian tag data (time-series sensor values)
- Real-time PLC tag values
- Temperatures, pressures, speeds logged over time

---

## All Available Views (91 Total)

### Production & Operations
| View | Description |
|------|-------------|
| v_run | Production runs |
| v_run_last7days | Recent runs (last 7 days) |
| v_runassetcount | Asset counts per run |
| v_runcountadjustments | Count adjustments during runs |
| v_runparameterset | Run parameters |
| v_runreconciliation | Run reconciliation data |
| v_runsignature | Run sign-offs |
| v_shift | Shift records |
| v_shiftassetcount | Asset counts per shift |
| v_shiftcountadjustments | Count adjustments per shift |
| v_shiftrunsegment | Run segments within shifts |
| v_shiftrunsegment_last30days | Recent run segments |
| v_shifttype | Shift type definitions |
| v_cycle | Production cycles |
| v_cyclerunningstatusrecord | Cycle status records |
| v_cyclestatusperiod | Cycle status periods |
| v_cycletarget | Cycle targets |
| v_changeover | Changeover events |

### Performance & Metrics
| View | Description |
|------|-------------|
| v_hourlyperformancesummary | **KEY VIEW** - OEE, production, labor by hour |
| v_inoutcounts | Input/output counts |
| v_liveruncounts | Real-time run counts |
| v_liveshiftcounts | Real-time shift counts |
| v_countadjustments | Count adjustment records |
| v_powerhour | Power hour tracking |

### Downtime & Losses
| View | Description |
|------|-------------|
| v_losses | **KEY VIEW** - Downtime events with reasons |
| v_losses_comments | Operator comments on downtime |
| v_lossdefinition | Loss type definitions |
| v_assetlosses | Asset-specific losses |
| v_asset_losses_comments | Comments on asset losses |
| v_cause | Root causes |
| v_solution | Solutions implemented |
| v_fishbone | Fishbone analysis data |
| v_problemgroup | Problem categories |

### Assets & Equipment
| View | Description |
|------|-------------|
| v_asset | Asset/equipment master |
| v_assettype | Asset type definitions |
| v_assetcount | Asset counts |

### Location & Organization
| View | Description |
|------|-------------|
| v_enterprise | Enterprise info |
| v_area | Production areas |
| v_locationdefinition | Location definitions |
| v_divisiontreebranch | Organizational hierarchy |

### Products
| View | Description |
|------|-------------|
| v_product | Product master |
| v_productgroup | Product groupings |
| v_productgroupmap | Product-to-group mappings |
| v_productstate | Product states |
| v_productunitconversion | Unit conversions |
| v_manufacturingtype | Manufacturing types |
| v_unitofmeasure | Units of measure |
| v_standard | Standards/specifications |

### Quality & Data Sheets
| View | Description |
|------|-------------|
| v_completeddatasheet | Completed quality checks |
| v_completeddatasheetcomments | Comments on data sheets |
| v_completeddatasheetsection | Data sheet sections |
| v_completeddataitem | Individual data items |
| v_datasheettemplate | Data sheet templates |
| v_dataitemtemplate | Data item templates |
| v_spcsample | SPC sample data |
| v_stepsummarystate | Step summary states |

### People & Labor
| View | Description |
|------|-------------|
| v_user | User/operator master |
| v_userbuddy | User buddy assignments |
| v_leadoperator | Lead operator assignments |
| v_actionuserhours | User labor hours |

### Skills & Training
| View | Description |
|------|-------------|
| v_skill | Skill definitions |
| v_userskill | User skill assignments |
| v_userskillexpanded | Expanded skill view |
| v_learningpack | Learning pack definitions |
| v_learningpackitem | Learning pack items |
| v_userlearningpack | User learning assignments |
| v_userlearningpackitem | User learning item progress |
| v_useronboarding | Onboarding status |
| v_userplays | User activity/plays |
| v_quizattempts | Quiz attempt records |
| v_quizanswers | Quiz answers |

### Actions & Workflows
| View | Description |
|------|-------------|
| v_action | Actions/tasks |
| v_actionmove | Action movements |
| v_actionpart | Action parts |
| v_actionworkflow | Workflow records |
| v_trigger | Automated triggers |

### Communication
| View | Description |
|------|-------------|
| v_chat | Chat threads |
| v_comment | Comments (8M+ records) |
| v_blog | Blog/huddle posts |
| v_reaction | Reactions |

### Meetings
| View | Description |
|------|-------------|
| v_meeting | Meeting records |
| v_meetingpresentuser | Meeting attendance |
| v_meetingtemplate | Meeting templates |
| v_meetingtemplateagendaitem | Agenda items |
| v_meetingtemplatelocation | Meeting locations |
| v_meetingtemplateparticipant | Expected participants |
| v_meetingtemplateprompt | Meeting prompts |
| v_meetingtemplatestakeholder | Stakeholders |

### Parts & History
| View | Description |
|------|-------------|
| v_partdata | Part data |
| v_parthistory | Part history |

### Other
| View | Description |
|------|-------------|
| v_filemetadata | File metadata |

---

## Key Views for SHELDON (Currently Used)

| View | Used For | Status |
|------|----------|--------|
| v_hourlyperformancesummary | OEE, Quality, Availability, Performance, Output | LIVE |
| v_losses | Downtime events and reasons | LIVE |

---

## Sample Data Structures

### v_hourlyperformancesummary (Sample Columns)
- timeZoneId, dateYear, quarter, monthNumber, week, dayName
- hourOfDay, dateTimeNearestHour
- locationUUID, locationName, areaUUID, areaName
- siteUUID, siteName
- runUUID, runName, productTypeName, productTypeSKU
- shiftUUID, shiftName
- theoreticalQuantity, inCount, outCount
- oee, target, performance, quality, availability
- upSeconds, downSeconds, plannedDownSeconds
- manHours, unitsPerManHour

### v_losses (Sample Columns)
- startTime, endTime
- locationName, areaName, siteName
- problemTypeName, problemGroupName
- problemPlanned (TRUE/FALSE)
- minutesLost, hoursLost

### v_cycle (Sample Columns)
- cycleUUID, startTime, endTime
- locationName, cycleAssetName
- actualDurationWithPlannedDowntime
- cycleActiveTargetSecondsForProduct
- cycleResult (GOOD, etc.)
- productTypeName, productTypeSKU
- shiftName, runName

---

## Sites in Data

| Site | Description |
|------|-------------|
| Foods | Main food production |
| Packaging | Packaging operations |
| ThermoPac | ThermoPac facility |

---

## Data NOT in This Share

### Ignition Historian Data
The raw time-series tag data from Ignition (temperatures, pressures, speeds, PLC values) is **NOT** in this Snowflake share.

To get historian data, would need to:
1. Check where Ignition Gateway stores historian data (MySQL, SQL Server, PostgreSQL, or internal)
2. Ask AmeriQual IT if historian data is replicated anywhere
3. May need direct access to Ignition system

### Sage X3 / Financial Data
Financial and inventory data is in Sage X3, accessed via SQL Server:
- Server: AQFDB1\X3
- Database: x3
- Schema: AMQ

Currently **BLOCKED** - needs company laptop access.

---

## Useful Queries

### Plant OEE Summary (Last 24 Hours)
```sql
SELECT
    ROUND(AVG("oee"), 1) AS plant_oee,
    ROUND(AVG("performance"), 1) AS plant_performance,
    ROUND(AVG("quality"), 1) AS plant_quality,
    ROUND(AVG("availability"), 1) AS plant_availability,
    SUM("outCount") AS total_output,
    ROUND(SUM("downSeconds")/3600, 1) AS total_downtime_hours,
    COUNT(DISTINCT "locationName") AS lines_reporting
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0;
```

### OEE by Line (Last 24 Hours)
```sql
SELECT
    "locationName" AS line_name,
    "areaName" AS area,
    ROUND(AVG("oee"), 1) AS avg_oee,
    ROUND(AVG("performance"), 1) AS avg_performance,
    ROUND(AVG("quality"), 1) AS avg_quality,
    ROUND(AVG("availability"), 1) AS avg_availability,
    SUM("outCount") AS total_output,
    ROUND(SUM("downSeconds")/3600, 1) AS downtime_hours
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0
GROUP BY "locationName", "areaName"
ORDER BY avg_oee DESC;
```

### Lines Below 70% OEE (Red Flags)
```sql
SELECT
    "locationName" AS line_name,
    "areaName" AS area,
    ROUND(AVG("oee"), 1) AS avg_oee,
    ROUND(SUM("downSeconds")/3600, 1) AS downtime_hours
FROM ZGRZDCXCHH_DB."ameriqual-org"."v_hourlyperformancesummary"
WHERE "dateTimeNearestHour" >= DATEADD(day, -1, CURRENT_TIMESTAMP())
  AND "oee" > 0
GROUP BY "locationName", "areaName"
HAVING AVG("oee") < 70
ORDER BY avg_oee ASC;
```

### Top Downtime Reasons (Last 24 Hours)
```sql
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
LIMIT 10;
```

### List All Views
```sql
SHOW VIEWS IN SCHEMA "ZGRZDCXCHH_DB"."ameriqual-org";
```

### Describe a View
```sql
SELECT * FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_viewname" LIMIT 1;
```

---

## Query Notes

- Column names are **case-sensitive** and must use double quotes: `"columnName"`
- Schema name contains a hyphen and must be quoted: `"ameriqual-org"`
- OEE values > 100 indicate exceeding target (not an error)
- Use `"problemPlanned" = FALSE` to filter for unplanned downtime only
- Timestamps are in UTC unless timeZoneId column specifies otherwise

---

## Related Documentation

- `Snowflake KPI Queries.md` - Detailed queries for SHELDON KPIs
- `Redzone Shop Floor Analysis.md` - Analysis of operator comments
- `SHELDON Executive Interface.md` - Main project tracking
- `KPI Tracker.md` - KPI implementation status

---

*Created: December 22, 2024*
*Related Project: SHELDON Executive Interface*
