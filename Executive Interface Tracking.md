# SHELDON Executive Interface - Project Tracking

## Project Overview
**Client:** AmeriQual Foods
**Executive User:** Dennis Straub (President & CEO)
**Interface Name:** SHELDON (Executive Intelligence System)
**Status:** Interface Complete - Building Automations

---

## Data Sources

### Primary Systems

| System | Type | Purpose | Connection Method |
|--------|------|---------|-------------------|
| **Sage X3** | ERP | Core business data | SQL Database |
| **SQL Server** | Database | Primary data store (Sage X3 backend) | Direct SQL queries |
| **Snowflake** | Data Warehouse | Analytics/reporting data | Snowflake connector |
| **Redzone** | MES | Production/operations data | API or SQL |
| **Ignition** | SCADA/MES | Real-time operations data | API or SQL |

### Data Flow
```
Sage X3 (ERP) ──► SQL Server ──► HTTP Calls ──► Make.com ──► SHELDON Interface
Snowflake ─────────────────────► HTTP Calls ──►
Redzone ───────────────────────► HTTP Calls ──►
Ignition ──────────────────────► HTTP Calls ──►
```

### Connection Method: HTTP Calls via Make.com
**Confirmed:** All data connections will use HTTP calls within Make.com
- HTTP calls already set up and working in Make.com
- SQL data accessible via HTTP endpoints
- Make.com serves as the central orchestration hub

### SQL Connection Details (Confirmed December 12, 2024)

**Authentication:** Microsoft OAuth 2.0 (Client Credentials Flow)
```
Token Endpoint: https://login.microsoftonline.com/64fa12be-ad4d-4585-a99c-d3fd32eb91b4/oauth2/v2.0/token
Grant Type: client_credentials
Client ID: 8663f23a-d277-4adc-bae8-5332d63e5104
Scope: https://service.flow.microsoft.com//.default
```

**Power Automate SQL Endpoint:**
```
URL: https://default64fa12bead4d4585a99cd3fd32eb91.b4.environment.api.powerplatform.com/powerautomate/automations/direct/workflows/e3c551c90ce44c2f819e820f834710ff/triggers/manual/paths/invoke?api-version=1
Method: POST
Headers:
  - Content-Type: application/json
  - Authorization: Bearer [token from OAuth]
```

**Request Body Format:**
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT ... FROM AMQ.TableName ..."
}
```

**Database Details:**
- Server: `AQFDB1\X3`
- Database: `x3`
- Schema: `AMQ`

**Known Sage X3 Tables:**
| Table | Purpose |
|-------|---------|
| `AMQ.MFGHEAD` | Manufacturing headers (work orders) |
| `AMQ.MFGITM` | Manufacturing items |
| `AMQ.ITMMASTER` | Item master data |

### Architecture Decision (December 11, 2024)
**Selected: Option A - Make.com as Data Hub**

```
┌─────────────────────────────────────────────────────────────────┐
│                        SHELDON Interface                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Make.com Webhooks                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  /briefing ────► HTTP to SQL ────► Financial KPIs               │
│              ────► HTTP to SQL ────► Inventory Alerts            │
│              ────► HTTP to SQL ────► Operations Data             │
│              ────► Aggregate + Check Thresholds                  │
│              ────► Return JSON                                   │
│                                                                  │
│  /kpi-live ────► HTTP to SQL ────► Real-time metrics            │
│                                                                  │
│  /red-flags ───► HTTP to SQL ────► Threshold checks             │
│                                                                  │
│  /financial ───► HTTP to SQL ────► Deep financial data          │
│                                                                  │
│  /inventory ───► HTTP to SQL ────► Full inventory breakdown     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SQL Server (Sage X3)                         │
│                     Snowflake                                    │
│                     Redzone                                      │
│                     Ignition                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Rationale:**
- All logic centralized in Make.com (easy to update/debug)
- Interface stays simple and clean
- Visual debugging in Make.com
- Easy to add new data sources later
- Single point of control for Dennis long-term

---

## Report Categories & Data Mapping

### 1. Financial Information
**Source:** Sage X3 / SQL Server
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Full Financial Statements | TBD | Pending | `[webhook-url]` |
| Contribution Margin by SKU | TBD | Pending | `[webhook-url]` |
| Customer Profitability | TBD | Pending | `[webhook-url]` |
| Cash Flow Forecasting | TBD | Pending | `[webhook-url]` |
| Banking Summary | TBD | Pending | `[webhook-url]` |
| Revenue (Daily) | TBD | Pending | `[webhook-url]` |
| Gross Margin | TBD | Pending | `[webhook-url]` |
| EBITDA | TBD | Pending | `[webhook-url]` |
| AR Days | TBD | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- Cash position below $X
- AR Days > X days
- Margin below X%

---

### 2. Inventory Analysis
**Source:** Sage X3 / SQL Server
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Total Inventory Value | TBD | Pending | `[webhook-url]` |
| Inventory by Status (FG, WIP, RM) | TBD | Pending | `[webhook-url]` |
| Inventory by Customer | TBD | Pending | `[webhook-url]` |
| Inventory by Segment | TBD | Pending | `[webhook-url]` |
| Days on Hand | TBD | Pending | `[webhook-url]` |
| POs in System | TBD | Pending | `[webhook-url]` |
| Inventory Turns | TBD | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- SKU below X days safety stock
- Inventory turns below X
- Excess inventory > $X

---

### 3. INST Business Summary
**Source:** Sage X3 / SQL Server
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Sales by Customer | TBD | Pending | `[webhook-url]` |
| INST Inventory | TBD | Pending | `[webhook-url]` |
| Days on Hand | TBD | Pending | `[webhook-url]` |
| POs in System | TBD | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- TBD based on business rules

---

### 4. Operational Performance
**Source:** Redzone / Ignition / SQL
**Status:** Not Started

| Metric | Source System | Query Status | Webhook |
|--------|--------------|--------------|---------|
| OEE by Line | Redzone | Pending | `[webhook-url]` |
| Schedule Attainment | Redzone | Pending | `[webhook-url]` |
| Labor by Line | Redzone | Pending | `[webhook-url]` |
| Production Rate | Ignition | Pending | `[webhook-url]` |
| Downtime | Redzone/Ignition | Pending | `[webhook-url]` |
| Lines Active | Ignition | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- OEE below X%
- Throughput decrease > X%
- Unplanned downtime > X hours

---

### 5. People
**Source:** TBD (HRIS/Payroll system?)
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Total Employees by Function | TBD | Pending | `[webhook-url]` |
| Temp vs Full Time | TBD | Pending | `[webhook-url]` |
| Open Positions | TBD | Pending | `[webhook-url]` |
| KPIs by Function | TBD | Pending | `[webhook-url]` |
| KPIs by Person | TBD | Pending | `[webhook-url]` |
| Attendance Rate | TBD | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- Attendance below X%
- Open positions > X
- Overtime hours > X

---

### 6. Quality
**Source:** Sage X3 / Redzone / SQL
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Rework Rate | TBD | Pending | `[webhook-url]` |
| Past Due Releases | TBD | Pending | `[webhook-url]` |
| Quality Issues Summary | TBD | Pending | `[webhook-url]` |
| MRE Quality Ratings | TBD | Pending | `[webhook-url]` |
| First Pass Yield | TBD | Pending | `[webhook-url]` |
| Defect Rate | TBD | Pending | `[webhook-url]` |

**Future Integration:** Quality AI Group data

**Red Flag Thresholds:**
- Rework rate > X%
- Past due releases > X
- Quality score below X%

---

### 7. Marketing
**Source:** TBD (CRM? Spreadsheets?)
**Status:** Not Started

| Metric | SQL Table/View | Query Status | Webhook |
|--------|---------------|--------------|---------|
| Customer Targets | TBD | Pending | `[webhook-url]` |
| Active Contracts | TBD | Pending | `[webhook-url]` |
| Trade Shows | TBD | Pending | `[webhook-url]` |
| Customer Visits | TBD | Pending | `[webhook-url]` |
| R&D Summary | TBD | Pending | `[webhook-url]` |
| Pipeline Value | TBD | Pending | `[webhook-url]` |
| Win Rate | TBD | Pending | `[webhook-url]` |

**Red Flag Thresholds:**
- Pipeline below $X
- Contract expiring within X days

---

## Webhooks Registry

### Active Webhooks (Working)
| Name | URL | Purpose |
|------|-----|---------|
| Chat | `https://hook.us2.make.com/3eftqahiejqpw3yr2va4993aqkdoipgs` | AI Chat |
| TTS | `https://hook.us2.make.com/lypllp614zvrjplgpm16lhzbk7heykgm` | Text-to-Speech (NOT USED - see below) |

### TTS Decision (December 11, 2024)
**Using: FREE Browser-Based TTS (Web Speech API)**
- No external service calls
- No cost
- Built into Chrome/Edge/Firefox/Safari
- Voice: Auto-selects best available English voice (Microsoft David, Google UK Male, etc.)
- Paid TTS webhook exists but intentionally NOT used to keep costs at $0

### Webhooks to Build
| Name | Purpose | Priority | Status |
|------|---------|----------|--------|
| `kpiLive` | Real-time KPI updates | HIGH | Not Started |
| `briefing` | Daily executive briefing | HIGH | Not Started |
| `redFlags` | Alert detection | HIGH | Not Started |
| `morningReport` | Morning report generation | MEDIUM | Not Started |
| `boardReport` | Board package compilation | LOW | Not Started |
| `whatIf` | Scenario analysis | LOW | Not Started |
| `competitor` | Competitor intelligence | LOW | Not Started |

---

## Make.com Scenarios to Build

### Phase 1: Core Data (Priority)
1. **Daily KPI Aggregator**
   - Pull from: SQL (Sage X3), Redzone, Ignition
   - Output: JSON with all top-level KPIs
   - Frequency: Every 5-15 minutes

2. **Red Flag Monitor**
   - Check thresholds across all systems
   - Trigger alerts when exceeded
   - Push to interface

3. **Executive Briefing Generator**
   - Compile daily summary
   - Identify highlights and issues
   - Format for TTS

### Phase 2: Category Deep Dives
4. Financial Details Scenario
5. Inventory Details Scenario
6. Operations Details Scenario
7. Quality Details Scenario
8. People Details Scenario
9. Marketing Details Scenario
10. INST Business Scenario

### Phase 3: Advanced Features
11. What-If Analysis Engine
12. Period Comparison Tool
13. Board Package Generator
14. Competitor Intelligence Aggregator

---

## SQL Queries Library

### Financial Queries
```sql
-- Template: Daily Revenue
-- Table: TBD
-- Status: Pending

-- Template: Gross Margin
-- Table: TBD
-- Status: Pending
```

### Inventory Queries
```sql
-- Template: Total Inventory by Status
-- Table: TBD
-- Status: Pending

-- Template: Days on Hand
-- Table: TBD
-- Status: Pending
```

### Operations Queries
```sql
-- Template: OEE by Line
-- Source: Redzone
-- Status: Pending
```

---

## Implementation Progress

### Completed
- [x] SHELDON Interface HTML/CSS/JS
- [x] Welcome experience with greeting
- [x] TTS system (browser-based)
- [x] Chat interface connected to webhook
- [x] KPI cards with drill-down
- [x] Red flags panel UI
- [x] Quick actions UI
- [x] Category cards for all 7 report types
- [x] Navigation tabs
- [x] Executives Calendar Tab (Jan 16, 2026)
  - Day/Week/2Week/Month/3Month/6Month/Year views
  - Executive sidebar with status indicators
  - Event detail modal with attendees
  - Client/Customer meeting highlighting
  - AI chat integration (can answer "what's on the schedule")
  - Waiting on MS Graph permissions for live calendar data

### In Progress
- [x] SQL connection via Make.com - ✅ CONFIRMED WORKING
- [ ] KPI data webhook
- [ ] Red flag detection logic

### Pending
- [ ] All category-specific webhooks
- [ ] Historical data storage
- [ ] Period comparison logic
- [ ] Board package generation
- [ ] Export functionality

---

## Questions to Resolve

1. ~~**SQL Access:** How will Make.com connect to SQL Server?~~
   - ✅ **RESOLVED:** OAuth 2.0 → Power Automate HTTP trigger → SQL query

2. ~~**HTTP Response Format:** What format does SQL HTTP call return?~~
   - ✅ **RESOLVED:** JSON (parsed automatically by Make.com)

3. ~~**Sage X3 Schema:** Need table/view names for key data~~
   - ✅ **RESOLVED (Dec 26, 2024):** Key tables identified and documented
   - **Revenue:** `AMQ.SINVOICE` - Sales invoices (AMTATI_0 = total amount)
   - **Inventory:** `AMQ.STOCK` - Current stock positions (QTYSTU_0 = quantity)
   - **Full documentation:** See `Sage X3 Data Dictionary.md`

4. **Redzone API:** Documentation for pulling OEE/production data

5. **Ignition Access:** How to query real-time operations data

6. **Refresh Frequency:** How often should each data type update?
   - Real-time (seconds)
   - Near real-time (minutes)
   - Periodic (hourly/daily)

7. **Historical Data:** How much history to retain for comparisons?

8. **User Authentication:** Will other executives access this?

---

## Meeting Notes

### December 11, 2024 - Initial Planning & Architecture
- Interface design approved and completed
- Data sources identified: SQL (Sage X3), Snowflake, Redzone, Ignition
- Priority: Start with SQL-based financial and inventory data
- **Architecture Decision:** Make.com as central data hub
- **Connection Method:** HTTP calls (already working in Make.com)
- **Action Items:**
  - [x] Get sample HTTP call structure/endpoint from Make.com
  - [ ] Gather Sage X3 table/view documentation
  - [ ] Get sample reports from Dennis for data mapping

### December 12, 2024 - SQL Connection Confirmed
- Full HTTP call flow documented and working
- **Auth Flow:** OAuth 2.0 Client Credentials → Bearer Token → Power Automate
- **SQL Access:** POST to Power Automate workflow with JSON body containing query
- **Database:** `AQFDB1\X3` / `x3` / Schema: `AMQ`
- **Known Tables:** `MFGHEAD`, `MFGITM`, `ITMMASTER`
- **Action Items:**
  - [x] Get Sage X3 table names for Financial metrics (Revenue, AR, Margin) ✅ Dec 26
  - [x] Get Sage X3 table names for Inventory metrics ✅ Dec 26
  - [ ] Build first test webhook for KPI data
  - [ ] Get sample report from Dennis for data mapping

### December 26, 2024 - Sage X3 Live Integration Complete
- **Company laptop now has Sage X3 access** - major blocker removed!
- Explored full AMQ schema (1,400+ tables)
- **Key tables identified and documented:**
  - `SINVOICE` - Sales invoices (Revenue) - AMTATI_0 field for total amount
  - `STOCK` - Current inventory positions - QTYSTU_0 for quantity
  - `ITMCOST` - Item costs for inventory valuation - CSTTOT_0 for unit cost
- **Created:** `Sage X3 Data Dictionary.md` with full field documentation
- **Built Make.com Webhooks:**
  - Financial KPIs: `https://hook.us2.make.com/4slwqk6jdoky1n6fk13kpfky9qr5vpwq`
  - Inventory KPIs: `https://hook.us2.make.com/tw4462qo2h4xokc9s2roptchstul9vy3`
- **SHELDON Now Live with Sage X3 Data:**
  - Revenue Today: $38.00M (MTD from SINVOICE)
  - Inventory Turns: 111.0x (from STOCK + ITMCOST join)
  - Inventory Total Value: $111.0M (FD1: $44.7M, PK1: $16.1M, TP1: $50.2M)
- **Still Static (Future Work):**
  - Financial Overview: Gross Margin, EBITDA, Cash Position, AR Days
  - Inventory: Finished Goods breakdown, Days on Hand calculation

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Interface | `C:\Users\condo\SHELDON.html` | Main dashboard |
| Tracking | This file | Project tracking |
| Data Dictionary | `Sage X3 Data Dictionary.md` | Sage X3 table/field documentation |
| KPI Queries | `Snowflake KPI Queries.md` | Snowflake SQL queries |

---

*Last Updated: January 16, 2026 - Major update: Calendar integration complete, all panels populated*

---

## Session Update - January 16, 2026 (Evening)

### Completed This Session

#### 1. EBITDA Calculation ✅
- Added `/api/financial/ebitda` endpoint
- Hybrid approach: Revenue/COGS from invoices + D&A from BALANCE table
- Current value: $5.01M MTD
- Components: Revenue $12.07M, COGS $9.88M, Depreciation $2.42M, Amortization $0.40M

#### 2. AR Days Calculation Fixed ✅
- Now calculates weighted average from aging buckets (was hardcoded to 45)
- Current value: 117.5 days (most AR is over 90 days)
- Endpoint: `/api/ar/days`

#### 3. Overall Health Score ✅
- New endpoint: `/api/health-score`
- Composite score 0-100 based on weighted KPIs
- Current value: 78 (Good status)
- Weights: OEE (25%), Quality (20%), Gross Margin (20%), AR Days (15%), Inventory (10%), Availability (10%)
- Color-coded display: Green (excellent), Cyan (good), Yellow (fair), Red (needs attention)

#### 4. People Panel Populated ✅
- New endpoint: `/api/people/summary`
- Data from Snowflake/Redzone plant_oee query
- Current values: 152 headcount, 100% attendance, 19 lines staffed, 2,625.7 units/manhour
- Headcount estimated from manhours (real HR system would be better)

#### 5. Quality Panel Populated ✅
- New endpoint: `/api/quality/summary`
- Data from Snowflake/Redzone
- Current values: 98.4% First Pass Yield, 3.2M total output
- Certifications listed: SQF, FSSC 22000, Organic

#### 6. Drill-Down Modals Enhanced ✅
- Production: Live line-by-line OEE data with status badges
- Quality: Real FPY, output, and certifications
- Labor: Real headcount, productivity, staffing
- Revenue: Estimated segment breakdown with AR data
- Inventory: Facility-by-facility breakdown

#### 7. Microsoft Graph Calendar Integration ✅
- **Permissions granted by Ayden:** Calendars.Read, User.Read.All, Presence.Read.All
- Added `MicrosoftGraphClient` class to sheldon_api.py
- `/api/calendar/events` now returns LIVE Outlook calendar data
- `/api/calendar/executives` returns executive list with presence status
- Dennis Straub's calendar showing real meetings

### New API Endpoints Added
```
GET /api/health-score       - Overall business health score (0-100)
GET /api/people/summary     - Headcount, attendance, productivity
GET /api/quality/summary    - First pass yield, defects, audits
GET /api/financial/ebitda   - EBITDA calculation
```

### Azure AD / Microsoft Graph Details
```
Tenant ID: 64fa12be-ad4d-4585-a99c-d3fd32eb91b4
Client ID: 8663f23a-d277-4adc-bae8-5332d63e5104
Permissions Granted: Calendars.Read, User.Read.All, Presence.Read.All
```

---

## Next Steps (Priority Order)

### Completed Dec 26
- ~~Query ITMCOST for inventory valuation~~ ✅
- ~~Build revenue query from SINVOICE~~ ✅
- ~~Connect Financial Overview panel~~ ✅ (Revenue, AR Days, Cash, Gross Margin)
- ~~Connect Inventory panel~~ ✅ (Total Value, FG, Days on Hand)
- ~~Operations Panel~~ ✅ (OEE, Lines Active, Downtime via Redzone kpiLive)
- ~~Red Flags~~ ✅ (Low OEE alerts from Redzone - already returning J2 at 42.6%)
- ~~Executive Briefing~~ ✅ (webhook connected and working)
- ~~Days on Hand~~ ✅ (calculated client-side: 94 days)
- ~~Cash Position~~ ✅ (3.0M live from GL accounts)
- ~~Gross Margin~~ ✅ (19.4% from SINVOICED cost/revenue)

### Completed Jan 16, 2026
- ~~EBITDA Calculation~~ ✅ ($5.01M MTD)
- ~~AR Days Calculation~~ ✅ (117.5 days weighted average)
- ~~Overall Health Score~~ ✅ (78 - Good status)
- ~~People Panel~~ ✅ (152 headcount from Redzone)
- ~~Quality Panel~~ ✅ (98.4% FPY from Redzone)
- ~~Drill-Down Modals~~ ✅ (Live data in all modals)
- ~~Microsoft Graph Calendar~~ ✅ (Live Outlook calendar integrated)

### Remaining Tasks
1. **Add More Executives to Calendar:** Need list of executives (names, emails, titles) from Dennis
2. **Marketing Panel:** Needs CRM/sales pipeline data source
3. **Inventory Threshold Alerts:** Could query Sage for SKUs below safety stock
4. **Test with Dennis:** Demo the fully live dashboard

### Executive List to Add (Need from Dennis)
Currently only Dennis Straub is configured. To add more executives to the calendar view:
1. Get their email addresses
2. Add to EXECUTIVES list in `sheldon_api.py` (line ~1431)
3. Calendar will automatically pull their events
