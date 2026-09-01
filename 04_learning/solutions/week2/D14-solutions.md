# Day 14 — solutions

---

## Spaced recall answers

1. `TREATAS ( <table>, <col1>, … )` applies `<table>`'s current values as a
   filter onto `<col1>`, … — the first argument supplies values, the trailing
   column arguments get filtered.
2. `SUMMARIZE`'s extension-column expressions did not respect the per-group
   filter context on a derived table the way a real model table would — both
   buckets returned the whole table's count. Use `SUMMARIZECOLUMNS` or explicit
   `FILTER`+`COUNTROWS`/`SUMX` instead.
3. Recomputed (pooled, from `FactPortCall`) = 66.22%; `FactTarget`'s stored `ACT`
   (unweighted mean across 7 lanes) = 74.71%, an 8.5-point gap. Reasons: (1) the
   stored actual averages 7 lane-level rows unweighted — the Day 9 averaging trap
   recurring in a new context; (2) the two numbers may use different definitional
   cutoffs (recomputed vs a separately-recorded planning snapshot).
4. 2026-08-20 — the last snapshot date with full SKU coverage (1,584 SKUs); dates
   after it in the live feed only touch a handful of SKUs per day, so "today" would
   silently classify almost the whole catalog as having zero value.

---

## Exercise 14.1 — build the group

`Current` matches plain `Revenue` in **every** year, not just 2021 — `Current` is
defined as `SELECTEDMEASURE()` with no time manipulation at all, so it is always
identical to the base measure regardless of year. The item that is special in 2021
specifically is **`PY`**: since `DimDate` starts 2021-01-01, `SAMEPERIODLASTYEAR`
in 2021 has no prior year to shift into, so `PY` (and therefore `YoY %`, which
depends on it) returns blank for every 2021 row — not a bug, a correct reflection
of there being no 2020 to compare against.

## Exercise 14.2 — a measure the calculation group should not touch

`Active Carrier Count` under `YoY %` returns a number — DAX does not refuse to
apply a calculation item to a measure just because the result is meaningless. A
"year-over-year percent change in distinct carrier count" is a technically valid
computation and a substantively strange thing to put in front of a reader: carrier
count does not have a "year ago" in the same sense revenue does, and a small
absolute change (say, 2 carriers) can produce a large, attention-grabbing
percentage that overstates what actually happened.

**What this means for auditing:** a calculation group is model-wide by default —
shipping one without checking it against every "shape" of measure in the library
(counts, ratios, already-time-shifted measures, static targets) means the first
person to put the wrong measure next to `YoY %` in a report gets a technically
correct, substantively misleading number, with nothing in the UI warning them.
This is exactly why `Calculation Group Precedence` and per-measure exclusion exist
— worth returning to once Week 3's full library makes the blast radius real.

## Exercise 14.3 — fiscal year check

| Period | Revenue |
|---|---|
| Calendar YTD through 30 Sep 2025 (Jan–Sep) | **$300,286,005** |
| FYTD (fiscal year end 30 Sep, per `README` §7) through 30 Sep 2025 (Oct 2024–Sep 2025) | **$435,565,820** |
| Difference — Q4 2024 (Oct–Dec), the quarter FYTD includes that calendar YTD doesn't | **$135,279,815** |

FYTD is **45.0% larger** than plain calendar YTD at the same date, entirely because
it includes a whole extra quarter (Oct–Dec 2024) that calendar-year `TOTALYTD`
does not. Using a plain `TOTALYTD` where a fiscal-year measure was intended is not
a rounding difference — at this model's revenue run-rate it is a nine-figure error,
and it will not throw a warning; the number will simply look plausible.

---

## Checkpoint 2 — Part B reference answers (compare, don't copy)

1. `CALCULATE`'s boolean filter arguments desugar to `FILTER(ALL(col), …)`, which
   clears the column's existing filter before applying the new one — replacement,
   not intersection. `KEEPFILTERS` suppresses the `ALL`, so the new filter
   intersects with whatever was already there instead of overwriting it.
2. It is imprecise because the size of the error depends on the correlation
   between the per-row ratio and its own denominator — strongly negative
   correlation (productivity metrics) produces large errors; near-zero correlation
   (pricing metrics) produces almost none. "Never average an average" is the right
   instinct without the mechanism; the correlation is the mechanism.
3. A column is semi-additive when it is meaningful to sum across some dimensions
   (SKU, warehouse, customer) but not across time, because it represents a balance
   sampled repeatedly rather than an event. `FactInventorySnapshot[OnHandValueUsd]`
   is semi-additive; `FactShipmentMilestone[LagTotalDoorToDoor]` is fully additive
   (well, averageable) because it is computed once per shipment, not resampled.
4. Reach for `TREATAS` when two tables that need to filter each other share a
   real-world concept but no physical relationship can connect them — different
   grain, or a text column instead of a key. Always verify, with `DISTINCT` on
   both sides, that the columns you're bridging actually contain the same values
   at the same granularity before trusting the join — `Region` vs `TradeRegion`
   this week is the concrete example of guessing wrong.
5. Calculation groups let one set of time-intelligence (or other reshaping) logic
   apply to every measure in the model without duplicating it per-measure. The
   sharp edge: they apply to every measure by default, including ones where the
   reshape is meaningless, so a calculation group needs auditing against the
   model's full measure library before it ships widely.

Part C has no reference answer — it is your own finding, written for your own
portfolio.
