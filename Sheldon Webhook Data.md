# SHELDON Webhook Data

## Webhook Configuration (from SHELDON.html)

---

## Active Webhooks (Working)

| Name | URL | Purpose | Status |
|------|-----|---------|--------|
| `chat` | `https://hook.us2.make.com/3eftqahiejqpw3yr2va4993aqkdoipgs` | AI Chat - sends user messages, receives AI responses | **WORKING** |
| `tts` | `https://hook.us2.make.com/lypllp614zvrjplgpm16lhzbk7heykgm` | Text-to-Speech (NOT USED - browser TTS instead) | Available but unused |

---

## Webhooks to Build

### Data Retrieval (HIGH Priority)

| Name | Placeholder | Purpose | Expected Input | Expected Output |
|------|-------------|---------|----------------|-----------------|
| `kpiLive` | `[webhook-url]` | Real-time KPI updates | None or time range | JSON with all top-level KPIs |
| `briefing` | `[webhook-url]` | Daily executive briefing | None | Summary text + key metrics JSON |
| `redFlags` | `[webhook-url]` | Alert/threshold detection | None | Array of alerts with severity |

### Reports (MEDIUM Priority)

| Name | Placeholder | Purpose | Expected Input | Expected Output |
|------|-------------|---------|----------------|-----------------|
| `morningReport` | `[webhook-url]` | Morning report generation | None | Formatted report data |
| `boardReport` | `[webhook-url]` | Board package compilation | Date range | Full board report data |

### Analysis (LOW Priority)

| Name | Placeholder | Purpose | Expected Input | Expected Output |
|------|-------------|---------|----------------|-----------------|
| `whatIf` | `[webhook-url]` | Scenario analysis | Scenario parameters | Projected outcomes |
| `competitor` | `[webhook-url]` | Competitor intelligence | None or company name | Competitor data summary |

---

## Webhook Architecture

```
SHELDON Interface (Browser)
         │
         ▼ HTTP POST (JSON)
┌─────────────────────────────────┐
│     Make.com Webhook            │
├─────────────────────────────────┤
│  1. Receive request             │
│  2. OAuth token → Power Auto    │
│  3. SQL query to Sage X3        │
│  4. Process/aggregate data      │
│  5. Check thresholds (redFlags) │
│  6. Return JSON response        │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Data Sources                   │
│  - Sage X3 (SQL Server)         │
│  - Snowflake                    │
│  - Redzone                      │
│  - Ignition                     │
└─────────────────────────────────┘
```

---

## SQL Connection Details

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

---

## Known Sage X3 Tables

| Table | Purpose |
|-------|---------|
| `AMQ.MFGHEAD` | Manufacturing headers (work orders) |
| `AMQ.MFGITM` | Manufacturing items |
| `AMQ.ITMMASTER` | Item master data |

**Tables Still Needed:**
- Financial: Revenue, AR, Margin, Cash Flow
- Inventory: Value, Status, Days on Hand, Turns

---

## Expected JSON Response Formats

### kpiLive Response
```json
{
  "timestamp": "2024-12-17T08:00:00Z",
  "kpis": {
    "revenue": { "value": 1250000, "change": 5.2, "unit": "USD" },
    "oee": { "value": 78.5, "change": -2.1, "unit": "%" },
    "scheduleAttainment": { "value": 94, "change": 1.5, "unit": "%" },
    "arDays": { "value": 42, "change": -3, "unit": "days" },
    "inventoryValue": { "value": 8500000, "change": 0.8, "unit": "USD" },
    "linesActive": { "value": 6, "total": 8 }
  }
}
```

### redFlags Response
```json
{
  "timestamp": "2024-12-17T08:00:00Z",
  "alerts": [
    {
      "id": "rf-001",
      "severity": "high",
      "category": "operations",
      "title": "Line 3 OEE Below Threshold",
      "message": "Line 3 dropped to 62% OEE (threshold: 70%)",
      "value": 62,
      "threshold": 70,
      "timestamp": "2024-12-17T07:45:00Z"
    }
  ],
  "summary": {
    "high": 1,
    "medium": 2,
    "low": 3
  }
}
```

### briefing Response
```json
{
  "timestamp": "2024-12-17T08:00:00Z",
  "greeting": "Good morning, Dennis",
  "summary": "Overall performance is strong today. Revenue is up 5.2% and 6 of 8 lines are running. One item needs attention: Line 3 OEE has dropped below threshold.",
  "highlights": [
    "Revenue up 5.2% vs yesterday",
    "Schedule attainment at 94%",
    "AR Days improved to 42"
  ],
  "concerns": [
    "Line 3 OEE at 62% - maintenance reviewing"
  ],
  "kpis": { ... }
}
```

---

## Implementation Checklist

- [x] Chat webhook - working
- [x] TTS webhook - available (using browser TTS instead)
- [ ] kpiLive webhook
- [ ] briefing webhook
- [ ] redFlags webhook
- [ ] morningReport webhook
- [ ] boardReport webhook
- [ ] whatIf webhook
- [ ] competitor webhook

---

*Last Updated: December 17, 2024*
