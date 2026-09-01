# Day 17: Landside measures (16 KPIs)

> Time: 3.5 h · Spaced recall 10 min · Concept 15 min · Drill 160 min · Ship 30 min · Log 15 min

Trucking and rail. Fewer naive/correct pairs than Ocean, but the domain's signature
trap is different and arguably sharper: **DIFOT**, where multiplying two correct
marginal rates together gives you a plausible-looking wrong answer, because the two
events are not independent. Same family as the load-factor and moves-per-crane-hour
traps, one level more subtle.

---

## Spaced recall (10 min, closed book)

1. State the naive/correct gap mechanism for `OCN.UTL.LF.HEAD`, which denominator
   family made it larger than `Revenue per FFE`'s naive gap?
2. Why does `Avg Container Dwell Hours` require an explicit `<> -1` filter, and
   what table introduced you to that sentinel convention?
3. Name the three biggest movers inside the Jul–Sep 2025 congestion window, by
   contract-specified shock multiple.
4. What is the practical difference between `Deadhead %` (kilometre-based) and
   `Empty Repositioning Ratio` (leg-count-based)? Can one substitute for the other?
5. Restate the `[DO NOT USE]` naming convention and why naive/correct pairs live in
   the same folder, not a separate "deprecated" one.

---

## Concept

All 16 codes come from `KPI_DICTIONARY.md` §2, folder `06 Landside`, sub-foldered
by function per Day 15 (code segment decides: `CST`/`REV` → Revenue & Cost,
`SVC`/`CAR`/`SUS` → Quality & Service, `UTL`/`OPS` → Rate & Utilisation). Landside
has no `Volume & Mix` bucket: no code in §2 carries a `VOL`/`MIX`/`WT`/`INV`
segment. Every measure below reads from `FactTransportLeg` (320,000 rows, one
truck/rail movement) unless noted; `LND.CAR.SCORE` and `LND.SVC.DIFOT` also reach
into `DimCarrier` and `FactShipment` respectively.

---

## Concept: the nine KPIs worked in full

### 1. Cost per km: `LND.CST.KM`, naive/correct pair
```dax
Cost per km := DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[DistanceKm] ) )

[DO NOT USE] Cost per km (naive) :=
AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[TotalCostUsd], FactTransportLeg[DistanceKm] ) )
```
A 12 km drayage move and a 1,200 km line-haul get equal weight in the naive
version, same mechanism as `LPH Naive` from Day 9, denominator is `DistanceKm`, an
effort/duration measure. Watch-out: `TotalCostUsd` already sums
`FreightCostUsd + FuelSurchargeUsd + TollsUsd + AccessorialUsd`, never add any
component back on top when building a cost bridge.

### 2. On-Time Pickup / On-Time Delivery: `LND.SVC.OTP` / `LND.SVC.OTD`
```dax
On-Time Pickup %   := AVERAGE ( FactTransportLeg[IsOnTimePickup] )
On-Time Delivery %  := AVERAGE ( FactTransportLeg[IsOnTimeDelivery] )
```
Plain `AVERAGE` on a 0/1 flag is safe here because every row is one leg at equal
weight in the population, the same reasoning that made `On-Time Pickup %` safe as
a flat average also means it stops being safe the moment the grain changes (e.g. a
many-to-many bridge where one leg could appear twice); switch to explicit
`DIVIDE(COUNT WHERE=1, COUNT ALL)` if that ever happens. Pickup window is ±2h,
delivery ±4h, do not average the two "on-time" rates together, they measure
different tolerances.

### 3. DIFOT: `LND.SVC.DIFOT`, **the domain's signature trap**
```dax
DIFOT % :=
VAR CommercialLegs = FILTER ( FactTransportLeg, FactTransportLeg[ShipmentKey] <> -1 )
VAR DifotLegs =
    FILTER (
        CommercialLegs,
        FactTransportLeg[IsOnTimeDelivery] = 1 && RELATED ( FactShipment[IsInFull] ) = 1
    )
RETURN DIVIDE ( COUNTROWS ( DifotLegs ), COUNTROWS ( CommercialLegs ) )
```
`ShipmentKey = -1` marks empty repositioning, no commercial delivery, excluded
from the denominator by construction (same pattern as `OCN.REV.FFE`'s empty
exclusion). **The trap:** `On-Time Delivery % × In-Full %`, each computed
independently, is *not* the same number as the joint condition above, unless
on-time and in-full are statistically independent, which they usually are not (a
late leg is disproportionately also a split/partial delivery). Multiplying two
correct marginals gives you a *plausible, wrong* number. This is the mirror image
of `WHS.QLT.OTIF` (Day 18): OTIF's trap is averaging when you should multiply;
DIFOT's trap is multiplying independently-computed marginals when you should count
the joint condition directly. Same family of error, treating two correlated
events as if they were independent, appearing on two different sides of the
arithmetic.

### 4. Deadhead %: `LND.UTL.DEADHEAD`, naive/correct pair
```dax
Deadhead % := DIVIDE ( SUM ( FactTransportLeg[EmptyKm] ), SUM ( FactTransportLeg[DistanceKm] ) )

[DO NOT USE] Deadhead % (naive) :=
AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[EmptyKm], FactTransportLeg[DistanceKm] ) )
```
A 5 km empty repositioning leg (100% deadhead) and a 500 km loaded linehaul with a
20 km empty tail (4% deadhead) count equally in the naive average, the fleet-level
number ends up dominated by short legs regardless of how many empty kilometres they
actually represent.

### 5. Truck Utilisation: `LND.UTL.TRUCK`
```dax
Truck Utilisation % := DIVIDE ( SUM ( FactTransportLeg[LoadedKm] ), SUM ( FactTransportLeg[DistanceKm] ) )
```
Algebraically `= 1 − Deadhead %`, but computed independently from `LoadedKm` rather
than derived as `1 −` the other measure, a deliberate choice, per the dictionary,
so that a data-quality break (`LoadedKm + EmptyKm ≠ DistanceKm`) shows up as a
visible reconciliation gap instead of being silently hidden by the subtraction.

### 6. Carrier Composite Score: `LND.CAR.SCORE`, the domain's biggest build
```dax
VAR CarrierStats =
    ADDCOLUMNS (
        VALUES ( DimCarrier[CarrierKey] ),
        "OnTime",  CALCULATE ( AVERAGE ( FactTransportLeg[IsOnTimeDelivery] ) ),
        "FirstAtt", CALCULATE ( AVERAGE ( FactTransportLeg[IsFirstAttemptSuccess] ) ),
        "CostKm",  CALCULATE ( DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[DistanceKm] ) ) ),
        "SubRate", CALCULATE ( AVERAGE ( FactTransportLeg[IsSubcontracted] ) )
    )
VAR MinCost = MINX ( CarrierStats, [CostKm] )
VAR MaxCost = MAXX ( CarrierStats, [CostKm] )
VAR MinSub  = MINX ( CarrierStats, [SubRate] )
VAR MaxSub  = MAXX ( CarrierStats, [SubRate] )
RETURN
    ADDCOLUMNS (
        CarrierStats,
        "CompositeScore",
            0.40 * [OnTime] + 0.25 * [FirstAtt]
          + 0.20 * ( 1 - DIVIDE ( [CostKm] - MinCost, MaxCost - MinCost ) )
          + 0.15 * ( 1 - DIVIDE ( [SubRate] - MinSub, MaxSub - MinSub ) )
    )
```
Weighted 40/25/20/15 across on-time, first-attempt, cost (inverted, min-max
normalised), subcontracting discipline (inverted, min-max normalised), the
dictionary's full weighting rationale is worth reading once, not repeating here.
This is a table-valued expression, not a scalar measure: ship it as the DAX
backing a matrix visual (carrier on rows) rather than a single-value card.
Watch-out: min-max normalisation is sensitive to the carrier population in scope,
adding or removing one extreme carrier re-scales everyone else's score. Re-run the
whole ranking when the carrier panel changes; never patch one carrier's score in
isolation. The dictionary's own naive version (`AVERAGE(IsOnTimeDelivery) +
AVERAGE(IsFirstAttemptSuccess)`) is wrong on two counts, not one: it silently drops
cost and subcontracting entirely instead of weighting them, and it adds two raw
percentages with no population normalisation. Ship it as
`[DO NOT USE] Carrier Score (naive)` with both failure modes named in its
description.

### 7. CO2 per Tonne-km: `LND.SUS.CO2`, naive/correct pair, `SUMX` product trap
```dax
CO2 per Tonne-km (g) :=
VAR TotalCo2Grams = SUM ( FactTransportLeg[Co2Kg] ) * 1000
VAR TotalTonneKm = SUMX ( FactTransportLeg, ( FactTransportLeg[WeightKg] / 1000 ) * FactTransportLeg[DistanceKm] )
RETURN DIVIDE ( TotalCo2Grams, TotalTonneKm )
```
`SUMX` is required for the denominator because tonne-km is a **product of two
row-level columns**, `SUM(WeightKg) × SUM(DistanceKm)` at the total level
cross-multiplies unrelated legs' weight and distance and is wrong except by
coincidence. This is a distinct trap from the averaging family: it is not about
weighting a ratio correctly: it is about *when a total-level product is even a
valid substitute for a row-level product summed up*. The naive `AVERAGEX` version
(per-leg intensity, equally weighted) is the domain's third naive/correct pair,
ship `[DO NOT USE] CO2 per Tonne-km (naive)` alongside it.

### 8. Fuel Surcharge Recovery: `LND.REV.FSC`, cross-fact-table ratio
```dax
Fuel Surcharge Recovery :=
VAR FscRevenue =
    CALCULATE (
        SUM ( FactFreightCharge[RevenueAmount_usd] ),
        RELATED ( DimChargeType[ChargeCategory] ) = "Fuel Surcharge",
        RELATED ( DimChargeType[AppliesToMode] ) = "Road"
    )
VAR FscCost = SUM ( FactTransportLeg[FuelSurchargeUsd] )
RETURN DIVIDE ( FscRevenue, FscCost )
```
This measure spans two fact tables (`FactFreightCharge` revenue lines,
`FactTransportLeg` cost lines) with no row-level join between them, there is no
`TransportLegKey` on `FactFreightCharge`. It works because both tables share a
dimensional grain (customer × mode × period) through their common dimensions, the
same principle behind Day 13's `TREATAS` bridge, except here the bridge is an
ordinary shared relationship rather than a virtual one, because both tables *do*
relate to `DimCustomer`/`DimMode`/`DimDate` normally. Watch-out: slicing by a
`FactTransportLeg`-only attribute with no equivalent on the charge side returns
blank or a meaningless number, not an error, silent, not loud.

### 9. Detention at Site Hours: `LND.OPS.DET`
```dax
Avg Detention at Site Hours := AVERAGE ( FactTransportLeg[DetentionAtSiteHours] )
```
The landside mirror of `OCN.REV.DET`, but measured in **hours of delay**, not
**dollars of revenue**, never combine the two into one blended "detention" KPI
card; they are not the same unit and do not have the same owner.

---

## Checklist: remaining 7 Landside KPIs, same method

- [ ] `LND.CST.MOVE`, Cost per Container Move (TEU-normalised):
      `DIVIDE(SUM(TotalCostUsd), SUM(Teu))`
- [ ] `LND.OPS.TURN`, Avg Drayage Turn Time: `AVERAGE(TurnTimeMinutes)`,
      note `GateInWaitMinutes` is a *component* of this, not an alternative
- [ ] `LND.UTL.EMPTYREPO`, Empty Repositioning Ratio:
      `AVERAGE(IsEmptyRepositioning)`, related to but not substitutable for
      `Deadhead %`
- [ ] `LND.SVC.FAD`, First-Attempt Delivery Rate: `AVERAGE(IsFirstAttemptSuccess)`
- [ ] `LND.CST.ACC`, Accessorial Cost Ratio:
      `DIVIDE(SUM(AccessorialUsd), SUM(TotalCostUsd))`
- [ ] `LND.OPS.DET`, already worked above, confirm folder+description
- [ ] `LND.OPS.SUBCON`, Subcontracting Ratio: `AVERAGE(IsSubcontracted)`, also the
      `SubRate` input to `LND.CAR.SCORE`, so ship this one first if building the
      composite score from scratch

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 17.1: the nine worked KPIs (70 min)
Build all nine, including all three naive/correct pairs. Predict each naive gap's
rough size before checking, using the denominator-correlation logic from Day 9 and
Day 16, rank the three naive/correct pairs (`Cost per km`, `Deadhead %`,
`CO2 per Tonne-km`) from largest expected gap to smallest, and justify the ranking
from what each denominator measures.

### Exercise 17.2: DIFOT vs the product of marginals (25 min)
Build `DIFOT %` (joint condition) and a second measure,
`On-Time Delivery % × In-Full %` (the product of two independently-computed
`AVERAGE`s), side by side. Predict, before checking, which will be higher, the
joint measure or the product, and by roughly how many points. Explain your answer
in terms of the correlation between lateness and partial delivery, the same
reasoning structure Day 13 used for `TREATAS` region grain and Day 9 used for
averaging ratios.

### Exercise 17.3: remaining 7 KPIs (40 min)
Build the checklist. Predict, before building `Empty Repositioning Ratio`, whether
it will be higher or lower than `Deadhead %` for the same filter context, given
that one is leg-count-based and the other kilometre-based, think about what a
short, 100%-deadhead repositioning leg does to each measure differently.

### Exercise 17.4: Carrier Composite Score, re-scaled (25 min)
Build `Carrier Composite Score` (the table-valued version). Then remove the single
best-cost carrier from `DimCarrier[CarrierKey]` scope (filter it out with a slicer)
and recompute. Predict, before checking, what happens to every *other* carrier's
score, do they all move the same direction, and why does min-max normalisation
guarantee that?

---

## Ship

`06 Landside` now holds all 16 KPIs (or a logged checklist remainder), each in its
function subfolder, three naive/correct pairs marked `[DO NOT USE]`, `Carrier
Composite Score` shipped as a table-valued measure backing a matrix visual.

```
git add .
git commit -m "Day 17: Landside measure library, 16 KPIs, DIFOT joint-condition trap documented"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] All 16 Landside KPIs exist in `06 Landside`, each in its function subfolder
      per Day 15 and described with its `[KpiCode]`.
- [ ] Three naive/correct pairs shipped (`LND.CST.KM`, `LND.UTL.DEADHEAD`,
      `LND.SUS.CO2`), naive ones named `[DO NOT USE]`.
- [ ] `DIFOT %` (joint condition) and the product-of-marginals comparison exist,
      and you can state from your own numbers how far apart they land and why.
- [ ] `Carrier Composite Score` exists as a table-valued measure and you can
      explain, from your own re-scaling test, why the score is population-relative.
- [ ] Predictions recorded, misses annotated.
