# Day 12 — Snapshot fact tables, semi-additive measures, and the accumulating snapshot

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 75 min · Ship 30 min · Log 15 min

Every fact table you have touched so far — `FactShipment`, `FactBooking`,
`FactContainerMove` — is a **transaction fact**: one row per event, fully additive,
sum it across any dimension and the answer is meaningful. Today you meet the other
two fact table shapes in this model, and the mistake that transaction-fact habits
walk you straight into when you first touch them.

---

## Spaced recall (10 min, closed book)

1. State the rule for when a `CALCULATE` filter argument replaces versus
   intersects an existing filter, and what changes that.
2. Why does averaging a per-row ratio (`AVERAGEX` over per-row `DIVIDE`s) usually
   overstate a productivity metric and barely move a pricing metric?
3. Name the three additivity classes a numeric fact column can fall into.
4. What is `FactInventorySnapshot`'s grain, in one sentence?
5. Per this project's conventions (`00_docs/README` §7), what value does a
   not-yet-happened date column hold, and why not `BLANK()`?

---

## Concept

### Three fact table shapes, not one

| Shape | Example in this model | What a row means | Additive over time? |
|---|---|---|---|
| **Transaction fact** | `FactShipment`, `FactBooking`, `FactContainerMove` | one event | Yes — sum freely |
| **Periodic snapshot** | `FactInventorySnapshot` | SKU × warehouse × customer, **as of one date** — weekly for the older 18 months, daily for the latest 12 | **No** — sum across dates and you double-, quadruple-, or worse-count the same stock |
| **Accumulating snapshot** | `FactShipmentMilestone` | one row per shipment, **updated in place** as milestones happen, not re-inserted | Its lag/duration columns are fine to average; its date-key columns are not facts to aggregate at all |

You already know the transaction shape cold. The other two share one property that
breaks the instinct transaction facts trained into you: **a row is not an
independent, addable unit.** A snapshot row is a balance; an accumulating-snapshot
row is a single evolving record of one shipment's whole journey.

### The semi-additive trap, proven on this model

`FactInventorySnapshot[OnHandValueUsd]` is additive across `SkuKey`, `WarehouseKey`,
`CustomerKey` — at a single snapshot date, summing on-hand value across every SKU in
every warehouse gives you a real total inventory value. It is **not** additive
across `SnapshotDateKey`. Summing it across a date range adds the same stock to
itself once per snapshot date it was counted on.

Measured, not asserted — May 2025 has four weekly snapshot dates (25 May was the
last one on or before month-end):

| Measure | DAX shape | Value |
|---|---|---|
| **Naive** — sum across every May snapshot row | `CALCULATE(SUM(OnHandValueUsd), DATESBETWEEN(DimDate[Date], "2025-05-01", "2025-05-31"))` | **$8,148,025,014** |
| **Correct** — value as of the last snapshot on/before month end | `CALCULATE(SUM(OnHandValueUsd), FactInventorySnapshot[SnapshotDateKey] = <last date ≤ month end>)` | **$2,016,073,487** |

The naive number is **4.04× too high** — almost exactly the count of weekly
snapshots inside May, which is not a coincidence: you are not measuring stock, you
are measuring how many times the calendar happened to sample it.

Widen the mistake to the whole two-year history (581 distinct snapshot dates,
weekly-then-daily) and a plain `SUM` with no date filter at all returns
**$1.30 trillion** for a company whose real month-end inventory value sits around
**$2 billion**. That is not a rounding error, it is a measure that will pass code
review, look like a real number, and be wrong by three orders of magnitude — the
most dangerous kind of bug, because nothing about it looks broken.

### The fix: a point-in-time filter, not a sum

The general pattern for any semi-additive balance column:

```dax
On Hand Value (as of) :=
VAR AsOfDate = MAX ( DimDate[Date] )
VAR LastSnapshotOnOrBefore =
    CALCULATE ( MAX ( FactInventorySnapshot[SnapshotDateKey] ),
                FILTER ( ALL ( FactInventorySnapshot ), FactInventorySnapshot[SnapshotDateKey] <= AsOfDate ) )
RETURN
    CALCULATE ( SUM ( FactInventorySnapshot[OnHandValueUsd] ),
                FactInventorySnapshot[SnapshotDateKey] = LastSnapshotOnOrBefore )
```

Built-in time-intelligence functions (`LASTDATE`, `CLOSINGBALANCEMONTH`) assume the
fact table has a row for *every* date in the period, which is true here only for
the most recent 12 months (daily cadence) and false for everything older (weekly).
`LASTNONBLANK` over `DimDate[Date]` is the version that survives the gap — it walks
backward from the period end until it finds a date the fact table actually has a
row for, which is exactly "last known balance" and exactly what the manual
`FILTER`/`MAX` pattern above does by hand. Know both: the manual version because it
makes the mechanism visible, `LASTNONBLANK` because it is what you will actually
ship.

### The accumulating snapshot: `FactShipmentMilestone`

One row per shipment. Instead of one immutable fact per event, this table's row is
updated as the shipment progresses — 14 milestone date-key columns
(`BookingConfirmedDateKey` → `EmptyReturnDateKey`), 7 pre-computed `Lag*` duration
columns between consecutive milestones, plus `MilestonesCompleted`,
`CurrentMilestoneKey`, `IsJourneyComplete`.

Two things to hold at once:

**The `Lag*` columns are ordinary additive/averageable numbers** — `AVERAGE` or
`SUM` on `LagTotalDoorToDoor` behaves exactly like any transaction-fact measure,
because a lag is a duration computed once per shipment, not a balance sampled
repeatedly.

**The milestone date-key columns are not that.** A milestone not yet reached holds
`-1`, per this project's fixed convention (never `BLANK()` for a not-yet-happened
date — see `README` §7 and Week 1's work with the `-1` unknown-member pattern).
`AVERAGE(FactShipmentMilestone[GateOutDestinationDateKey])` on an in-progress
shipment average-blends real `yyyymmdd` integers with `-1` sentinels into a
meaningless number that will not even error — it will just be wrong, silently,
which is the same shape of danger as the semi-additive trap above wearing a
different disguise.

Live numbers from this table today: **`AVERAGE(LagTotalDoorToDoor)` = 37.26 days**
across 493,608 rows; **9,945 rows** currently carry `GateOutDestinationDateKey =
-1` — shipments genuinely still in flight, not shipments with missing data.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 12.1 — measure the semi-additive trap yourself (25 min)
Build both measures from the table above (`Naive`, `Correct`) against
`FactInventorySnapshot[OnHandValueUsd]`. Predict, before running, which will be
larger and roughly by what multiple, for **June 2025** and **July 2025**. Then
verify against the reference values in this day's solutions. Explain in one
sentence why the multiple is different in June than in May.

### Exercise 12.2 — build the general point-in-time pattern (25 min)
Write the `LASTNONBLANK`-based version of `On Hand Value (as of)` and confirm it
returns the same June and July numbers as your manual `FILTER`/`MAX` version from
12.1. Then build `Days of Supply (as of)` the same way, using
`FactInventorySnapshot[DaysOfSupply]` — predict first whether this column should be
summed or averaged at a point in time, and justify it from what the column means.

### Exercise 12.3 — the `-1` sentinel, measured (15 min)
Build two versions of average door-to-door lag broken out by
`IsJourneyComplete`:
```dax
Avg Lag (all rows)       := AVERAGE ( FactShipmentMilestone[LagTotalDoorToDoor] )
Pct Journey Complete     := DIVIDE ( CALCULATE ( COUNTROWS ( FactShipmentMilestone ), FactShipmentMilestone[IsJourneyComplete] = 1 ), COUNTROWS ( FactShipmentMilestone ) )
Avg Milestones Completed := AVERAGE ( FactShipmentMilestone[MilestonesCompleted] )
```
There are 14 milestone date columns on this table. Predict what
`Avg Milestones Completed` should be if 98% of journeys are complete, then check it
against the real number. If your prediction and the real number disagree by more
than a milestone or two, that gap is the exercise — go find out what
`IsJourneyComplete` is actually flagging that `MilestonesCompleted` isn't counting.
Write your finding in one sentence. (This is a genuine open question in this
dataset — there is a real, checkable answer, and finding it the way you found the
Rotterdam/LA congestion story in Week 2 is the point.)

### Exercise 12.4 — why not just filter the visual? (10 min)
A colleague suggests skipping the DAX and just putting a date slicer on the report
page set to month-end, then using a plain `SUM`. Explain in 2–3 sentences why this
does not actually fix the bug, using what you know about `ALLSELECTED` from Day 9.

---

## Ship

Add to `_Measures`, in a display folder `03 Inventory (semi-additive)`:
`On Hand Value (as of)`, `Days of Supply (as of)`, and both accumulating-snapshot
measures from 12.3, each with a `description` property explaining in one sentence
why it cannot be summed across dates — the next person to open this model should
not have to rediscover this the hard way.

```
git add .
git commit -m "Day 12: snapshot vs accumulating-snapshot patterns, semi-additive measures shipped"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can state, from memory, the difference between a transaction fact, a
      periodic snapshot, and an accumulating snapshot, with a table from this
      model as the example of each.
- [ ] You measured the semi-additive trap yourself and can quote the multiple by
      which the naive sum overstates a real month's inventory value.
- [ ] You can explain why `-1` and not `BLANK()` for a not-yet-happened milestone
      date, and what aggregating over it silently does.
- [ ] `On Hand Value (as of)` and `Days of Supply (as of)` exist, verified against
      the reference values.
- [ ] Predictions recorded, misses annotated.
