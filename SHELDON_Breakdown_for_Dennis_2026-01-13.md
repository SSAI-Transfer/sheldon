# SHELDON Executive Interface — Breakdown for Dennis
**Date:** January 13, 2026
**Prepared by:** Brandon Carr

---

## What is SHELDON?

An executive intelligence dashboard that pulls live data from Redzone (operations) and Sage X3 (financials) into one screen, with an AI assistant that can answer questions in plain English.

**Goal:** Dennis starts his day knowing exactly what needs attention — without digging through reports or waiting on analysts.

---

## Current Capabilities

### Live Dashboard
| Feature | Status |
|---------|--------|
| 8 KPI cards with comparison badges | Working |
| AI Chat (ask questions in plain English) | Working |
| Executive Briefing (auto-generated summary) | Working |
| Voice briefing (speaks the summary) | Working |
| PDF Export | Working |
| 60-second auto-refresh | Working |
| Operations Panel (downtime, OEE by line) | Working |
| Financial Panel (revenue, margin, cash) | Working |
| Inventory Panel (value by facility) | Working |

### Data Sources Connected

| System | Connection | Data Provided |
|--------|------------|---------------|
| Snowflake (Redzone MES) | Direct | OEE, production, downtime, labor |
| Sage X3 | SQL Server | Revenue, inventory, AR, cash, margin |
| OpenAI | API | AI chat responses |

**No Make.com dependency** — runs entirely on local Python API.

---

## Live KPIs Currently Displayed

### Operations (from Redzone)
- Plant OEE (Overall Equipment Effectiveness)
- Quality, Availability, Performance
- Total Output (24-hour production)
- Downtime Hours (planned + unplanned)
- Lines Reporting / Active Lines
- Problem Lines (below 70% OEE)

### Financial (from Sage X3)
- Revenue: Daily / MTD / YTD
- Gross Margin: 19.4%
- Cash Position: $3.0M
- AR Days: 45 days

### Inventory (from Sage X3)
- Total Value: $108.4M
  - FD1 (Foods): $44.7M
  - PK1 (Pack): $16.1M
  - TP1 (TPL): $47.6M
- Inventory Turns: 111.0x

---

## What's Working Well

1. **Single screen** — Operations + Financials + Inventory in one place
2. **Live data** — Refreshes every 60 seconds
3. **AI chat** — Ask questions like "What's causing downtime today?"
4. **Morning briefing** — Auto-generated summary on load
5. **No analyst required** — Self-service for executives

---

## Known Limitations

| Issue | Impact | Fix |
|-------|--------|-----|
| Briefing takes 55-60 sec | Slow first load | Needs caching strategy |
| Red flags query failing | Errors in console | Needs threshold config from Dennis |
| Chat resets on refresh | No conversation memory | Enhancement needed |
| Dark theme only | May be too casual for board | Light theme option needed |

---

## Panels Not Yet Built

| Panel | Blocker |
|-------|---------|
| People | No HR/payroll data source connected |
| Quality | No quality system integration |
| Marketing/Sales | No CRM/pipeline data |
| Board Report | Not yet implemented |
| What-If Analysis | Concept only |

---

## Decisions Needed from Dennis

### KPI Priorities
1. **Which 3 KPIs matter most for your morning glance?**
   - Currently showing: OEE, Revenue, Inventory
   - Alternatives: Schedule Attainment? Cash Position?

2. **What's your OEE alert threshold?**
   - Currently: <70% triggers red flag
   - Should it vary by facility?

3. **What's your target Gross Margin?**
   - Currently: 19.4%
   - What triggers concern? <18%? <15%?

4. **How many AR Days are acceptable?**
   - Currently: 45 days
   - Target: <40? <35?

### Usage & Access
5. **When will you check SHELDON?**
   - Morning briefing only?
   - Throughout the day?
   - Before meetings?

6. **Who else should have access?**
   - Just you?
   - Other executives?
   - Operations team?

### Design
7. **Do you need a light theme for board presentations?**
   - Current dark/sci-fi theme may be too casual

8. **Should voice briefing auto-play or be on-demand?**

### Competitive Intelligence
9. **Who are the biggest competitors you'd like to watch?**
   - SHELDON can potentially track competitor news, pricing, market moves
   - Which companies should be on your radar?

### Timing
10. **What time do you normally intend to check in with SHELDON in the mornings?**
    - Helps us optimize when data refreshes and briefings are ready
    - Before coffee? After first meeting? Specific time?

---

## Architecture (Simple View)

```
┌─────────────────────────────────┐
│     SHELDON.html (Browser)      │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│   sheldon_api.py (Flask API)    │
│      localhost:5000             │
└───────────────┬─────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
Snowflake    Sage X3     OpenAI
(Redzone)    (SQL)       (Chat)
```

---

## Overall Status

### Completion: ~80%

**What's solid:**
- Live operational data from Redzone
- Live financial data from Sage X3
- AI chat working
- No external dependencies (Make.com eliminated)

**What's needed:**
- Red flag thresholds defined by Dennis
- Historical comparisons (vs yesterday, vs target)
- Faster briefing load time
- Light theme for board presentations

---

## Next Steps After This Meeting

1. Configure red flag thresholds based on Dennis's input
2. Add comparison context ("vs yesterday", "vs target") to KPIs
3. Build Schedule Attainment if Dennis wants it
4. Add light theme option
5. Test with Dennis for weekly feedback

---

## The Vision

SHELDON becomes Dennis's daily operating system — one screen that tells him what's working, what's broken, and what needs his attention. No digging. No waiting. Just answers.

**"Your business, at a glance. Your AI, always watching."**

---

*Document prepared for Dennis Straub meeting — January 13, 2026*
