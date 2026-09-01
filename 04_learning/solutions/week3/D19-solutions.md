# Day 19: solutions

---

## Spaced recall answers

1. Naive (arithmetic mean of DIF/DOQ/DOT) ≈ 95.4%, correct (product) ≈ 86.7%, an
   8.7-point gap. The bug was using `+`/`3` instead of `×` on a joint requirement.
2. Because the dynamic classification ranks SKUs by the exact `OnHandValueUsd`
   figure that also feeds the value-share numerator, classification basis and
   measured value are built from the same source, so the concentration the
   classification finds tracks the concentration actually being measured. The
   static seed's basis is undocumented and may not track current on-hand value at
   all, so there's no structural reason it should reproduce 80/20.
3. Filtering out a "not applicable"/"not yet happened" sentinel before averaging or
   summing a column, because the sentinel is a valid-looking number that corrupts
   the aggregate if left in. This week: `Avg Container Dwell Hours` (`DwellHours <>
   -1`), `Avg Dock-to-Stock Minutes` (`DockToStockMinutes <> -1`), `Inventory
   Accuracy %`/`Shrinkage Rate` (`PhysicalCountUnits <> -1`).
4. Tonne-km is a row-level product of two columns (weight and distance) that varies
   independently leg to leg. `SUM(WeightKg) × SUM(DistanceKm)` at the total level
   cross-multiplies every leg's weight against every *other* leg's distance summed
   together, it does not reconstruct the sum of each leg's own weight × its own
   distance. `SUMX` computes the product row by row, then sums; that is the only
   form that means anything.
5. `IsHigherBetter` lets a single generic "vs target" measure know, per KPI,
   whether being above or below the target value is the good direction, without
   it, a generic attainment measure would have to hardcode which KPIs are
   "higher is better" (revenue, on-time %) versus "lower is better" (cost per km,
   deadhead %) rather than reading that logic from the data itself.

---

## Exercise 19.1: the three chargeable-weight measures

```dax
Chargeable Weight kg (Air 1:6000) :=
CALCULATE ( SUM ( FactShipment[ChargeableWeightKg] ), RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:6000" )

Chargeable Weight kg (Air 1:5000) :=
CALCULATE ( SUM ( FactShipment[ChargeableWeightKg] ), RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:5000" )

Revenue Tons (LCL) :=
CALCULATE ( SUM ( FactShipment[RevenueTons] ), DimMode[ModeCode] = "LCL" )
```

**Summing the two air measures together is safe, unlike summing across all three
rule families.** Both `Chargeable Weight kg (Air 1:6000)` and `Chargeable Weight kg
(Air 1:5000)` are the same physical unit, kilograms, resolved via `MAX(actual,
volumetric)`, on two **disjoint** shipment populations (a shipment is tagged with
exactly one `ChargeableWeightRule`). Adding "total air chargeable weight kg" across
the two rule populations is arithmetically the same as `SUM(ChargeableWeightKg)`
filtered to `ModeGroup = "Air"` with no rule split at all, it just tells you total
air kilos, not anything about the *rate* each rule produced. What is **not** safe
is dividing that combined kilo figure by revenue or comparing a yield computed
across the mixed population, the *rate economics* differ by rule even though the
underlying unit (kg) is identical, which is exactly the watch-out this domain keeps
repeating: same unit, same column name, different economics underneath.

---

## Exercise 19.2: Yield per kg, naive vs correct

```dax
Yield per kg :=
CALCULATE ( DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Air" )

[DO NOT USE] Yield per kg (naive) :=
CALCULATE ( AVERAGEX ( FactShipment, DIVIDE ( FactShipment[Revenue_usd], FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Air" )
```

**Expect a meaningful gap, not a near-zero one.** `ChargeableWeightKg` for air
shipments is a genuinely **wide-range denominator**, a 40 kg document courier
shipment and a 12,000+ kg charter consolidation coexist in the same `FactShipment`
population, a three-orders-of-magnitude spread far wider than, say, `Ffe` on ocean
shipments. That width is exactly the condition Day 9's mechanism predicts will
produce a large naive error: many small, high-per-kg-rate document shipments can
dominate an unweighted average even though they represent a tiny share of total air
revenue and weight. Expect the naive figure to read noticeably higher than the
pooled correct figure, similar in shape (though not necessarily identical size) to
the `Lines Per Labour Hour` gap from Day 9.

---

## Exercise 19.3: the ocean-rule-on-air error, demonstrated

```dax
[DEMONSTRATION ONLY] Wrong Chargeable Weight, Ocean Rule on Air :=
VAR AirShipments = FILTER ( FactShipment, RELATED ( DimMode[ModeGroup] ) = "Air" )
RETURN SUMX ( AirShipments, MAX ( FactShipment[GrossWeightKg], FactShipment[VolumeCbm] ) )
```

**`MAX(GrossWeightKg, VolumeCbm)` returns `GrossWeightKg` for essentially every
single row.** This follows from dimensions alone, before touching the data:
`VolumeCbm` is a bare count of cubic metres (typically single- to triple-digit for
a house-bill shipment); `GrossWeightKg` is a count of kilograms (typically
three-to-five-digit). For `VolumeCbm` to exceed `GrossWeightKg` numerically, the
shipment's density would have to be below roughly 1 kg per cubic metre, less
dense than air itself. No real air-freight commodity is that light, so the ocean
rule's `MAX` never picks the volume branch at all when misapplied this way.

**The failure mode this produces is worse than "off by a fixed multiple", it is
structurally blind to the exact population the correct rule exists to catch.** The
wrongly-applied measure silently collapses to "always bill actual weight," which
means every genuinely volumetric-driven shipment (`ALC.WT.VOLMIX`'s population,
where `ChargeableWeightKg > GrossWeightKg` under the real 1:6000 rule) gets
**under-billed** to its actual weight instead of its correctly higher volumetric
weight, and the error is invisible in aggregate, because most shipments (the
weight-bound majority) show no divergence at all. Comparing
`[DEMONSTRATION ONLY] Wrong Chargeable Weight` against the real
`Chargeable Weight kg (Air 1:6000)` should show the two matching exactly for
weight-bound shipments and the wrong version reading **lower** for every
volumetric-driven shipment, confirm this split in your own build by cross-filtering
on `Volumetric-Driven Shipment Share`'s underlying condition. The "5000 vs 6000"
framing from the Concept section is a genuinely different, smaller-scale comparison
(two air divisors 1.2× apart); this exercise is the larger-scale version, an
entire billing methodology (divide-by-thousands volumetric weight) silently
replaced by a different one (flat tonne-for-cbm) that, on this data's realistic
density range, behaves as if the volumetric branch does not exist at all.

---

## Exercise 19.4: the remaining KPIs and the modal cost index

```dax
Quote-to-Book Conversion (booking-stage proxy) :=
VAR Converted = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsConfirmed] = 1 || FactBooking[IsRolled] = 1 )
VAR AllQuotes = DISTINCTCOUNT ( FactBooking[QuoteKey] )
RETURN DIVIDE ( Converted, AllQuotes )

Ocean vs Air Transit Index :=
VAR OceanMedian = CALCULATE ( MEDIANX ( FactShipment, FactShipment[ActualTransitDays] ), DimMode[ModeGroup] = "Ocean" )
VAR AirMedian   = CALCULATE ( MEDIANX ( FactShipment, FactShipment[ActualTransitDays] ), DimMode[ModeGroup] = "Air" )
RETURN DIVIDE ( OceanMedian, AirMedian )

Volumetric-Driven Shipment Share :=
DIVIDE (
    COUNTROWS ( FILTER ( FactShipment, FactShipment[ChargeableWeightKg] > FactShipment[GrossWeightKg] ) ),
    COUNTROWS ( FactShipment )
)

Air vs Ocean Cost Index (per kg) :=
VAR AirCostPerKg   = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Air" )
VAR OceanCostPerKg = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Ocean" )
RETURN DIVIDE ( AirCostPerKg, OceanCostPerKg )

Gross Profit per House Bill := DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), DISTINCTCOUNT ( FactShipment[HouseBlNo] ) )
```

**Expect the modal cost index in the 4–8× band the dictionary states as typical**,
most likely toward the middle-to-upper end of that range for FCL-heavy ocean
traffic excluded and LCL/air compared directly, since air's per-kg cost structure
(dedicated aircraft space, faster transit) is intrinsically far more expensive per
kilogram than ocean's bulk-capacity economics, even before accounting for any
particular lane's specifics. Confirm against your own build; a result well outside
4–8× is worth checking for an FCL-contamination bug (FCL cargo's per-kg cost is not
meaningfully comparable, per the domain's own watch-out) before assuming the
number itself is correct.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Air volumetric-weight formula | `VolumeCbm × 1,000,000 ÷ 6,000 = VolumeCbm × 166.67` |
| Ocean LCL revenue-ton formula | `MAX(WeightKg ÷ 1000, VolumeCbm)`, flat 1,000 kg/cbm |
| Divisor comparison, 6000 vs 5000 | 1.2× (5000 charges bulkier cargo more) |
| Density threshold below which ocean rule would ever pick volume | < 1 kg/cbm (physically impossible) |
| Typical air-vs-ocean cost multiple per kg | 4–8× |
