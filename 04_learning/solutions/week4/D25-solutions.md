# Day 25: solutions

---

## Spaced recall answers

1. `OTIF % = DIF x DOQ x DOT`. DIF ~0.962, DOQ ~0.987, DOT ~0.913, multiplicative
   headline ~0.867 (86.7%). The naive arithmetic mean of the same three figures is
   ~0.954 (95.4%) - an 8.7-point gap purely from choosing `+/3` instead of `x`.
2. The `-1` sentinel marks task types where `DockToStockMinutes` doesn't apply.
   Left unfiltered, it is a large negative outlier disguised as a valid number,
   and it drags any unfiltered average sharply and misleadingly downward.
3. `AbcClassStatic` is a point-in-time seed set once during data generation; a
   dynamic reclassification anchored to one snapshot date reflects only that
   date's on-hand value and only SKUs active in the model at that point -
   structurally different populations and timing, not just "the business changed
   since the seed."
4. `Lines per Labour Hour := DIVIDE(SUM(FactWarehouseTask[LinesProcessed]),
   SUM(FactWarehouseTask[LabourHours]))`, pooled. Day 9 measured the naive
   `AVERAGEX` per-task-ratio version at roughly **+21.9%** high (38.48 pooled vs.
   46.89 naive), because short tasks run efficient per hour and long tasks don't,
   so the naive mean over-weights the short, inflated-ratio tasks.
5. They're semi-additive over date because each day's occupancy figure is a valid
   point-in-time snapshot, but summing the ratio (or its components) across
   multiple days produces a meaningless total - you can't add up "80% full on
   Monday" and "85% full on Tuesday" into a duration or a total. Trending across a
   month requires averaging the daily ratio (or explicitly switching to
   `AVERAGEX` over `VALUES(DimDate[Date])`), never summing positions across days.

---

## Exercise 25.1: OTIF comparison

```dax
[DO NOT USE] OTIF % (naive) :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN ( Dif + Doq + Dot ) / 3

OTIF % :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN Dif * Doq * Dot
```

Expected gap against your own data: close to the contract's documented **8.7
points** (95.4% naive vs. 86.7% correct). A materially different gap in your own
build (more than a point or two off) is worth investigating before shipping the
visual - check that both measures are reading the same underlying `FactShipment`
population with no accidental filter mismatch between them.

## Exercise 25.2: dock-to-stock sentinel

Filtering out `-1` should shift the average **up** (the correct, filtered figure
lands inside the 60-120 minute directional band the KPI dictionary names), while
the unfiltered version reads noticeably lower and outside any sensible band,
dragged down by the large negative sentinel values sitting in rows where the
measure never applied. The exact point shift depends on how many rows in your
build's `FactWarehouseTask` carry the sentinel for non-Receive/Putaway task types.

## Exercise 25.3: productivity small multiples

Expect the lowest `Lines per Labour Hour` figures on **night shift** (contract
baseline 97.4% pick accuracy vs. 99.1% overall gives the general direction, and
labour productivity follows a similar tenure/shift pattern) and among
**first-six-months agency staff**. The small-multiples view should make this
visible directly, rather than requiring a filtered drill-down to discover it - that
visibility is the entire point of building small multiples instead of one
site-wide productivity card.

## Exercise 25.4: ABC dual-share

Expect Class A to land closer to the classic Pareto pattern: a **small SKU count
share** (roughly 15-20%) carrying a **large value share** (roughly 70-80%). That
combination implies purchasing and demand-planning attention should prioritise
**SKU-level review** for Class A specifically - a small, identifiable list of
individually important SKUs - rather than a broad category-level policy, since a
category-level rule applied uniformly would under-manage the handful of SKUs that
actually carry most of the value at risk.
