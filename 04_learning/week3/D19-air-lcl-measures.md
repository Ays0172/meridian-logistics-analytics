# Day 19: Air & LCL measures (9 KPIs)

> Time: 3 h · Spaced recall 10 min · Concept 30 min · Drill 130 min · Ship 30 min · Log 15 min

The smallest domain, and the one with the sharpest single trap: three different
"chargeable weight" conventions that use superficially similar arithmetic (divide a
volume by a number, compare it to actual weight) but encode genuinely different
densities. Confusing them is a real, expensive rating error in this industry, not
just a curriculum exercise, get comfortable stating why both 6000 and 5000 exist
before you touch the DAX.

---

## Spaced recall (10 min, closed book)

1. State OTIF's naive/correct gap and which arithmetic operator was the actual bug.
2. Why does `Value Share by ABC Class (Dynamic)` land closer to the classic 80%
   Pareto line than the static version, structurally, not just numerically?
3. What is the sentinel-filter pattern, and name three tables/measures this week
   that needed it (Ocean, Warehouse ×2).
4. Restate the `SUMX` product trap from `CO2 per Tonne-km`, why is
   `SUM(WeightKg) × SUM(DistanceKm)` wrong at the total level?
5. What does `IsHigherBetter` on `FactTarget` let you do that a flat target value
   alone can't (think ahead to Day 20/21, you have not built anything with it yet,
   reason from the column name)?

---

## Concept: why two air divisors exist, and why one ocean rule doesn't match either

Air cargo billing weight is `MAX(GrossWeightKg, VolumetricWeight)`, where
volumetric weight comes from dividing volume by a **density divisor**:

```
Volumetric Weight (kg) = Volume_cbm × 1,000,000 ÷ divisor
```

**IATA's standard divisor is 6,000** (cm³ per kg), the number most air waybills
use. **Some carriers, and historically some express/parcel networks, use 5,000
instead.** Because `5,000 < 6,000`, the *same* cubic volume produces a **higher**
volumetric weight under the 5,000 rule, dividing by a smaller number gives a
bigger result. In plain terms: **1:5000 charges bulky, low-density cargo more than
1:6000 does**, for the identical physical shipment. Which rule applies is
carrier- and trade-lane-specific, never assumed, always looked up per shipment via
`DimMode.ChargeableWeightRule`.

**Ocean LCL uses a completely different convention**, not a third divisor on the
same 1:N scale, but a flat **1,000 kg per cubic metre** weight-or-measure (W/M)
equivalence:

```
Revenue Tons (RT) = MAX ( WeightKg ÷ 1000, VolumeCbm )
```

This is not "ocean's divisor happens to be 1000 instead of 6000": it is a
structurally different rule (a direct tonne-for-cbm swap, no divide-by-thousands
volumetric-weight step at all). The three rules superficially resemble each other
("a number you divide volume by") and that resemblance is exactly what makes
confusing them a classic, expensive rating-desk error: applying ocean's 1:1000
logic to an air shipment, or air's divide-by-6000 logic to an ocean LCL shipment,
misprices by a factor of five to six, not by a rounding amount.

```dax
Chargeable Weight kg (Air 1:6000) :=
CALCULATE ( SUM ( FactShipment[ChargeableWeightKg] ), RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:6000" )

Chargeable Weight kg (Air 1:5000) :=
CALCULATE ( SUM ( FactShipment[ChargeableWeightKg] ), RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:5000" )

Revenue Tons (LCL) :=
CALCULATE ( SUM ( FactShipment[RevenueTons] ), DimMode[ModeCode] = "LCL" )
```

All three read the **already-resolved** `ChargeableWeightKg`/`RevenueTons` columns
rather than recomputing `MAX(...)` from raw dimensions, the contract carries only
aggregate `VolumeCbm`/`GrossWeightKg`, no per-piece dimensions, so the resolution
already happened upstream in the generator. All three are additive **within their
own rule population**, never sum `ChargeableWeightKg` across shipments mixing
1:6000, 1:5000, and 1:1000 without segmenting first; the column name is identical
across all three but the unit it represents is not.

## Concept: Yield per kg, naive/correct pair

```dax
Yield per kg :=
CALCULATE (
    DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ),
    DimMode[ModeGroup] = "Air"
)

[DO NOT USE] Yield per kg (naive) :=
CALCULATE (
    AVERAGEX ( FactShipment, DIVIDE ( FactShipment[Revenue_usd], FactShipment[ChargeableWeightKg] ) ),
    DimMode[ModeGroup] = "Air"
)
```

Same family as `OCN.REV.FFE`'s trap, one domain over, a 40 kg document courier
shipment and a 12,000 kg charter consolidation contribute equally to the naive
"average yield," so a book with many small shipments and a few large ones gets a
headline dominated by the small-shipment count rather than revenue-weighted
reality. Watch-out: comparing yield across shipments mixing the 1:6000 and 1:5000
rules without segmenting mixes two different denominators' economics into one
number, the same discipline as never mixing chargeable-weight rule populations
above, now applied to a ratio built on top of them.

## Concept: the rest, worked

```dax
Gross Profit per House Bill :=
DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), DISTINCTCOUNT ( FactShipment[HouseBlNo] ) )
```
`DISTINCTCOUNT`, not `COUNTROWS`, even though the contract states one row per
house bill, defensive modelling never assumes a table has no duplicates without
checking, per `SCHEMA_CONTRACT.md` §3.5 landmine #2 (the duplicated `BookingNo`
pattern elsewhere in this model is the concrete precedent for why this caution is
not paranoia).

```dax
Air vs Ocean Cost Index (per kg) :=
VAR AirCostPerKg   = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Air" )
VAR OceanCostPerKg = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Ocean" )
RETURN DIVIDE ( AirCostPerKg, OceanCostPerKg )
```
Watch-out: FCL cargo's `ChargeableWeightKg` is not meaningfully comparable to an
LCL or air per-kg figure (FCL prices per container, not per kg), restrict this
comparison to LCL and air, or use a per-shipment revenue basis instead, when FCL is
in scope.

---

## Checklist: remaining 3 Air & LCL KPIs, same method

- [ ] `ALC.SLS.CONV`, Quote-to-Book Conversion (booking-stage proxy, read the
      dictionary's §7 Gaps entry #3 before shipping the description; this is *not*
      true top-of-funnel win rate, since a quote that never reached a booking
      attempt is invisible to this measure by construction)
- [ ] `ALC.TRN.MODAL`, Ocean vs Air Transit Index (median-based, not mean, given
      the right-skewed distribution from `SCHEMA_CONTRACT.md` §3.4)
- [ ] `ALC.WT.VOLMIX`, Volumetric-Driven Shipment Share:
      `COUNT(ChargeableWeightKg > GrossWeightKg) / COUNT(all)`, segment by mode
      before reporting, mixing 1:6000/1:5000/1:1000 populations produces an
      uninterpretable blend, same caution as the chargeable-weight measures above

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 19.1: the three chargeable-weight measures (25 min)
Build `Chargeable Weight kg (Air 1:6000)`, `Chargeable Weight kg (Air 1:5000)`, and
`Revenue Tons (LCL)`. Predict, before checking, whether summing the two air
measures together produces a meaningful "total air chargeable weight" figure, is
this safe, given both are the same unit (kg) on disjoint populations, or does the
same-column-different-rule caution still apply? Explain your answer.

### Exercise 19.2: Yield per kg, naive vs correct (25 min)
Build both variants. Predict the gap's rough size using the same denominator logic
as every other naive/correct pair this week, is `ChargeableWeightKg` for air
shipments a wide-range or narrow-range denominator, given document couriers and
charter consolidations both exist in the same fact table? Then verify.

### Exercise 19.3: the ocean-rule-on-air error, demonstrated (30 min)
Deliberately build a wrong measure: apply the ocean LCL 1:1000 rule to an air
shipment's volume, i.e. `MAX(GrossWeightKg, VolumeCbm)` for `ModeGroup = "Air"`
rows, note this literally compares a kilogram number to a bare cubic-metre number
with no unit conversion at all, which is the bug. Before building anything, reason
about it dimensionally: `VolumeCbm` for a shipment is typically a two- or
three-digit number of cubic metres; `GrossWeightKg` is typically a three- to
five-digit number of kilograms. For `MAX(GrossWeightKg, VolumeCbm)` to ever pick
`VolumeCbm`, the shipment's density would have to fall below roughly 1 kg per cubic
metre, lighter than air itself, physically impossible for real cargo. Predict, on
that basis, what `MAX(GrossWeightKg, VolumeCbm)` will return for essentially every
row before you run it. Then verify by comparing it against `GrossWeightKg` directly
for the same shipments, and separately against the real
`Chargeable Weight kg (Air 1:6000)`.

### Exercise 19.4: the remaining KPIs and the modal cost index (30 min)
Build the three checklist KPIs plus `Air vs Ocean Cost Index (per kg)` and `Gross
Profit per House Bill`. Predict, before checking, whether the modal cost index will
land closer to 4× or closer to 8× (the dictionary's stated typical range) for this
dataset, restricting the comparison to LCL and air only as the watch-out demands.

---

## Ship

`08 Air & LCL` now holds all 9 KPIs. All three chargeable-weight/revenue-ton
measures described with which rule population they belong to; `Yield per kg`'s
naive twin marked `[DO NOT USE]`.

```
git add .
git commit -m "Day 19: Air & LCL measure library, 9 KPIs, chargeable-weight rule discipline documented"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] All 9 Air & LCL KPIs exist in `08 Air & LCL`, each described with its
      `[KpiCode]` and, for the three weight/revenue-ton measures, which rule
      population it belongs to.
- [ ] `Yield per kg` and its naive twin both exist and you can state the gap and
      why it is the size it is.
- [ ] You built the deliberate 1:1000-on-air error and can state the multiple by
      which it diverges from the correct 1:6000 figure, from your own numbers, not
      just the theoretical 166.67-vs-1 ratio.
- [ ] You can state, without notes, why 1:6000 and 1:5000 both legitimately exist
      and which shipments end up costing more under 1:5000.
- [ ] Predictions recorded, misses annotated.
