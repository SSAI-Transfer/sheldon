# Redzone Shop Floor Communication Analysis

## Overview
**Date Explored:** December 22, 2024
**Purpose:** Analyze operator communication and downtime comments from Redzone
**Potential Use:** Enhanced insights for SHELDON Executive Interface

---

## Data Sources Discovered

### v_losses_comments (Primary - Operator Downtime Notes)
| Metric | Value |
|--------|-------|
| Total Comments | 32,338 |
| Unique Operators | 266 |
| Date Range | Active - data from today |

**What it contains:** Free-text operator explanations for downtime events

### v_comment (System + User Comments)
| Metric | Value |
|--------|-------|
| Total Comments | 8,277,635 |
| Unique Users | 1,464 |
| Date Range | 2017-01-16 to Present |

**Comment Types Available:**
| Type | Count |
|------|-------|
| WORKFLOW | 2,783,292 |
| NULL (user comments) | 2,780,350 |
| SENSOR_COUNT_ADJUSTED | 1,128,951 |
| RETESTED_DATA_SHEET | 664,168 |
| RETRIED_DATA_SHEET | 284,452 |
| MANUAL_RUN_STOP | 76,332 |
| MANUAL_SHIFT_START | 70,137 |
| MANUAL_RUN_START | 69,542 |
| SENSOR_BECAME_BAD | 67,408 |
| SENSOR_BECAME_GOOD | 66,835 |
| MANUAL_SHIFT_STOP | 56,283 |
| MEETING_ENDED | 37,088 |
| And many more... | ... |

### v_blog (Huddle/Kaizen Notes)
| Metric | Value |
|--------|-------|
| Total Posts | 7 |
| Date Range | 2018-2020 |
| Status | Old/sparse - not actively used |

### v_chat (Chat Threads)
- Contains chat metadata (names, subjects, types)
- Types: USER, MY_MENTIONS
- Less useful for text analysis

### v_reaction (Automated Triggers)
- System triggers for data sheets and quality checks
- Not user-generated content

---

## Comments by Site (Last 90 Days)

| Site | Comment Count | Unique Operators |
|------|---------------|------------------|
| Foods | 1,710 | 57 |
| ThermoPac | 12 | 2 |
| Packaging | 7 | 3 |

---

## Top Downtime Reasons from Operator Comments (Last 90 Days)

| Reason | Occurrences |
|--------|-------------|
| leakers | 65 |
| leaker | 57 |
| foldovers from pickup arm with worn bushings | 37 |
| adjusting grippers table and screen settings for atlink pouches | 29 |
| pouch pickup issues | 23 |
| leaking cut | 20 |
| cup impression | 19 |
| leaking cups | 19 |
| pick up | 18 |
| 30 munit break | 17 |
| fault | 16 |
| belt skipped 2 | 15 |
| robot dropping pouches | 15 |
| maintenance try to fixed | 14 |
| pouches between the belts | 13 |
| pouches between belts | 12 |
| sitting too high/ splashing | 11 |
| bucket not picking up all pouches waiting on maintenance | 11 |
| case not coming out maintenance working on it | 11 |
| change pick head | 10 |
| trays stock maintenance working on it | 10 |
| replace broken tube | 10 |

---

## Sample Recent Comments (Dec 2024)

| Time | Operator | Reason Given |
|------|----------|--------------|
| 2025-12-22 10:14 | Jessica Jones | Piece on lane 1 plate curled upwards |
| 2025-12-20 23:48 | Denis Chavarria Canales | Food gun / nozzle |
| 2025-12-20 23:28 | Denis Chavarria Canales | Sitting too high/ splashing |
| 2025-12-20 17:06 | Vil Woodjeri | The mechanic is fixing the tray |
| 2025-12-20 15:15 | Morgan Kunkle | Ultrasonic mean pouches being rejected |
| 2025-12-20 14:10 | Whittney Halfacre | Working on other lines and shift change |
| 2025-12-20 12:34 | Chong Allen | Cam follower |

---

## Key Insights

### Issue Categories Identified
1. **Leaks/Sealing Issues** - leakers, leaking cut, leaking cups (141+ mentions)
2. **Pickup/Handling Issues** - pouch pickup, robot dropping, bucket not picking up
3. **Equipment Wear** - worn bushings, cam follower, broken tube
4. **Adjustments Needed** - grippers, settings, pushers
5. **Maintenance Delays** - waiting on maintenance, mechanic fixing
6. **Planned Stops** - breaks, shift change

### Patterns Observed
- **Foods site** generates 99% of the comments
- Many comments are brief (1-5 words)
- Operators use informal language and abbreviations
- Same issues repeat frequently (leakers, pickup issues)
- Maintenance-related comments indicate equipment reliability issues

---

## SQL Queries

### Get Recent Loss Comments
```sql
SELECT
    "createdDate" as time,
    "firstName" || ' ' || "lastName" as operator,
    "siteName" as site,
    "description" as reason_given
FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_losses_comments"
WHERE "description" IS NOT NULL
  AND "createdDate" >= DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY "createdDate" DESC
LIMIT 30;
```

### Top Downtime Reasons (Last 90 Days)
```sql
SELECT
    LOWER("description") as reason,
    COUNT(*) as occurrences
FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_losses_comments"
WHERE "description" IS NOT NULL
  AND "createdDate" >= DATEADD(day, -90, CURRENT_TIMESTAMP())
GROUP BY LOWER("description")
ORDER BY occurrences DESC
LIMIT 30;
```

### Comments by Site
```sql
SELECT
    "siteName" as site,
    COUNT(*) as comment_count,
    COUNT(DISTINCT "username") as unique_operators
FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_losses_comments"
WHERE "description" IS NOT NULL
  AND "createdDate" >= DATEADD(day, -90, CURRENT_TIMESTAMP())
GROUP BY "siteName"
ORDER BY comment_count DESC;
```

### Comment Volume Stats
```sql
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT "username") as users
FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_losses_comments"
WHERE "description" IS NOT NULL;
```

### System Comment Types Breakdown
```sql
SELECT
    "systemCommentType" as comment_type,
    COUNT(*) as count
FROM "ZGRZDCXCHH_DB"."ameriqual-org"."v_comment"
GROUP BY "systemCommentType"
ORDER BY count DESC;
```

---

## Potential Features to Build

### 1. AI Issue Categorizer
Use Claude/GPT to automatically categorize free-text comments into standard buckets:
- Equipment failure
- Material issue
- Operator adjustment
- Planned break
- Quality issue

Then trend these categories over time.

### 2. Recurring Issue Detector
- Flag when the same issue appears 3+ times in a week
- Alert: "Pouch pickup issues mentioned 23 times this month - investigate root cause"

### 3. Word Cloud / Trending Terms
- Visual dashboard of what operators are talking about
- Spot emerging problems before they become major

### 4. Operator Sentiment Analysis
- Detect frustration in comments
- Identify equipment that's causing the most operator pain

### 5. Maintenance Predictor
- Track comments mentioning specific equipment (ultrasonic, robot, grippers)
- Predict when maintenance intervention is needed based on comment patterns

### 6. Root Cause Linker
- Connect operator comments to v_losses and v_cause tables
- Build a knowledge base of what causes what

### 7. Hot Issues Alert for SHELDON
- Real-time monitoring of operator comments
- Surface trending issues to executives
- "3 operators reported gripper issues in the last hour"

---

## Other Redzone Views Worth Exploring

| View | Potential Use |
|------|---------------|
| v_changeover | Changeover time optimization |
| v_cycle, v_cycletarget | Cycle time analysis |
| v_shift, v_shiftrunsegment | Shift comparison |
| v_skill, v_userskill | Skills matrix / training gaps |
| v_learningpack, v_quizattempts | Training completion tracking |
| v_fishbone, v_cause, v_solution | Root cause tracking |
| v_meeting, v_meetingpresentuser | Tier meeting attendance |
| v_powerhour | Power hour performance |
| v_spcsample, v_completeddatasheet | Quality data |
| v_liveruncounts, v_liveshiftcounts | Real-time production |

---

## Next Steps

1. [ ] Decide which feature to prototype first
2. [ ] Build Make.com webhook for comment analysis
3. [ ] Integrate with SHELDON as new insight panel
4. [ ] Consider AI categorization of comments
5. [ ] Explore other Redzone views listed above

---

*Created: December 22, 2024*
*Related Project: SHELDON Executive Interface*
