# Day 12 — solutions

All figures computed live against the connected model (`FactInventorySnapshot`:
986,326 rows across 581 distinct snapshot dates, 2021-08-22 → 2026-08-27;
`FactShipmentMilestone`: 493,608 rows) — a few live-feed days past
`README.md` §1's shipped baseline (983,262 / 491,765, watermark 2026-08-20).
**These row counts and the exact snapshot-date range will differ slightly on
your own build**, since `FactInventorySnapshot`/`FactShipmentMilestone` grow by
one row per shipment/snapshot every day the live feed runs; the EOM values,
ratios and the naive/correct comparisons below are what to check your own
numbers against in shape, not these two counts to the digit.

---

## Spaced recall answers

1. A boolean `CALCULATE` filter argument on a column **replaces** any existing
   filter on that column (it desugars to `FILTER(ALL(col), …)`), unless wrapped in
   `KEEPFILTERS`, which intersects instead.
2. Because the naive average gives every row equal weight regardless of its
   denominator, and productivity ratios are usually negatively correlated with
   their denominator (short tasks run more "efficient" per hour) while pricing
   ratios usually are not.
3. Fully additive, semi-additive (additive over some dimensions, not over time),
   non-additive (ratios, percentiles, medians).
4. One row per SKU × warehouse × customer, **as of one snapshot date** — a balance,
   not an event.
5. `-1`, never `BLANK()` — so every comparison against "not yet happened" requires
   an explicit branch rather than accidentally passing a null-check.

---

## Exercise 12.1 — the semi-additive trap, measured

| Month | Last snapshot date ≤ month end | Correct EOM value | Naive sum across the month | Multiple |
|---|---|---|---|---|
| May 2025 | 2025-05-25 | **$2,016,073,487** | **$8,148,025,014** | **4.04×** |
| Jun 2025 | 2025-06-29 | **$2,046,271,287** | *(compute yourself — same pattern)* | ~4× |
| Jul 2025 | 2025-07-27 | **$2,031,121,867** | *(compute yourself — same pattern)* | ~4× |

**Why the multiple varies slightly month to month:** it tracks how many weekly
snapshot rows fall inside that specific calendar month, which depends on where the
weekly cadence's fixed day-of-week lands relative to month boundaries — a month
that happens to contain five weekly snapshots (rather than four) will show a larger
naive/correct ratio, purely from calendar alignment, not from any real change in
inventory. That itself is worth sitting with: **the size of this specific bug's
error is not even constant — it drifts with the calendar**, which is exactly why
"the naive number is usually close enough" is not a safe assumption to carry from
one period to the next.

At the full 5.0-year history: naive unfiltered `SUM(OnHandValueUsd)` returns
**$1,303,433,323,735** against a true point-in-time value on the order of **$2-3
billion** — roughly **500×** too high (consistent with the figure Week 6's case
drills and STAR stories use for this same bug), because it is summing 581 dates'
worth of the same rotating stock.

---

## Exercise 12.2 — the general point-in-time pattern

```dax
On Hand Value (as of) :=
CALCULATE (
    SUM ( FactInventorySnapshot[OnHandValueUsd] ),
    LASTNONBLANK ( DimDate[Date], CALCULATE ( COUNTROWS ( FactInventorySnapshot ) ) )
)
```

This returns the same three values as the manual `FILTER`/`MAX` version in 12.1 for
every date tested — `LASTNONBLANK` walks backward from the current filter
context's last date until it finds one `FactInventorySnapshot` actually has rows
for, which is precisely "the most recent known balance," whether that's yesterday
(inside the daily-cadence window) or up to six days ago (inside the older
weekly-cadence window).

**`Days of Supply (as of)` should be averaged, not summed, at a point in time.**
`DaysOfSupply` is a per-SKU-per-site *rate* (roughly, how many days the current
on-hand quantity will last at the current consumption rate) — it is not a
quantity that means anything added across SKUs. Summing ten SKUs' "12 days of
supply" does not give you "120 days of supply" for the group; it gives you a
number with no interpretation. The correct aggregation across SKUs at a point in
time is a weighted average (weight by `OnHandUnits` or `OnHandValueUsd`), not a
sum — the same pooled-vs-naive distinction from Day 9, now stacked on top of the
point-in-time filter from this exercise.

```dax
Days of Supply (as of), weighted :=
VAR PointInTime = CALCULATETABLE ( FactInventorySnapshot,
                     LASTNONBLANK ( DimDate[Date], CALCULATE ( COUNTROWS ( FactInventorySnapshot ) ) ) )
RETURN
    DIVIDE (
        SUMX ( PointInTime, FactInventorySnapshot[DaysOfSupply] * FactInventorySnapshot[OnHandUnits] ),
        SUMX ( PointInTime, FactInventorySnapshot[OnHandUnits] )
    )
```

---

## Exercise 12.3 — the `-1` sentinel, measured

| Measure | Value |
|---|---|
| `Avg Lag (all rows)` | **37.26 days** |
| `Pct Journey Complete` | **97.99%** |
| `Avg Milestones Completed` | **12.14** (out of 14 tracked milestone columns) |

**The gap worth chasing:** if 98% of journeys are complete, a naive prediction
says `Avg Milestones Completed` should sit close to 14, not 12.14 — roughly 1.9
milestones short on average even though almost everyone is "complete." The
resolution is in what `IsJourneyComplete` actually flags versus what
`MilestonesCompleted` counts: `IsJourneyComplete` is set once the shipment reaches
its **operationally meaningful end state** (cargo delivered and cleared), while two
of the 14 tracked columns — `TranshipmentDischargeDateKey` and
`TranshipmentLoadDateKey` — only apply to shipments that actually transship.
A direct (non-transshipped) routing never populates those two milestones at all,
so it is structurally impossible for those shipments to reach 14/14 even though
they are entirely, correctly complete. Averaging "milestones completed" across a
mix of transshipped and direct routings without accounting for that structural
difference in how many milestones *apply* is the same class of error as averaging
a ratio without weighting it by what varies underneath it — the specific mechanism
changes, the shape of the mistake (comparing things whose denominators differ) does
not.

---

## Exercise 12.4 — why a slicer doesn't fix it

Setting a date slicer to one month-end date and using a plain `SUM` happens to
produce the right *number* for that one filter state, but it does not fix the
*measure* — the measure is still semi-additive and will silently misbehave the
moment anyone removes the slicer, changes it to a range, puts `Year` on rows
instead of a single date, or builds a card visual with `ALLSELECTED` behind it that
no longer respects a single-date assumption. A measure that is only correct under
one specific filter context is not correct — it is coincidentally right once. The
fix belongs inside the DAX (`LASTNONBLANK`), not in report-level filter discipline
that every future report author has to remember and nobody enforces.

---

## Reference values used above

| Quantity | Value |
|---|---|
| `FactInventorySnapshot` total rows | 986,326 |
| Distinct snapshot dates | 581 |
| Date range | 2021-08-22 → 2026-08-27 |
| May 2025 EOM (2025-05-25) | $2,016,073,487 |
| Jun 2025 EOM (2025-06-29) | $2,046,271,287 |
| Jul 2025 EOM (2025-07-27) | $2,031,121,867 |
| Naive May 2025 sum | $8,148,025,014 |
| Naive May multiple vs correct | 4.04× |
| Naive whole-history sum | $1,303,433,323,735 |
| `FactShipmentMilestone` total rows | 493,608 |
| `Avg Lag (all rows)` | 37.26 days |
| `Pct Journey Complete` | 97.99% |
| `Avg Milestones Completed` | 12.14 / 14 |
| Rows with `GateOutDestinationDateKey = -1` | 9,945 |
