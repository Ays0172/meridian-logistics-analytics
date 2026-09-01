# Day 15: solutions

---

## Spaced recall answers

1. A calculation group applies to **every** measure in the model by default,
   including ones where the reshape is meaningless (a count-distinct, a static
   target, an already-time-shifted ratio). The fix is auditing it against every
   "shape" of measure before shipping widely, and `Calculation Group Precedence`
   / per-measure exclusion for the cases that genuinely need to opt out.
2. Fiscal year starts 1 October and is named for the year it ends in (Oct 2025–Sep
   2026 = FY26). In DAX: `TOTALYTD ( <expr>, DimDate[Date], "09-30" )` or
   `DATESYTD ( DimDate[Date], "09-30" )`.
3. It disagreed by 8.5 points because `FactTarget`'s `ACT` rows are not an
   aggregation of `FactPortCall` at all, by any method — `build_fact_target`
   (`01_generator/meridian/facts_land.py`) draws every `TargetValue`, `ACT`
   included, from an independent `rng.uniform(0.60, 0.98, ...)` call with no read
   of any transactional table. The tempting first guess (an unweighted mean
   across the 7 trade-lane rows, the Day 9 averaging trap recurring) is worth
   checking against the generator before reporting it — it's exactly the shape of
   explanation that sounds right and isn't, here. The real, checkable reason is
   simpler and less flattering to the pattern-matching instinct: `FactTarget` is
   a separately-generated planning-system snapshot with no arithmetic
   relationship to the live data, so it is never guaranteed to reconcile with a
   live recomputation, on this dataset or any other.
4. Transaction fact (`FactShipment`, `FactBooking`, `FactContainerMove`, one row
   per event, fully additive); periodic snapshot (`FactInventorySnapshot`, a
   balance as of one date, semi-additive over time); accumulating snapshot
   (`FactShipmentMilestone`, one row per shipment, updated in place).
5. `01 Core`, created Day 8. Since then: Day 9 added `02 Ratios`; Day 10 added
   `03 Iterators`; Day 11 added `04 Time`; Day 12 added `03 Inventory
   (semi-additive)`; Day 13 added `04 Targets & Segmentation`.

---

## Exercise 15.1: the scaffolding

`03 Iterators` and `03 Inventory (semi-additive)` **do** coexist without conflict.
Power BI's Display Folder is a plain string property on each measure, there is no
uniqueness constraint on the leading number, and the Fields pane simply groups
measures by the exact string, creating two visually distinct folders that happen to
sort next to each other because they share a first character. This is worth
predicting wrong once: it is easy to assume folder numbers behave like sheet order
or a primary key, and they don't.

---

## Exercise 15.2: OCN.VOL.TEU and OCN.VOL.FFE

```dax
TEU Volume := SUM ( FactContainerMove[Teu] )
Laden TEU Volume := CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
FFE Volume := SUM ( FactContainerMove[Ffe] )
```

**TEU Volume is the larger number, by roughly 1.6×.** Per `SCHEMA_CONTRACT.md`
§1.9, `DimEquipment.TeuFactor`/`FfeFactor` runs `1.0/0.5` for a 20' box and
`2.0/1.0` for a 40'/45' box, a 20' box counts as a *whole* TEU but only *half* an
FFE. Since the fleet mix skews toward 40'/45' equipment (the FFE-native sizes), the
gap is not the full theoretical 2× a naive "TEU always ≈ 2×FFE" assumption would
predict, it lands closer to 1.6–1.7× once the real 20'/40' mix is accounted for.
The exact multiple is worth confirming against your own build's equipment mix
rather than assumed, per the KPI's own watch-out: TEU and FFE totals for the same
fleet are never numerically comparable as a combined figure, only side by side.

---

## Exercise 15.3: re-foldering Week 2 measures

```dax
Revenue per FFE :=
CALCULATE (
    DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) ),
    KEEPFILTERS ( FactShipment[Ffe] > 0 )
)
-- folder: 05 Ocean Liner\Revenue & Cost   (OCN.REV.FFE -> REV)
-- description: [OCN.REV.FFE] Average commercial yield per FFE carried; excludes
-- empty repositioning by construction (no Revenue_usd row exists for an empty
-- move) and restricts to Ffe > 0 so air shipments' revenue doesn't ride along
-- with nothing in the denominator. Non-additive weighted ratio, never average
-- lane-level rates.

Lines Per Labour Hour := DIVIDE ( SUM ( FactWarehouseTask[LinesProcessed] ), SUM ( FactWarehouseTask[LabourHours] ) )
-- folder: 07 Warehouse & Inventory\Rate & Utilisation   (WHS.PRD.LPH -> PRD)
-- description: [WHS.PRD.LPH] Order lines processed per hour of direct labour, the
-- primary warehouse productivity KPI. Non-additive weighted ratio; compare by
-- RoleName/TenureBand, never as one site-wide number across TaskType.
```

Both measures' DAX is unchanged from Day 9, only the `DisplayFolder` and
`Description` properties move. This is the point: the taxonomy organises measures
you already trust, it does not require rebuilding them.

---

## Exercise 15.4: OCN.REL.SCHED naive vs correct, formalised

```dax
Schedule Reliability Rolling 8wk :=
VAR LastDate = MAX ( DimDate[Date] )
VAR WindowStart = LastDate - 55
VAR CallsInWindow =
    CALCULATETABLE ( FactPortCall, DATESBETWEEN ( DimDate[Date], WindowStart, LastDate ) )
RETURN
    DIVIDE (
        COUNTROWS ( FILTER ( CallsInWindow, FactPortCall[IsOnTimeArrival] = 1 ) ),
        COUNTROWS ( CallsInWindow )
    )
-- folder: 05 Ocean Liner\Rate & Utilisation   (OCN.REL.SCHED -> REL)
-- description: [OCN.REL.SCHED] Share of port calls arriving within ±1 calendar day
-- of the originally published (never revised) ETA, trailing 56 days. Non-additive;
-- recompute per window, never average sub-window rates.

[DO NOT USE] Schedule Reliability Rolling 8wk (naive) :=
AVERAGEX (
    VALUES ( DimDate[ISOWeekLabel] ),
    CALCULATE ( AVERAGE ( FactPortCall[IsOnTimeArrival] ) )
)
-- folder: 05 Ocean Liner\Rate & Utilisation (same subfolder as the correct version, deliberately)
-- description: [DO NOT USE, OCN.REL.SCHED naive] Averages 8 pre-aggregated weekly
-- rates with equal weight regardless of call volume. See "Schedule Reliability
-- Rolling 8wk" for the pooled, correct version.
```

**At the full-history grand total, expect the gap to be smaller than Day 9's
Lines-per-Labour-Hour gap (21.9%)**: both measures are still averaging
on-time-arrival rates over roughly comparable weekly call volumes across most of
the 5-year history, so the correlation between the per-week rate and that week's
call count is weak outside of any specific shock. A grand-total comparison across
2021–2026 mostly cancels the two methods out.

**Why a small grand-total gap does not make the naive version safe:** the
dictionary's own commentary is explicit that this exact naive/correct gap *drifts
further apart precisely as call volume varies week to week*, and `SCHEMA_CONTRACT.md`
§3.3 describes exactly that condition happening for nine weeks straight: the Jul–Sep
2025 congestion event at `NLRTM`/`USLAX`. A measure that looks nearly identical to
its naive twin across five years of mostly-stable weekly volume can still diverge
sharply the moment it is filtered down to the one nine-week window where the
business question actually matters, a grand-total average is exactly the filter
context in which this specific bug is most likely to go undetected, because it is
the filter context in which naive averaging error is at its smallest and least
representative.

---

## Exercise 15.5: description audit

By the end of today, eight measures should carry a non-empty description:
`Revenue` (Day 8, base), `Revenue FCL`/`Revenue FCL Kept` (Day 9, if described at
the time), `Lines Per Labour Hour`, `Revenue per FFE`, `On Hand Value (as of)`,
`Days of Supply (as of)`, `Actual Schedule Reliability (via TREATAS)`. Any measure
missing one gets it added now, using the `[KpiCode] <definition>. <watch-out>.`
template from the Concept section, retrofitting eight measures today costs
minutes; retrofitting 150 in Week 6 costs an afternoon.

---

## Reference values used above

| Quantity | Value / note |
|---|---|
| `DimEquipment.TeuFactor` (20'/40'/45') | 1.0 / 2.0 / 2.25 |
| `DimEquipment.FfeFactor` (20'/40'/45') | 0.5 / 1.0 / 1.125 |
| TEU:FFE ratio at grand total | ≈1.6–1.7×, fleet-mix dependent, confirm against your own build |
| Congestion window (schedule reliability shock) | 14 Jul – 14 Sep 2025, NLRTM/USLAX |
