# SHELDON Executive Interface - Comprehensive Capabilities Report
**Generated:** January 4, 2026
**Purpose:** Full system analysis and questions for Dennis Straub

---

## 1. COMPLETE CAPABILITIES LIST

### A. Data Sources Connected

| Source | Type | Status | What It Provides |
|--------|------|--------|------------------|
| **Snowflake** | Redzone MES | Active | OEE, production, downtime, labor (91+ views) |
| **Sage X3** | SQL Server | Active | Revenue, inventory, AR, financial data |
| **OpenAI** | AI Chat | Active | gpt-4o-mini for SHELDON persona |

### B. Live KPIs Currently Displayed

**Operations (Snowflake/Redzone)**
- Plant OEE (Overall Equipment Effectiveness)
- Quality, Availability, Performance metrics
- Total Output (24-hour production units)
- Downtime Hours (planned + unplanned)
- Lines Reporting / Active Lines
- Problem Lines (below 70% OEE)

**Financial (Sage X3)**
- Revenue: Daily / MTD / YTD
- Inventory Total Value: $108.4M
  - FD1 (Foods): $44.7M
  - PK1 (Pack): $16.1M
  - TP1 (TPL): $47.6M
- AR Days: 45 days
- Cash Position: $3.0M
- Gross Margin: 19.4%
- Inventory Turns: 111.0x

### C. Features Available

| Feature | Status | Description |
|---------|--------|-------------|
| Dashboard | Working | 8 KPI cards with comparison badges |
| AI Chat | Working | OpenAI-powered SHELDON persona |
| Text-to-Speech | Working | Browser-native, zero cost |
| Executive Briefing | Working | Auto-generated summary on load |
| Red Flags Panel | Partial | Framework ready, needs threshold config |
| PDF Export | Working | Full dashboard screenshot |
| Data Polling | Working | 60-second auto-refresh |
| Operations Panel | Working | Downtime breakdown, OEE by line |
| Financial Panel | Working | Live revenue, margin, cash |
| Inventory Panel | Working | Value by facility, FG breakdown |

### D. API Endpoints (12 Total)

**Operations:**
- `GET /api/kpi/live` - Plant OEE, production metrics
- `GET /api/redflags` - Low OEE alerts
- `GET /api/operations/downtime` - Downtime breakdown
- `GET /api/operations/labor` - Labor productivity
- `GET /api/operations/trend` - Hourly OEE trend
- `GET /api/operations/active-lines` - Currently running lines

**Financial:**
- `GET /api/financial/revenue` - Daily/MTD/YTD
- `GET /api/financial/kpis` - All financial metrics
- `GET /api/inventory/value` - By facility
- `GET /api/inventory/finished-goods` - FG value
- `GET /api/ar/days` - AR Days

**System:**
- `POST /api/chat` - AI chat (OpenAI)
- `GET /api/briefing` - Executive briefing
- `GET /api/health` - API health check

---

## 2. DATA SOURCES DEEP DIVE

### Snowflake (Redzone MES)

**Database:** ZGRZDCXCHH_DB / Schema: "ameriqual-org"

**Key Views Used:**
| View | Records | Purpose |
|------|---------|---------|
| v_hourlyperformancesummary | Live | OEE, output, labor by hour |
| v_losses | 32K+ | Downtime with reasons |
| v_losses_comments | 32,338 | Operator notes on downtime |
| v_user | Active | Operator data |
| v_cycle | Active | Production runs |

**Rich Data Available (Not Yet Used):**
- 91+ views total in Redzone
- Skills, training, credentials
- Meetings and communications
- Quality data sheets
- SPC samples

**Insight:** 32,338 operator comments on downtime - rich source for AI analysis:
- Top issues: Leakers (141 mentions), pickup issues (60+), equipment wear (30+)
- 266 unique operators contributing
- Foods site generates 99% of notes

### Sage X3 / SQL Server

**Connection:** OAuth 2.0 → Power Automate → SQL Query

**Tables Used:**
| Table | Purpose | Key Field |
|-------|---------|-----------|
| AMQ.SINVOICE | Revenue | AMTATI_0 (amount) |
| AMQ.STOCK | Inventory qty | QTYSTU_0 (quantity) |
| AMQ.ITMCOST | Item costs | CSTTOT_0 (unit cost) |
| AMQ.GACCOUNT | GL accounts | Cash position |

**Tables Available (Future Use):**
- AMQ.ITMMASTER - Item master
- AMQ.BALANCE - Balance sheet
- AMQ.BPCUSTOMER - Customer master (AR analysis)
- 1,400+ total tables in AMQ schema

---

## 3. CURRENT LIMITATIONS & GAPS

### Incomplete Panels

| Panel | Status | Blocker |
|-------|--------|---------|
| People | Framework only | No HR/payroll data source |
| Quality | Framework only | No quality system integration |
| Marketing | Framework only | No CRM/pipeline data |
| INST Business | Framework only | Needs INST-specific data split |
| Board Report | Placeholder | Not implemented |
| What-If Analysis | Placeholder | Concept only |

### Missing Metrics

- EBITDA (optional - Gross Margin covers profitability)
- Schedule Attainment (exists in Redzone, not queried)
- Period comparisons (vs last week, vs budget)
- Inventory threshold alerts (SKUs below safety stock)
- Quality holds and rework tracking
- Customer profitability analysis
- Cash flow forecasting

### Known Issues

| Issue | Impact | Status |
|-------|--------|--------|
| Red flags query failing | Console errors | Fixed to fail gracefully |
| Briefing load time 55-60s | Slow first load | Needs caching strategy |
| No conversation persistence | Chat resets on refresh | Enhancement needed |
| Dark theme unpresentable | Board meeting concern | Needs light theme option |

### UI/UX Concerns (from Executive Critique)

1. Welcome screen creates friction (delays before dashboard)
2. Too much visual noise (animations prioritize aesthetics over function)
3. Chat takes 1/3 of prime screen space
4. Red flags lack actionability (no owner, cause, status)
5. No comparison context on metrics (vs prior period/target)
6. Dark sci-fi theme may be unprofessional for board

---

## 4. QUESTIONS FOR DENNIS

### A. KPI Priorities & Thresholds

1. **Which 3 KPIs matter most for your morning glance?**
   - Currently: OEE, Revenue, Inventory
   - Alternative: Revenue, Schedule Attainment, Cash Position?

2. **What's your OEE alert threshold?**
   - Currently: <70% triggers red flag
   - Should it be different by facility?

3. **What's your target Gross Margin?**
   - Currently showing: 19.4%
   - What triggers concern? (<18%? <15%?)

4. **How many AR Days are acceptable?**
   - Currently: 45 days
   - Target: <40? <35?

5. **What's your target Schedule Attainment?**
   - Not currently displayed
   - Target: 95%? 90%?

6. **Inventory strategy:**
   - Is $108M the right level?
   - Target turnover rate?
   - Which facility concerns you most?

### B. Workflow & Usage Patterns

7. **When do you check SHELDON?**
   - Morning briefing?
   - Throughout the day?
   - Before meetings?

8. **Should voice briefing auto-play?**
   - Currently: Auto-plays on open
   - Prefer: On-demand only?

9. **Who else will use SHELDON?**
   - Just you?
   - Other executives?
   - Operations team?
   - Board members?

10. **What action do you take on red flags?**
    - Who do you call?
    - Should alerts auto-notify someone?
    - Need action tracking?

### C. Missing Data Sources

11. **Schedule Attainment:**
    - How is it calculated?
    - Where is it tracked?

12. **Quality data:**
    - Where stored? (Redzone? Separate system?)
    - Key metrics: Rework %, First Pass Yield, Defects?

13. **People/Labor insights:**
    - Want to see: Staffing? Overtime? Turnover?
    - Data source: HR system? Payroll?

14. **Customer profitability:**
    - Which customers drive most profit?
    - Should unprofitable customers be flagged?

15. **Cash position frequency:**
    - Currently: $3.0M shown
    - Updated: Daily? Weekly? Month-end?
    - Minimum threshold before red flag?

### D. Advanced Features

16. **Forecast vs Actual:**
    - Want: Budget vs Actual revenue?
    - Production plan vs Actual output?

17. **Downtime analysis:**
    - We have 32,338 operator comments
    - Want AI-categorized issues?
    - Flag repeated problems?

18. **Facility ranking:**
    - Rank by: Revenue? OEE? Margin?
    - Any facility concerns?

19. **What-If scenarios:**
    - "What if we run one less shift?"
    - Would you use this feature?

20. **Board reporting:**
    - How often? (Quarterly? Monthly?)
    - Auto-generate board summaries?

### E. Design & Presentation

21. **Board meeting presentation:**
    - Current dark theme too casual?
    - Need light/professional theme?
    - Separate "board view"?

22. **Export needs:**
    - PDF sufficient?
    - Need Excel? PowerPoint?

23. **Mobile access:**
    - Check on phone/tablet?
    - Quick summary view needed?

24. **Data freshness:**
    - 60-second refresh acceptable?
    - Need real-time (<5 sec)?
    - Or slower (5 min) is fine?

25. **Chat memory:**
    - Remember previous conversations?
    - Persist across sessions?

---

## 5. STRATEGIC SUMMARY

### Current State: 80% Complete

**Strengths:**
- Direct database integration (no Make.com dependency)
- Live financial + operational data combined
- Comprehensive data available (91 Snowflake views, 1,400+ Sage tables)
- 32,338 operator downtime comments for AI analysis

**Critical Gaps:**
1. Red flags need threshold config and ownership
2. Metrics lack historical comparison (vs yesterday/budget)
3. 6 of 7 panels still placeholder
4. Briefing takes 55-60 seconds

### Recommended Next Phase

1. **Meet with Dennis** - Define red flag thresholds and priorities
2. **Add comparison context** - "vs yesterday", "vs target" on all KPIs
3. **Build Schedule Attainment** - High-value missing metric
4. **Optimize briefing performance** - Cache strategy needed
5. **Consider light theme** - For board presentations

---

*Report generated from comprehensive analysis of all SHELDON project files*
