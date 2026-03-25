# SHELDON Technical Issues Checklist

**Created:** December 28, 2024
**Focus:** Technical functionality (complements Executive Critique.md which covers UX/design)
**Priority Order:** Critical → High → Medium → Lower

---

## CRITICAL - Must Fix First

- [x] **1. Chat Has No Memory** *(FIXED Dec 28)*
  - Problem: Each message sent independently with no conversation history
  - Impact: SHELDON forgets everything after each response, can't hold a conversation
  - Fix: Added `conversationHistory` array, sends full context with each request
  - Added: Clear chat button, initial briefing added to history, max 20 messages

- [x] **2. All Data is Fake/Hardcoded** *(FIXED Dec 28)*
  - Problem: Every KPI, metric, and briefing text was static or randomly generated
  - Fix: Replaced all hardcoded values with "--" placeholders awaiting live data
  - Status: Dashboard now shows placeholders until webhooks populate real data

- [x] **3. Data Webhooks Not Connected** *(MOSTLY FIXED Dec 28)*
  - 11 webhooks connected: chat, tts, kpiLive, briefing, redFlags, financialKPIs, inventoryKPIs, arDays, finishedGoods, cashPosition, grossMargin, morningReport
  - 3 still placeholder: boardReport, whatIf, competitor

---

## HIGH - Fix After Critical Items

- [x] **4. Navigation Tabs Don't Work** *(FIXED Dec 28)*
  - Problem: Clicking tabs only speaks "Switching to X view" - content doesn't change
  - Fix: Implemented tab switching - Overview shows all, individual tabs show expanded category view
  - Added: Expanded card CSS, INST Business special handling

- [x] **5. Drill-Down is Fake** *(FIXED Dec 28)*
  - Problem: Clicking KPIs or "Details" buttons shows canned message only
  - Fix: Built full modal system with detailed views for all 6 KPI categories
  - Added: Stats grids, data tables, status badges, "Ask SHELDON" button, Escape to close

- [x] **6. Export Features Do Nothing** *(FIXED Dec 28)*
  - Problem: "Export to PDF" and "Sent to email" are fake confirmations
  - Fix: Implemented real PDF export using jsPDF + html2canvas
  - Added: exportBriefing() for formatted report, exportDashboard() for screenshot

---

## MEDIUM - Professional Polish

- [x] **7. Data Freshness Indicator** *(ADDED Dec 28)*
  - Added "Data Updated" timestamp in header
  - All fetch functions call updateDataTimestamp() on success
  - Turns orange/stale after 5 minutes without update

- [ ] **8. Period Comparison is Stub**
  - Problem: Just asks what to compare, can't actually do comparison
  - Fix: Build comparison logic and visualization

- [ ] **9. No Charts/Visualizations**
  - Problem: Space allocated for charts but none implemented
  - Fix: Add Chart.js or similar for trend visualizations

---

## LOWER - Nice to Have

- [ ] **10. Auto-Voice May Be Jarring**
  - Problem: Briefing starts speaking immediately on dashboard entry
  - Fix: Add preference setting or confirmation before auto-play

- [ ] **11. No User Preferences**
  - Problem: Can't customize thresholds, favorite KPIs, notifications
  - Fix: Add settings panel with localStorage persistence

- [ ] **12. No Security/Authentication**
  - Problem: No login, anyone can access
  - Fix: Add authentication layer (lower priority for demo)

---

## COMPLETED TODAY (Dec 28 - Evening Session)

- [x] **Last Updated Timestamp** - Data freshness indicator in header
- [x] **KPI Comparison Values** - "vs target" badges with color coding on all 6 KPI cards
- [x] **Collapsible Chat Panel** - Toggle button to collapse/expand SHELDON chat
- [x] **Clock Format Fix** - Changed to 12-hour AM/PM, fixed layout shift with min-width
- [x] **Morning Report Automation** - Full Make.com scenario:
  - Webhook: `https://hook.us2.make.com/e44f46x7g3x4kfemdam34bbkn9ltsdnk`
  - Pulls kpiLive, financialKPIs, grossMargin data
  - OpenAI compiles into executive narrative
  - Dynamic button label (Morning/Afternoon Report based on time)
  - Sends timeOfDay parameter for AI prompt

---

## Remaining Webhooks to Build

| Webhook | Purpose | Priority |
|---------|---------|----------|
| boardReport | Generate board-ready summary reports | Medium |
| whatIf | Scenario analysis ("what if we...") | Low |
| competitor | Competitor intelligence | Low |

---

## Next Session Options

1. **Charts/Visualizations** - Add Chart.js for trend lines in category cards
2. **Period Comparison** - Build actual week-over-week, month-over-month logic
3. **Board Report** - Similar to morning report but formatted for board presentation
4. **Auto-Voice Toggle** - Add setting to disable auto-speak on dashboard entry

---

*Last Updated: December 28, 2024 (Evening)*
