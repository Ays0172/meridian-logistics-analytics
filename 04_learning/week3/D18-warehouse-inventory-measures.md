# Day 18: Warehouse & inventory measures (18 KPIs)

> Time: 3.75 h · Spaced recall 10 min · Concept 20 min · Drill 190 min · Ship 30 min · Log 15 min

Eighteen KPIs, and two of them are the reason this day gets extra time: `WHS.QLT.OTIF`
is the single most-cited "arithmetic operator matters" example in the whole
dictionary, and `WHS.INV.ABC` is the day Day 13's dynamic ABC calculated column
stops being a Week 2 exercise and becomes a shipped measure. Both deserve full
attention, not a checklist entry.

---

## Spaced recall (10 min, closed book)

1. State DIFOT's trap from Day 17 in one sentence, is it an averaging error or a
   multiplication error, and what does that make it structurally similar to?
2. What does `-1` mean in `FactWarehouseTask[DockToStockMinutes]`, and what table
   introduced the "wrong sentinel silently corrupts an average" pattern first?
3. What is `WHS.INV.TURNS`'s throughput-based convention, and why does this dataset
   need a convention at all instead of a standard COGS-based turns formula?
4. Restate the two structural reasons `SkuAbcClassDynamic` (Day 13) disagreed with
   `DimSku[AbcClassStatic]`, different populations, and different what?
5. What anchor date did Day 13 use for dynamic ABC, and why not "today"?

---

## Concept: the OTIF decomposition, and why it belongs next to Day 9

`00_docs/KPI_DICTIONARY.md`'s `WHS.QLT.OTIF` entry is the cleanest single
demonstration in this whole project of Day 9's percentage-scope lesson taken one
step further. Day 9 taught you that "never average an average" depends on
*correlation between a ratio and its denominator*. OTIF's trap is adjacent but
distinct: it's not about averaging a ratio across a denominator, it's about which
**arithmetic operator** combines three already-correct ratios.

```dax
-- NAÏVE, arithmetic mean instead of product
OTIF % (naive) :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN ( Dif + Doq + Dot ) / 3

-- CORRECT, multiplicative decomposition
OTIF % :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )                     -- ~0.962
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )   -- ~0.987
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )                      -- ~0.913
RETURN Dif * Doq * Dot                                             -- ~0.867
```

Three components that each individually look healthy (96%, 99%, 91%) arithmetic-mean
to ~95.4%, a great-looking number, but the correct multiplicative headline is
~86.7%, an **8.7-point gap entirely from the choice of `+` versus `×`.** OTIF is a
**joint requirement**: a shipment either satisfies all three conditions or it does
not satisfy OTIF at all, so the correct combination is the product of independent
marginal pass rates (per `SCHEMA_CONTRACT.md` §3.4, DIF/DOQ/DOT are generated
independently for this KPI, unlike DIFOT's positively-correlated pair from Day 17,
worth noticing the two KPIs solve structurally similar-looking problems with
different correct answers because the underlying correlation assumption differs).
The compounding effect gets *worse*, not better, as more factors are added, which
is exactly why the four-factor `WHS.QLT.PERFECT` (Perfect Order Rate,
warehouse-touched) is always lower than three-factor OTIF for the same population.
A stakeholder who has only ever seen the arithmetic-mean version will find the
correct 86.7% "suspiciously low", have the worked numbers above ready when that
happens; `README` §6 states the enterprise figure as **0.9130 for delivery OTIF**
in a different framing (on-time only) and **0.8574 for perfect order rate**, both
worth having memorised alongside this one.

## Concept: WHS.INV.ABC reuses Day 13's calculated column directly

`WHS.INV.ABC`'s dictionary-stated formula is `Σ OnHandValueUsd [AbcClassStatic = c]
÷ Σ OnHandValueUsd [all]`, a *measure* that reads a class already sitting on
`DimSku`. You built exactly that class as a **calculated column**,
`SkuAbcClassDynamic`, on Day 13, anchored to the 2026-08-20 snapshot. Today's job is
not to rebuild ABC segmentation: it is to ship **two** versions of the KPI's value-
share measure side by side: one reading the seeded `AbcClassStatic`, one reading
your Day 13 `SkuAbcClassDynamic`, both against the same `OnHandValueUsd` numerator,
so a reader can see both classifications' value concentration without needing to
know DAX to compare them.

```dax
Value Share by ABC Class (Static) :=
DIVIDE (
    SUM ( FactInventorySnapshot[OnHandValueUsd] ),
    CALCULATE ( SUM ( FactInventorySnapshot[OnHandValueUsd] ), ALL ( DimSku[AbcClassStatic] ) )
)

Value Share by ABC Class (Dynamic) :=
DIVIDE (
    SUM ( FactInventorySnapshot[OnHandValueUsd] ),
    CALCULATE ( SUM ( FactInventorySnapshot[OnHandValueUsd] ), ALL ( DimSku[SkuAbcClassDynamic] ) )
)
```

Both are non-additive distributions, the three class shares sum to 100% within
whichever classification is on rows, but that total is not itself meaningful across
the two classifications combined. Day 13 already found the two structural reasons
they disagree (different populations, static covers all 12,000 SKUs including
zero-stock ones, dynamic only the 1,537 with stock on the anchor date; different
bases, static's provenance is undocumented, dynamic is explicitly current-value on
one date). Ship both, and describe each with which basis it uses, so nobody
compares them as if they were the same question asked twice.

## Concept: the rest, briefly

Six more full builds below; the remaining ten are a checklist. All folder
`07 Warehouse & Inventory`, sub-foldered by function per Day 15 (`OPS`/`UTL`/`PRD`
→ Rate & Utilisation, `INV`→ Volume & Mix, `QLT`→ Quality & Service, `CST`→ Revenue
& Cost).

**Dock-to-Stock Minutes, `WHS.OPS.D2S`** (reuses Day 12's sentinel discipline):
```dax
Avg Dock-to-Stock Minutes :=
CALCULATE (
    AVERAGE ( FactWarehouseTask[DockToStockMinutes] ),
    FactWarehouseTask[TaskType] IN { "Receive", "Putaway" },
    FactWarehouseTask[DockToStockMinutes] <> -1
)
```

**Pick Accuracy, `WHS.QLT.PICKACC`**, naive/correct pair, day-average trap:
```dax
Pick Accuracy % :=
DIVIDE (
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick", FactWarehouseTask[IsAccurate] = 1 ),
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick" )
)
```
The naive version averages one daily accuracy % per day with equal weight, a slow
Sunday with 40 picks and a peak Wednesday with 4,000 picks count the same. Ship
`[DO NOT USE] Pick Accuracy % (naive)` alongside; contract baseline is 99.1%
overall, 97.4% night shift, 98.2% agency staff in their first six months, those
cuts *always* look worse by design, not a data bug.

**Pallet Position Utilisation, `WHS.UTL.PALLET`** (semi-additive, Day 12 pattern):
```dax
Pallet Position Utilisation % :=
DIVIDE ( SUM ( FactInventorySnapshot[PalletPositionsUsed] ), SUM ( FactInventorySnapshot[PalletPositionsAvailable] ) )
```
Summed across a date range this stays a valid ratio (numerator and denominator both
accumulate proportionally), but if the report needs "average daily occupancy,"
switch explicitly to `AVERAGEX` over `VALUES(DimDate[Date])`, and never mix the two
forms in the same report without labelling which is which.

**Inventory Turns, `WHS.INV.TURNS`**, naive/correct pair, annualisation trap:
```dax
Inventory Turns :=
VAR PeriodDays = COUNTROWS ( DATESBETWEEN ( DimDate[Date], MIN ( DimDate[Date] ), MAX ( DimDate[Date] ) ) )
VAR AnnualiseFactor = DIVIDE ( 365, PeriodDays )
VAR UnitsOutAnnualised =
    CALCULATE ( SUM ( FactWarehouseTask[UnitsProcessed] ), FactWarehouseTask[TaskType] = "Pick" ) * AnnualiseFactor
VAR AvgOnHand = AVERAGE ( FactInventorySnapshot[OnHandUnits] )
RETURN DIVIDE ( UnitsOutAnnualised, AvgOnHand )
```
Naive version fails two ways at once: not annualised (a one-month and one-year view
give wildly different "turns"), and uses a single ending snapshot instead of an
average (a pre-period-end stock build makes the warehouse look artificially
inefficient). Ship `[DO NOT USE] Inventory Turns (naive)`.

---

## Checklist: remaining 10 Warehouse & Inventory KPIs, same method

- [ ] `WHS.QLT.INVACC`, Inventory Accuracy % (uses `PhysicalCountUnits <> -1`
      filter, a third instance of the sentinel-filtering pattern this week)
- [ ] `WHS.OPS.OCT`, Avg Order Cycle Time, via `SUMMARIZE(FactWarehouseTask,
      [OrderNo])` + `DATEDIFF`, sanity-check the grain per Day 13's `SUMMARIZE`
      warning before trusting the output
- [ ] `WHS.PRD.UPH`, Units per Labour Hour: `DIVIDE(SUM(UnitsProcessed),
      SUM(LabourHours))`
- [ ] `WHS.CST.LCPL`, Labour Cost per Line: `DIVIDE(SUM(LabourCostUsd),
      SUM(LinesProcessed))`
- [ ] `WHS.UTL.CUBE`, Cube Utilisation % (proxy, documented `StandardPalletCbm ≈
      1.7 m³` assumption, see `KPI_DICTIONARY.md` §7 Gaps #5)
- [ ] `WHS.QLT.PERFECT`, Perfect Order Rate (warehouse-touched):
      `CALCULATE(AVERAGE(IsPerfectOrder), WarehouseKey <> -1)`, a superset of
      OTIF, never quote the two interchangeably
- [ ] `WHS.INV.DOH`, Days on Hand: `DIVIDE(365, [Inventory Turns])`, never
      `AVERAGE(DaysOfSupply)` as a shortcut: that's the averaging-a-ratio trap
      again, hidden behind a column that looks pre-aggregated
- [ ] `WHS.QLT.SHRINK`, Shrinkage Rate (cycle-count rows only, `PhysicalCountUnits
      <> -1`, consistent with Inventory Accuracy)
- [ ] `WHS.INV.OBS`, Obsolete Stock Ratio: `DIVIDE(SUM(ObsoleteUnits),
      SUM(OnHandUnits))`
- [ ] `WHS.QLT.STOCKOUT` / `WHS.QLT.REWORK`, `AVERAGE(IsStockout)` /
      `AVERAGE(IsRework)`, two simple flag-averages to close out the domain

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 18.1: OTIF, both ways (30 min)
Build `OTIF %` and `[DO NOT USE] OTIF % (naive)`. Predict each component (DIF, DOQ,
DOT) and both combined headlines before checking against the contract's stated
~0.962/0.987/0.913 → ~0.867. Then build `Perfect Order Rate (Warehouse-touched)`
and confirm it sits *below* your OTIF number, explain in one sentence why adding a
fourth independent-ish condition to a multiplicative chain can only ever lower the
result, never raise it.

### Exercise 18.2: ABC, two ways, reconciled (25 min)
Build both `Value Share by ABC Class` measures. Put `AbcClassStatic` and
`SkuAbcClassDynamic` each on rows in separate matrix visuals, both showing value
share. Predict, before checking, whether Class A's value share will be *closer* to
the classic 80% Pareto expectation under the static or the dynamic classification,
and justify from what Day 13 already found about each classification's population
and basis.

### Exercise 18.3: the six other worked KPIs (60 min)
Build `Avg Dock-to-Stock Minutes`, both `Pick Accuracy %` variants, `Pallet
Position Utilisation %`, and both `Inventory Turns` variants. Predict the Pick
Accuracy naive/correct gap's rough size before checking, using the same
day-of-week seasonality reasoning as `SCHEMA_CONTRACT.md` §3.1's weekday effect
(0.35× Sunday volume, 0.7× Saturday). For `Inventory Turns`, predict whether the
naive version will read *higher* or *lower* than correct for a report filtered to
exactly one calendar month, and justify from the missing annualisation factor
alone (ignore the ending-vs-average-snapshot issue for this prediction).

### Exercise 18.4: the ten checklist KPIs (55 min)
Build the remaining ten. For `WHS.OPS.OCT`, predict what happens if you accidentally
group by `WarehouseTaskKey` instead of `OrderNo` inside the `SUMMARIZE`, will the
result error, or silently return a value, and if so what value? Verify against your
own build.

---

## Ship

`07 Warehouse & Inventory` now holds all 18 KPIs (or logged remainder), each in its
function subfolder. Both ABC value-share measures shipped, each described with
which classification basis it uses. Both `OTIF` variants and both `Inventory
Turns` variants shipped, naive ones marked `[DO NOT USE]`.

```
git add .
git commit -m "Day 18: Warehouse & inventory measure library, 18 KPIs, OTIF decomposition and dynamic ABC shipped"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] All 18 Warehouse & Inventory KPIs exist in `07 Warehouse & Inventory`, each
      in its function subfolder per Day 15 and described with its `[KpiCode]`.
- [ ] `OTIF %` and its naive twin both exist, and you can state the DIF/DOQ/DOT
      components and both headlines from memory.
- [ ] Both ABC value-share measures exist, each clearly labelled with its
      classification basis, and you can state which one your build's Class A sits
      closer to the classic 80% Pareto line under.
- [ ] `Perfect Order Rate (Warehouse-touched)` is confirmed lower than `OTIF %` for
      the same population, and you can explain why in one sentence.
- [ ] Predictions recorded, misses annotated.
