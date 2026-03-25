# Sage X3 Data Dictionary

**Database:** AQFDB1\X3 / x3 / Schema: AMQ
**Last Updated:** December 26, 2024
**Purpose:** Document Sage X3 table structures for SHELDON Executive Interface

---

## Connection Details

```
Server: AQFDB1\X3
Database: x3
Schema: AMQ
Method: OAuth 2.0 → Power Automate HTTP trigger → SQL query
```

**JSON Request Format:**
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT ... FROM AMQ.TableName ..."
}
```

---

## SINVOICE - Sales Invoices (Revenue Data)

**Purpose:** Sales invoice headers - use for Revenue, AR tracking
**Record Count:** Large (historical data back to 2022+)

### Key Fields for SHELDON

| Field | Type | Description | Use Case |
|-------|------|-------------|----------|
| `NUM_0` | String | Invoice number | Unique identifier |
| `BPR_0` | String | Business partner (customer) code | Customer identification |
| `BPRNAM_0` | String | Customer name | Display |
| `ACCDAT_0` | DateTime | Accounting date | Date filtering |
| `BPRDAT_0` | DateTime | Invoice date | Revenue timing |
| `CUR_0` | String | Currency (USD) | Currency |
| `AMTATI_0` | Decimal | Amount including tax | **TOTAL INVOICE AMOUNT** |
| `AMTNOT_0` | Decimal | Amount excluding tax | Net amount |
| `CPY_0` | String | Company code (TPL, PCK, FDS) | Company filter |
| `FCY_0` | String | Facility code (TP1, PK1, FD1) | Facility filter |
| `STA_0` | Int | Status (3 = Posted) | Filter for valid invoices |
| `SIVTYP_0` | String | Invoice type (INV) | Type filter |
| `PTE_0` | String | Payment terms (NET30, NET45, etc.) | AR Days calc |
| `STRDUDDAT_0` | DateTime | Due date | AR Days calculation |

### Sample Data (5 records from Sep 2022)

| NUM_0 | BPRNAM_0 | ACCDAT_0 | AMTATI_0 | CPY_0 | PTE_0 |
|-------|----------|----------|----------|-------|-------|
| CI2204039 | RED GOLD | 2022-09-02 | $46,267.20 | TPL | NET30 |
| M2711522300584-P | UGRA | 2022-09-02 | $13,893.68 | PCK | NET10 |
| CI2204040 | LONG LIFE FOOD DEPOT | 2022-09-02 | $1,834.00 | TPL | NET30 |
| CI2204041 | UMOJA SUPPLY CHAIN LLC | 2022-09-02 | $50,544.00 | FDS | NET30 |
| CI2204042 | HAIN-CELESTIAL GROUP | 2022-09-02 | $6,372.00 | FDS | NET45 |

### Verified Revenue Data (Dec 26, 2024)

| Period | Revenue |
|--------|---------|
| December 2024 (MTD) | $38,645,611.81 |

### Company Codes

| Code | Company |
|------|---------|
| TPL | (Facility TP1) |
| PCK | (Facility PK1) |
| FDS | (Facility FD1) |

### Revenue Query Example

```sql
-- Daily Revenue (today)
SELECT SUM(AMTATI_0) as DailyRevenue
FROM AMQ.SINVOICE
WHERE ACCDAT_0 = CAST(GETDATE() AS DATE)
  AND STA_0 = 3
  AND SIVTYP_0 = 'INV'

-- Monthly Revenue
SELECT SUM(AMTATI_0) as MonthlyRevenue
FROM AMQ.SINVOICE
WHERE ACCDAT_0 >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)
  AND ACCDAT_0 < DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) + 1, 0)
  AND STA_0 = 3
  AND SIVTYP_0 = 'INV'

-- Revenue by Customer (Top 10)
SELECT TOP 10 BPR_0, BPRNAM_0, SUM(AMTATI_0) as TotalRevenue
FROM AMQ.SINVOICE
WHERE ACCDAT_0 >= DATEADD(MONTH, -1, GETDATE())
  AND STA_0 = 3
GROUP BY BPR_0, BPRNAM_0
ORDER BY TotalRevenue DESC
```

### All SINVOICE Fields (Reference)

```
UPDTICK_0, SIVTYP_0, INVTYP_0, NUM_0, ORIMOD_0, BPR_0, BPRSAC_0, CPY_0,
FCY_0, GTE_0, JOU_0, ACCDAT_0, ACCNUM_0, BPRDAT_0, BPRVCR_0, CUR_0,
CURTYP_0, LED_0-9, CURLED_0-9, RATMLT_0-9, RATDIV_0-9, RATDAT_0,
BPRPAY_0, BPAPAY_0, BPYNAM_0-1, BPYADDLIG_0-2, BPYPOSCOD_0, BPYCTY_0,
BPYSAT_0, BPYCRY_0, BPYCRYNAM_0, BPRFCT_0, FCTVCR_0, FCTVCRFLG_0,
QTCACCNUM_0, STRDUDDAT_0, PTE_0, DEP_0, DEPRAT_0, VAC_0, SSTENTCOD_0,
DIRINVFLG_0, EECNUMDEB_0, STA_0, DES_0-4, INVNUM_0, SNS_0, AMTATI_0,
AMTNOT_0, AMTNOTL_0, AMTATIL_0, VATDAT_0, NBRTAX_0, TAX_0-9,
BASTAX_0-9, AMTTAX_0-9, THEAMTTAX_0, EXEAMTTAX_0-9, DIE_0-19, CCE_0-19,
BPAINV_0, BPRNAM_0-1, BPAADDLIG_0-2, POSCOD_0, CTY_0, SAT_0, CRY_0,
CRYNAM_0, BILVCR_0, TRSFAM_0, FIY_0, PER_0, STRDATSVC_0, ENDDATSVC_0,
LASDATSVC_0, AMTTAXUSA_0-9, CAI_0, DATVLYCAI_0, WRHE_0, EXPNUM_0,
SINUM_0, STARPT_0, ISEXTDOC_0, CREDAT_0, CREUSR_0, UPDDAT_0, UPDUSR_0,
BASDEP_0, CREDATTIM_0, UPDDATTIM_0, AUUID_0, BELVCS_0, ADRVAL_0,
SALPRITYP_0, DCLEECNUM_0, POREXPDCL_0, UMRNUM_0, RCRNUM_0, RCRDAT_0,
NBRCPY_0, CSHVAT_0, FLD40REN_0, FLD41REN_0, ORIDOCNUM_0, PERDEB_0,
PERFIN_0, BVRREFNUM_0, PAYBAN_0, REVCANSTA_0, ROWID
```

---

## STOCK - Current Inventory

**Purpose:** Current stock positions by item/lot/location
**Record Count:** 2.3M+ records (live inventory)

### Key Fields for SHELDON

| Field | Type | Description | Use Case |
|-------|------|-------------|----------|
| `STOFCY_0` | String | Stock facility (FD1, PK1, TP1) | Facility filter |
| `ITMREF_0` | String | Item reference | Item identification |
| `LOT_0` | String | Lot number | Lot tracking |
| `STA_0` | String | Status (A=Available, Q=QC, QH=QC Hold) | **Status filtering** |
| `LOC_0` | String | Location code | Location |
| `LOCTYP_0` | String | Location type | Location categorization |
| `QTYPCU_0` | Decimal | Quantity in PCU | Quantity |
| `QTYSTU_0` | Decimal | Quantity in STU | **STOCK QUANTITY** |
| `PCU_0` | String | Pack unit (CS, EA) | Unit of measure |
| `PALNUM_0` | String | Pallet number | Pallet tracking |
| `LASRCPDAT_0` | DateTime | Last receipt date | Freshness |
| `CREDAT_0` | DateTime | Creation date | Age tracking |

### Stock Status Codes

| Code | Meaning | Include in Available? |
|------|---------|----------------------|
| A | Available | Yes |
| Q | Quality Control | No |
| QH | Quality Hold | No |

### Sample Data (5 records from Dec 2025)

| STOFCY_0 | ITMREF_0 | LOT_0 | STA_0 | LOC_0 | QTYSTU_0 | PCU_0 |
|----------|----------|-------|-------|-------|----------|-------|
| FD1 | 85206 | 5309 | A | 0054143 | 90 | CS |
| PK1 | 2035 | 5353 | A | X060 | 1,008 | EA |
| PK1 | 7365 | 5339 | A | K17 | 3,353 | EA |
| TP1 | 900114 | 5344TP | Q | FGTUNL | 14 | CS |
| FD1 | 39630-002 | 4305 | QH | P10076C | 5,900 | EA |

### Facility Codes

| Code | Facility |
|------|----------|
| FD1 | Foods facility |
| PK1 | Pack facility |
| TP1 | TPL facility |

### Inventory Query Examples

```sql
-- Total Available Inventory by Facility
SELECT STOFCY_0, COUNT(*) as LineCount, SUM(QTYSTU_0) as TotalQty
FROM AMQ.STOCK
WHERE STA_0 = 'A'
GROUP BY STOFCY_0

-- Inventory by Status
SELECT STA_0, COUNT(*) as LineCount, SUM(QTYSTU_0) as TotalQty
FROM AMQ.STOCK
GROUP BY STA_0

-- Inventory Value (needs join to ITMCOST for pricing)
-- See ITMCOST table below
```

### All STOCK Fields (Reference)

```
UPDTICK_0, STOFCY_0, STOCOU_0, OWNER_0, ITMREF_0, LOT_0, SLO_0,
BPSLOT_0, PALNUM_0, CTRNUM_0, STA_0, LOC_0, LOCTYP_0, LOCCAT_0,
WRH_0, SERNUM_0, RCPDAT_0, PCU_0, PCUSTUCOE_0, QTYPCU_0, QTYSTU_0,
QTYSTUACT_0, PCUORI_0, QTYPCUORI_0, QTYSTUORI_0, QLYCTLDEM_0,
CUMALLQTY_0, CUMALLQTA_0, CUMWIPQTY_0, CUMWIPQTA_0, EDTFLG_0,
LASRCPDAT_0, LASISSDAT_0, LASCUNDAT_0, CUNLOKFLG_0, CUNLISNUM_0,
EXPNUM_0, CREDAT_0, CREUSR_0, UPDDAT_0, UPDUSR_0, CREDATTIM_0,
UPDDATTIM_0, AUUID_0, XM_USER_0, ECCVALMAJ_0, STOFLD1_0, STOFLD2_0,
XM_DEFLOC_0, XM5_SERNUM1_0, XM5_PTR_0, ZSSCC_0, ZSAPUTOLOT_0,
ZSAPUTOMFGDT_0, ROWID
```

---

## ITMCOST - Item Costs (Inventory Valuation)

**Purpose:** Standard costs by item/facility/year - use for inventory valuation
**Record Count:** Large (year-based cost records per item/facility)

### Key Fields for SHELDON

| Field | Type | Description | Use Case |
|-------|------|-------------|----------|
| `ITMREF_0` | String | Item reference | Join to STOCK |
| `STOFCY_0` | String | Stock facility (FD1, PK1, TP1) | Facility filter |
| `YEA_0` | Int | Cost year (2025, 2024, etc.) | **Filter for current year** |
| `CSTTOT_0` | Decimal | Total standard cost | **UNIT COST** |
| `VLTTOT_0` | Decimal | Total value | Value calculation |
| `CSTMAT_0` | Decimal | Material cost component | Cost breakdown |
| `CSTLAB_0` | Decimal | Labor cost component | Cost breakdown |
| `CSTMAC_0` | Decimal | Machine cost component | Cost breakdown |
| `CSTSUB_0` | Decimal | Subcontract cost component | Cost breakdown |
| `CSTBDN_0` | Decimal | Burden cost component | Cost breakdown |

### Sample Data (Dec 2025)

| STOFCY_0 | ITMREF_0 | YEA_0 | CSTTOT_0 | VLTTOT_0 |
|----------|----------|-------|----------|----------|
| FD1 | 220135 | 2025 | $27.32 | - |

### Verified Inventory Valuation (Dec 26, 2024)

| Facility | Line Count | Total Qty | Total Value |
|----------|------------|-----------|-------------|
| FD1 (Foods) | 30,759 | 2.29B | $44,686,967 |
| PK1 (Pack) | 3,877 | 32.3M | $16,140,385 |
| TP1 (TPL) | 32,042 | 819.6M | $47,570,504 |
| **TOTAL** | **66,678** | - | **$108,397,856** |

### Important Notes

- **Year Filter Required:** ITMCOST has records for multiple years. Always filter `YEA_0 = 2025` for current costs.
- **Join Key:** Use `ITMREF_0` + `STOFCY_0` to join with STOCK table for inventory valuation.

### Inventory Valuation Query

```sql
-- Total Inventory Value by Facility (Available Stock Only)
SELECT
    s.STOFCY_0,
    COUNT(*) as LineCount,
    SUM(s.QTYSTU_0) as TotalQty,
    SUM(s.QTYSTU_0 * c.CSTTOT_0) as TotalValue
FROM AMQ.STOCK s
INNER JOIN AMQ.ITMCOST c
    ON s.ITMREF_0 = c.ITMREF_0
    AND s.STOFCY_0 = c.STOFCY_0
WHERE s.STA_0 = 'A'
    AND c.YEA_0 = 2025
GROUP BY s.STOFCY_0
```

### JSON Query Template

```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT s.STOFCY_0, COUNT(*) as LineCount, SUM(s.QTYSTU_0) as TotalQty, SUM(s.QTYSTU_0 * c.CSTTOT_0) as TotalValue FROM AMQ.STOCK s INNER JOIN AMQ.ITMCOST c ON s.ITMREF_0 = c.ITMREF_0 AND s.STOFCY_0 = c.STOFCY_0 WHERE s.STA_0 = 'A' AND c.YEA_0 = 2025 GROUP BY s.STOFCY_0"
}
```

---

## Related Tables (To Explore)

### For Inventory Details
- `ITMMASTER` - Item master (descriptions, categories)

### For Financial KPIs
- `GACCOUNT` - General ledger accounts
- `GACCENTRY` - GL entries (for margin calculations)
- `BALANCE` - Balance sheet data
- `GJOURNAL` - Journal entries

### For AR Days
- `GACCDUDATE` - Account due dates
- `BPCUSTOMER` - Customer master

---

## Query Templates for SHELDON

### Daily Revenue
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT SUM(AMTATI_0) as DailyRevenue FROM AMQ.SINVOICE WHERE CAST(ACCDAT_0 AS DATE) = CAST(GETDATE() AS DATE) AND STA_0 = 3 AND SIVTYP_0 = 'INV'"
}
```

### Available Inventory Count
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT STOFCY_0, COUNT(*) as Lines, SUM(QTYSTU_0) as TotalQty FROM AMQ.STOCK WHERE STA_0 = 'A' GROUP BY STOFCY_0"
}
```

### December 2024 Revenue (Test Query)
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT SUM(AMTATI_0) as DecemberRevenue FROM AMQ.SINVOICE WHERE ACCDAT_0 >= '2024-12-01' AND ACCDAT_0 < '2025-01-01' AND STA_0 = 3 AND SIVTYP_0 = 'INV'"
}
```

### Inventory Valuation by Facility
```json
{
  "server": "AQFDB1\\X3",
  "database": "x3",
  "sqlQuery": "SELECT s.STOFCY_0, COUNT(*) as LineCount, SUM(s.QTYSTU_0) as TotalQty, SUM(s.QTYSTU_0 * c.CSTTOT_0) as TotalValue FROM AMQ.STOCK s INNER JOIN AMQ.ITMCOST c ON s.ITMREF_0 = c.ITMREF_0 AND s.STOFCY_0 = c.STOFCY_0 WHERE s.STA_0 = 'A' AND c.YEA_0 = 2025 GROUP BY s.STOFCY_0"
}
```

---

## Next Tables to Explore

1. **ITMMASTER** - Get item descriptions and categories
2. **GACCOUNT** - Chart of accounts for financial rollups
3. **BALANCE** - Balance sheet for cash position
4. **BPCUSTOMER** - Customer master for AR analysis

---

*Document created: December 26, 2024*
*Source: Live Sage X3 database queries via Power Automate*
