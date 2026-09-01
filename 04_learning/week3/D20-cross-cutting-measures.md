# Day 20: Cross-cutting / executive measures (7 KPIs)

> Time: 3.25 h · Spaced recall 10 min · Concept 35 min · Drill 130 min · Ship 30 min · Log 15 min

Seven KPIs, and every one of them either spans more than one fact table or reaches
across the whole book rather than one domain. This is where the pattern library you
built across Weeks 2–3 stops being domain-specific tooling and becomes the thing
that makes an executive scorecard possible at all, nothing here is a new
mechanism, everything here is Day 12's point-in-time pattern or Day 13's `TREATAS`,
applied at a wider scope than any single domain needed.

---

## Spaced recall (10 min, closed book)

1. Restate the chargeable-weight rating error from Day 19, what does
   `MAX(GrossWeightKg, VolumeCbm)` actually return for a real air shipment, and
   why, dimensionally?
2. State Day 13's `TREATAS` direction rule: which argument supplies values, which
   gets filtered, and what happens if you get it backwards?
3. Restate Day 12's `LASTNONBLANK` point-in-time pattern in one sentence.
4. Why does `DimCustomer` require ranking by `CustomerCode` rather than
   `CustomerKey` for any concentration or top-N measure (Day 13)?
5. What did Day 14's `FYTD` vs plain `TOTALYTD` comparison find, in dollars and in
   percentage terms?

---

## Concept

All 7 codes from `KPI_DICTIONARY.md` §5, folder `09 Cross-Cutting`, sub-foldered by
function per Day 15 (`QLT`→ Quality & Service, `FIN`→ Revenue & Cost, `CUS`→ Volume
& Mix). `XCT.SCOR.MAP` is the one exception - see below, it isn't a measure and
doesn't get foldered at all.

### SCOR Level-1 Attribute Map, `XCT.SCOR.MAP`, a classification, not a ratio

Not a computed measure, a fixed mapping table joining every KPI code to one of
SCOR's five Level-1 attributes (Reliability, Responsiveness, Agility, Cost, Asset
Management), so a scorecard can be organised the way a supply-chain executive
expects rather than by data domain. This is the one KPI this week that is
*consumed* by `TREATAS`, not built with a `CALCULATE` filter modifier, proof that
Day 13's virtual-relationship mechanism generalises beyond the specific
`FactTarget`/`DimLocation` bridge it was introduced for:

```dax
DEFINE
    TABLE SCORMap =
        DATATABLE (
            "KpiCode", STRING, "ScorAttribute", STRING,
            {
                { "OCN.REL.SCHED", "Reliability" }, { "LND.SVC.DIFOT", "Reliability" },
                { "WHS.QLT.OTIF", "Reliability" },  { "OCN.TRN.P90", "Responsiveness" },
                { "WHS.OPS.D2S", "Responsiveness" },{ "LND.OPS.SUBCON", "Agility" },
                { "LND.CST.KM", "Cost" },           { "OCN.UTL.LF.HEAD", "Asset Management" }
                -- full table carries all 72 codes; the mapping lives in
                -- KPI_DICTIONARY.md §5 XCT.SCOR.MAP, not reproduced here
            }
        )

Target Attainment % by SCOR Attribute :=
VAR TargetsInAttribute =
    TREATAS ( FILTER ( SCORMap, SCORMap[ScorAttribute] = SELECTEDVALUE ( SCORMap[ScorAttribute] ) )[KpiCode], FactTarget[KpiCode] )
RETURN
    CALCULATE (
        DIVIDE ( SUM ( FactTarget[TargetValue] ), SUM ( FactTarget[StretchValue] ) ),
        TargetsInAttribute
    )
```
Watch-out: SCOR mappings are house convention, not a universal standard,
document the choice once here and do not let analysts re-classify ad hoc on
different dashboards. Commercial/profitability KPIs sit deliberately *outside* the
five SCOR attributes; forcing revenue-per-FFE into "Asset Management" would
misrepresent both the KPI and the framework.

### Cash-to-Cash Cycle Time, `XCT.FIN.C2C`, Day 12's pattern, reused at a wider scope

```dax
Days Inventory Outstanding (proxy) := [Days on Hand]   -- = WHS.INV.DOH, Day 18

Days Sales Outstanding (contractual-terms proxy) :=
DIVIDE (
    SUMX ( FactShipment, FactShipment[Revenue_usd] * RELATED ( DimCustomer[PaymentTermsDays] ) ),
    SUM ( FactShipment[Revenue_usd] )
)

-- Days Payable Outstanding: NOT COMPUTABLE under this contract, no vendor
-- payment-terms field, no accounts-payable fact. No DAX is provided; do not
-- substitute an invented column (KPI_DICTIONARY.md §7 Gaps #1).

Cash-to-Cash Cycle Time (partial) :=
[Days Inventory Outstanding (proxy)] + [Days Sales Outstanding (contractual-terms proxy)]
```
`Days on Hand` is literally `[WHS.INV.DOH]`, itself built on `Inventory Turns`,
itself built on Day 18's average-on-hand logic, which is itself the same
semi-additive-aggregation discipline Day 12 introduced for `On Hand Value (as of)`.
This measure does not reuse Day 12's *code*, it reuses Day 12's *reasoning*:
`FactInventorySnapshot` cannot be summed across dates, only averaged or read
point-in-time, and every downstream measure built on top of it (turns, DOH, now
C2C) inherits that constraint whether or not its own DAX mentions
`FactInventorySnapshot` directly. Watch-out, twice over: this is explicitly a
**partial** figure (DIO + DSO only, DPO unavailable), never let it be relabelled
"the cash-to-cash cycle" without that caveat, since dropping DPO always makes the
number look *worse* (longer) than the true cycle would; and DSO here is a
*contractual-terms* proxy, not actual collection speed, there is no
cash-receipt date anywhere in this contract to build the real thing.

### Perfect Order Rate, company-wide, `XCT.QLT.PERFECT`

```dax
Perfect Order Rate (Company-wide) := AVERAGE ( FactShipment[IsPerfectOrder] )
```
The enterprise superset of Day 18's `Perfect Order Rate (Warehouse-touched)`, same
four-condition joint AND, no `WarehouseKey` filter. Validation gate 0.84–0.89
(`README` §6: **0.8574**). The two numbers will differ whenever warehouse-touched
shipments carry a different risk profile than the book as a whole, always label
which population a Perfect Order figure represents.

### Revenue Concentration, `XCT.CUS.CONC`, naive/correct pair, SCD2 caution

```dax
[DO NOT USE] Top-10 Customer Share (naive) :=
VAR Top10Static = { "CUS0001", "CUS0002", "CUS0003", "CUS0004", "CUS0005", "CUS0006", "CUS0007", "CUS0008", "CUS0009", "CUS0010" }
RETURN
    DIVIDE (
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), DimCustomer[CustomerCode] IN Top10Static ),
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), ALL ( DimCustomer ) )
    )

Top-10 Customer Share :=
VAR CustomerRevenue =
    ADDCOLUMNS ( VALUES ( DimCustomer[CustomerCode] ), "CustRev", CALCULATE ( SUM ( FactShipment[Revenue_usd] ) ) )
VAR Top10Revenue = SUMX ( TOPN ( 10, CustomerRevenue, [CustRev], DESC ), [CustRev] )
VAR TotalRevenue = SUMX ( CustomerRevenue, [CustRev] )
RETURN DIVIDE ( Top10Revenue, TotalRevenue )
```
The naive version hardcodes a customer list computed once, as the book changes,
this silently stops being "the top 10" and becomes "ten specific accounts," with no
error raised. The correct version ranks by **`CustomerCode`** (the durable business
key), not `CustomerKey`, `DimCustomer` is SCD2 (Day 13, Day 8 territory: 4,180 rows
for 3,200 current members), so ranking by the surrogate key can split one
customer's revenue across several `CustomerKey` versions, understating true
concentration by pretending one large customer is several smaller ones. `README`
§6 states this at **27.8%** for the current build, well inside the "diversified
book" band (<30–40%).

### Freight Cost % of Revenue, `XCT.FIN.FCR`

```dax
Freight Cost % of Revenue := DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[Revenue_usd] ) )
```
Complements the gross-margin validation gate (14–22% mean margin), should sit
roughly 78–86% given `Freight Cost % + Gross Margin % ≈ 100%` before other P&L
lines. Watch-out: `DirectCost_usd` excludes SG&A and overhead; this is not full
operating-cost coverage.

### Cost to Serve per Customer, `XCT.FIN.CTS`

```dax
Cost to Serve per Customer :=
DIVIDE (
    CALCULATE ( SUM ( FactFreightCharge[CostAmount_usd] ), FactFreightCharge[IsCost] = 1 ),
    DISTINCTCOUNT ( FactFreightCharge[CustomerKey] )
)
```
Numerator additive across customers/time; the per-customer average is non-additive
and must be recomputed, never averaged, when the customer population changes, the
same population-sensitivity Day 17's `Carrier Composite Score` exercise proved
directly for min-max normalisation, here showing up in a plain `DIVIDE` instead.
Watch-out: ranking customers by this measure alone rewards serving *fewer*
customers cheaply, which is not the same as serving each one efficiently, always
pair with revenue or margin per customer.

### Margin Dispersion, `XCT.FIN.MARGDISP`

```dax
Gross Margin % Std Dev := STDEVX.P ( FactShipment, FactShipment[GrossMarginPct] )
Gross Margin % P10–P90 Spread :=
VAR P90 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.9 )
VAR P10 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.1 )
RETURN P90 - P10
```
Validation gate: mean gross margin 14–22%, with a documented left tail below zero.
Ship both together, a flat or improving mean alongside a *widening* P10–P90
spread is a genuine warning sign (more shipments losing money even as the average
holds), invisible if you only ever chart the mean.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 20.1: Cash-to-Cash, built and labelled (30 min)
Build all three C2C components (DIO proxy, DSO proxy, the partial sum) plus a
visible label/description stating "partial: DIO+DSO only, DPO not computable." Then
try to build a naive full-looking `Cash-to-Cash Cycle Time := [DIO] + [DSO] -
0` (subtracting a hardcoded zero to "stand in" for DPO). Predict, before comparing
the two versions side by side in a report, which one a stakeholder reading quickly
is more likely to mistake for a complete figure, and write the one-sentence rule
you'd give a teammate about ever hardcoding a zero for a genuinely missing
component.

### Exercise 20.2: Top-10 concentration, both ways (30 min)
Build both `Top-10 Customer Share` variants. Predict, before checking, whether the
naive static-list version will read *higher* or *lower* than the correct dynamic
version for the current period, think about what happens to a hardcoded list as
new large customers grow into the top 10 that weren't there when the list was
written. Then rank by `CustomerKey` instead of `CustomerCode` in a third variant
and confirm it produces a smaller (or at least different) top-10 revenue figure
than ranking by `CustomerCode`, demonstrating the SCD2 split directly.

### Exercise 20.3: the SCOR map, applied (25 min)
Build the `SCORMap` table (at minimum the 8-row illustrative version) and
`Target Attainment % by SCOR Attribute`. Put `ScorAttribute` on rows. Predict,
before checking, which attribute will show the most measures once you extend the
mapping, Reliability or Asset Management, by counting codes in
`KPI_DICTIONARY.md`'s full SCOR table.

### Exercise 20.4: Margin Dispersion, the trap it's designed to catch (25 min)
Build both margin-dispersion measures. Filter to two different periods you expect
to differ (e.g., a congestion-window period vs a calm one). Predict, before
checking, whether the *mean* gross margin moves much between the two periods, and
separately whether the *P10–P90 spread* moves much, can you construct a filter
context where the mean barely moves but the spread widens noticeably? That
combination is exactly the warning sign the KPI exists to catch.

---

## Ship

`09 Cross-Cutting` now holds all 7 KPIs, each in its function subfolder.
`Cash-to-Cash Cycle Time (partial)` and
its two components clearly labelled as partial/proxy. Both `Top-10 Customer Share`
variants shipped, naive one marked `[DO NOT USE]`. `SCORMap` exists (illustrative
subset acceptable, full 72-row table logged as a follow-up if not completed today).

```
git add .
git commit -m "Day 20: Cross-cutting measure library, 7 KPIs, cash-to-cash gaps and SCOR map shipped"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] All 7 Cross-Cutting KPIs exist in `09 Cross-Cutting`, each in its function
      subfolder per Day 15 (except `XCT.SCOR.MAP`, unfoldered by design), described
      with its `[KpiCode]`.
- [ ] `Cash-to-Cash Cycle Time (partial)` is unambiguously labelled partial, and you
      can state from memory which component is not computable and why.
- [ ] Both `Top-10 Customer Share` variants exist, and you can state why ranking by
      `CustomerCode` instead of `CustomerKey` matters, with the SCD2 mechanism
      named specifically.
- [ ] `SCORMap` exists and `Target Attainment % by SCOR Attribute` returns
      different numbers for at least two attributes.
- [ ] Predictions recorded, misses annotated.
