# Day 18: solutions

---

## Spaced recall answers

1. DIFOT's trap is a multiplication error: multiplying two independently-computed
   marginals (on-time %, in-full %) understates the true joint rate because the two
   events are positively correlated. It is structurally similar to averaging a
   ratio without weighting it, both treat something that should be computed
   jointly/pooled as if its parts were independent and interchangeable.
2. `-1` means the task type does not apply to dock-to-stock measurement (only
   Receive/Putaway tasks get a real value). `FactShipmentMilestone` (Day 12)
   introduced the "wrong sentinel silently corrupts an average" pattern first, with
   its 14 milestone date columns.
3. This is a 3PL/warehousing dataset with no `COGS` measure, so `WHS.INV.TURNS`
   adopts a throughput-based convention instead: annualised units picked ÷ average
   on-hand units. A convention is needed because the standard retail-P&L turns
   formula (COGS ÷ average inventory value) has no COGS column to compute from in
   this contract.
4. Different populations (static covers all 12,000 SKUs including zero-stock ones;
   dynamic only the SKUs actually holding stock on the anchor date) and different
   bases (static's provenance is undocumented; dynamic is explicitly anchored to
   current on-hand dollar value on one date).
5. 2026-08-20, the last snapshot date with full SKU coverage; the live feed's
   daily appends after that date only touch a handful of SKUs each day, so "today"
   would silently classify almost the whole catalog as having zero value.

---

## Exercise 18.1: OTIF, both ways

```dax
OTIF % :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN Dif * Doq * Dot

[DO NOT USE] OTIF % (naive) :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN ( Dif + Doq + Dot ) / 3
```

Expect components close to **DIF ≈ 0.962, DOQ ≈ 0.987, DOT ≈ 0.913**
(`SCHEMA_CONTRACT.md` §3.4), naive headline ≈ **95.4%**, correct headline ≈
**86.7%**, an **8.7-point gap**, entirely from `+`/`3` versus `×`. This should
sit inside the contract's 0.85–0.88 validation gate.

```dax
Perfect Order Rate (Warehouse-touched) :=
CALCULATE ( AVERAGE ( FactShipment[IsPerfectOrder] ), FactShipment[WarehouseKey] <> -1 )
```

Expect this **below** the OTIF figure, around the contract's 0.84–0.89
company-wide band, but for the specific joint condition
`OnTime AND InFull AND NOT Damaged AND DocumentationClean` (four factors, one more
than OTIF's three). **A multiplicative chain of marginal pass rates, each ≤1, can
only stay the same or shrink as you multiply in another factor ≤1**, adding
`IsDocumentationClean`'s own sub-1.0 pass rate to the product can never increase
the result, only hold it flat (if that factor's pass rate were exactly 1.0, which
it isn't) or reduce it. This is a purely arithmetic consequence of multiplying
probabilities, not a fact about the specific business, it would hold for any
fourth condition added to any multiplicative KPI.

---

## Exercise 18.2: ABC, two ways, reconciled

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

**Class A's value share should sit closer to the classic ~80% Pareto expectation
under the dynamic classification**, not the static one. Day 13's own numbers
support this directly: the dynamic build put Class A at **80.0%** of value across
17.5% of stocked SKUs, almost exactly textbook Pareto, because it is freshly
computed by ranking SKUs on the exact `OnHandValueUsd` figure feeding the
denominator here, so numerator and classification basis are perfectly consistent
by construction. The static seed's basis is undocumented and may reflect an older
snapshot, a different metric (sales velocity, unit cost), or manual assignment,
whatever it reflects, it is not guaranteed to track *this period's* on-hand value,
so its Class A share can drift away from 80% simply because the classification and
the value figure it's being measured against were never built from the same
source. Confirm both numbers against your own live build rather than assuming Day
13's exact figures reproduce identically, the mechanism (freshly-derived class
tracks its own numerator; seeded class does not) is what transfers, not the precise
percentage.

---

## Exercise 18.3: the six other worked KPIs

```dax
Avg Dock-to-Stock Minutes :=
CALCULATE (
    AVERAGE ( FactWarehouseTask[DockToStockMinutes] ),
    FactWarehouseTask[TaskType] IN { "Receive", "Putaway" },
    FactWarehouseTask[DockToStockMinutes] <> -1
)

Pick Accuracy % :=
DIVIDE (
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick", FactWarehouseTask[IsAccurate] = 1 ),
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick" )
)
[DO NOT USE] Pick Accuracy % (naive) :=
AVERAGEX (
    VALUES ( FactWarehouseTask[TaskDateKey] ),
    CALCULATE ( AVERAGE ( FactWarehouseTask[IsAccurate] ), FactWarehouseTask[TaskType] = "Pick" )
)

Pallet Position Utilisation % :=
DIVIDE ( SUM ( FactInventorySnapshot[PalletPositionsUsed] ), SUM ( FactInventorySnapshot[PalletPositionsAvailable] ) )

Inventory Turns :=
VAR PeriodDays = COUNTROWS ( DATESBETWEEN ( DimDate[Date], MIN ( DimDate[Date] ), MAX ( DimDate[Date] ) ) )
VAR AnnualiseFactor = DIVIDE ( 365, PeriodDays )
VAR UnitsOutAnnualised = CALCULATE ( SUM ( FactWarehouseTask[UnitsProcessed] ), FactWarehouseTask[TaskType] = "Pick" ) * AnnualiseFactor
VAR AvgOnHand = AVERAGE ( FactInventorySnapshot[OnHandUnits] )
RETURN DIVIDE ( UnitsOutAnnualised, AvgOnHand )
[DO NOT USE] Inventory Turns (naive) :=
VAR UnitsOut = CALCULATE ( SUM ( FactWarehouseTask[UnitsProcessed] ), FactWarehouseTask[TaskType] = "Pick" )
VAR EndingOnHand = CALCULATE ( SUM ( FactInventorySnapshot[OnHandUnits] ), LASTDATE ( DimDate[Date] ) )
RETURN DIVIDE ( UnitsOut, EndingOnHand )
```

**Pick Accuracy naive/correct gap** should be modest in relative terms, both
methods are averaging a rate that stays in a tight band (99.1% baseline, dropping
to 97.4%/98.2% on specific cuts), but is not zero, because `SCHEMA_CONTRACT.md`
§3.1's weekday effect (0.35× Sunday volume, 0.7× Saturday) means low-volume days
get equal weight against high-volume weekdays in the naive daily-average version,
pulling the naive figure toward whatever accuracy those thin days happen to show,
in either direction depending on whether weekend staffing skews more toward
lower-accuracy agency/night-shift cuts.

**`Inventory Turns (naive)` reads *lower* than correct for a one-month filter**,
because the naive version has no `AnnualiseFactor` at all, it reports raw
monthly units-out over ending on-hand, which understates the *annualised* turns
rate by roughly the factor a full year would require (~12× for a calendar-month
filter, before even accounting for the ending-vs-average-snapshot distortion,
which independently pushes the naive number in whichever direction the specific
period's stock trajectory happens to run).

---

## Exercise 18.4: the ten checklist KPIs

```dax
Inventory Accuracy % :=
VAR CountedRows = FILTER ( FactInventorySnapshot, FactInventorySnapshot[PhysicalCountUnits] <> -1 )
VAR AbsVariance = SUMX ( CountedRows, ABS ( FactInventorySnapshot[SystemCountUnits] - FactInventorySnapshot[PhysicalCountUnits] ) )
VAR SystemTotal = SUMX ( CountedRows, FactInventorySnapshot[SystemCountUnits] )
RETURN 1 - DIVIDE ( AbsVariance, SystemTotal )

Avg Order Cycle Time (hrs) :=
VAR OrderSpans =
    ADDCOLUMNS (
        SUMMARIZE ( FactWarehouseTask, FactWarehouseTask[OrderNo] ),
        "SpanHours",
            DATEDIFF ( CALCULATE ( MIN ( FactWarehouseTask[TaskStartTs] ) ), CALCULATE ( MAX ( FactWarehouseTask[TaskEndTs] ) ), MINUTE ) / 60
    )
RETURN AVERAGEX ( OrderSpans, [SpanHours] )

Units per Labour Hour := DIVIDE ( SUM ( FactWarehouseTask[UnitsProcessed] ), SUM ( FactWarehouseTask[LabourHours] ) )
Labour Cost per Line := DIVIDE ( SUM ( FactWarehouseTask[LabourCostUsd] ), SUM ( FactWarehouseTask[LinesProcessed] ) )

Cube Utilisation % ( proxy ) :=
VAR StandardPalletCbm = 1.7
RETURN DIVIDE ( SUM ( FactInventorySnapshot[OnHandCbm] ), SUM ( FactInventorySnapshot[PalletPositionsAvailable] ) * StandardPalletCbm )

Perfect Order Rate (Warehouse-touched) :=
CALCULATE ( AVERAGE ( FactShipment[IsPerfectOrder] ), FactShipment[WarehouseKey] <> -1 )

Days on Hand := DIVIDE ( 365, [Inventory Turns] )

Shrinkage Rate :=
VAR CountedRows = FILTER ( FactInventorySnapshot, FactInventorySnapshot[PhysicalCountUnits] <> -1 )
RETURN DIVIDE ( SUMX ( CountedRows, FactInventorySnapshot[ShrinkageUnits] ), SUMX ( CountedRows, FactInventorySnapshot[SystemCountUnits] ) )

Obsolete Stock Ratio := DIVIDE ( SUM ( FactInventorySnapshot[ObsoleteUnits] ), SUM ( FactInventorySnapshot[OnHandUnits] ) )
Stockout Rate := AVERAGE ( FactInventorySnapshot[IsStockout] )
Rework Rate := AVERAGE ( FactWarehouseTask[IsRework] )
```

**Grouping by `WarehouseTaskKey` instead of `OrderNo` does not error**, it
silently returns a valid-looking result of **zero hours for every "order"**,
because each `WarehouseTaskKey` group now contains exactly one row, so
`MIN(TaskStartTs)` and `MAX(TaskEndTs)` are identical within every group and their
difference is always zero. `AVERAGEX` over that table then reports an average
order cycle time of 0 hours, plausible-shaped, completely wrong, and nothing in
the output flags it as broken. This is exactly the grain-checking discipline Day
13's `SUMMARIZE` warning called for: always sanity-check that the grouping column
actually produces groups with more than one row before trusting a `SUMMARIZE`-based
duration measure.

---

## Reference values used above

| Quantity | Value |
|---|---|
| OTIF components (DIF/DOQ/DOT) | ~0.962 / ~0.987 / ~0.913 |
| OTIF naive (arithmetic mean) / correct (product) | ~95.4% / ~86.7% |
| Gap from operator choice alone | 8.7 points |
| Perfect Order Rate, company-wide (README §6) | 0.8574 |
| Dynamic ABC Class A share of value / SKUs (Day 13 anchor) | 80.0% / 17.5% |
| Cube utilisation proxy assumption | StandardPalletCbm ≈ 1.7 m³ |
