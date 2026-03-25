# SHELDON Executive Interface

## Overview
- **Client:** AmeriQual Foods
- **Project:** Executive intelligence dashboard for CEO and leadership
- **End User:** Dennis Straub (President & CEO)
- **Interface Name:** SHELDON

## Status Summary - December 17, 2024

| Component | Status |
|-----------|--------|
| Interface (HTML/CSS/JS) | Complete |
| Welcome experience | Complete |
| TTS (browser-based) | Complete |
| Chat interface | Complete - connected to webhook |
| KPI cards with drill-down | LIVE - Snowflake data |
| Red flags panel UI | LIVE - Snowflake data |
| Executive Briefing panel | LIVE - Snowflake data |
| Spoken briefing | LIVE - Snowflake data |
| Operations panel | LIVE - Snowflake data |
| Financial/Inventory panels | Hardcoded (needs Sage X3) |

**Current Phase:** Core KPIs live from Snowflake. Financial data blocked until Sage X3 access.

---

## Make.com Webhooks

| Webhook | URL | Purpose | Status |
|---------|-----|---------|--------|
| kpiLive | https://hook.us2.make.com/vflzcgy2hajegl9gxjdhw4nm5bv1tem2 | Real-time KPI updates | Working |
| redFlags | https://hook.us2.make.com/laiiare52qa7d44jvscesy81m696hdc4 | Lines below 70% OEE | Working |
| briefing | https://hook.us2.make.com/iu72of55eni18o0l53he3esh685eq2kt | Morning executive briefing | Working |
| chat | https://hook.us2.make.com/3eftqahiejqpw3yr2va4993aqkdoipgs | Chat responses | Working |
| tts | https://hook.us2.make.com/lypllp614zvrjplgpm16lhzbk7heykgm | Text-to-speech | Working |

---

## Data Sources

| System | Type | Connection | Status |
|--------|------|------------|--------|
| Snowflake | Data Warehouse | HTTP via Make.com | Connected |
| Redzone | MES | Via Snowflake views | Working |
| Sage X3 | ERP | SQL via Make.com | Blocked - need laptop |
| SQL Server | Database | AQFDB1\X3 / x3 / Schema: AMQ | Blocked |

### Snowflake Details
- **Database:** ZGRZDCXCHH_DB
- **Schema:** "ameriqual-org"
- **Key Views:**
  - v_hourlyperformancesummary - OEE, production, labor metrics
  - v_losses - Downtime events with reasons

---

## Live KPIs (from Snowflake)

| KPI | Source Field | Location in UI |
|-----|--------------|----------------|
| Plant OEE | plant_oee | KPI Card, Briefing, Operations |
| Quality | plant_quality | KPI Card, Briefing |
| Availability | plant_availability | KPI Card |
| Performance | plant_performance | KPI Card (Labor) |
| Total Output | total_output | Briefing |
| Downtime Hours | total_downtime_hours | Operations |
| Lines Reporting | lines_reporting | Briefing, Operations |
| Problem Lines | problem_lines | Red Flags, Briefing |
| Worst Line/OEE | worst_line, worst_oee | Briefing |

---

## Still Hardcoded (Future Work)

### Needs Sage X3 Access
- Financial Overview (Gross Margin, EBITDA, Cash Position, AR Days)
- Inventory Status (Total Value, Finished Goods, Days on Hand)
- Revenue KPI card

### Needs Other Data Sources
- People panel (HR system)
- Quality panel (Quality system)
- Marketing & Sales (CRM)
- Schedule Attainment (may be in Redzone)

---

## Files Location

All files in: C:\Users\Claude\AMERIQUAL PROJECT TRACKER\Current Projects\SHELDON Executive Interface\

- SHELDON.html - Main interface
- SHELDON Executive Interface.md - This tracking doc
- Snowflake KPI Queries.md - SQL queries for Snowflake
- KPI Explained.md - KPI definitions for Dennis
- KPI Tracker.md - Implementation tracker

---

## Technical Notes

### Briefing Webhook Performance
- Snowflake queries take ~55-60 seconds
- SHELDON prefetches briefing data on welcome screen load
- 120 second timeout configured
- JSON response requires line break cleanup (Make adds carriage returns)

### Key JavaScript Functions
- prefetchBriefingData() - Loads briefing while welcome screen shows
- playWelcomeBriefing() - Speaks and displays briefing
- updateBriefingPanel(data) - Updates Executive Briefing panel
- updateKPIsFromData(data) - Updates KPI cards and Operations panel
- checkForAlerts() - Fetches red flags
- updateRedFlags(data) - Updates Command Center red flags

---

## Next Steps

1. Get Sage X3 access (company laptop) for Financial/Inventory KPIs
2. Add Schedule Attainment from Redzone if available
3. Wire People panel to HR data
4. Wire Quality panel to quality system
5. Optimize Snowflake queries for faster briefing load
6. Test with Dennis for feedback

---

*Last Updated: January 12, 2026

**Upcoming:** Meeting with Dennis scheduled for Wednesday, January 14, 2026*
