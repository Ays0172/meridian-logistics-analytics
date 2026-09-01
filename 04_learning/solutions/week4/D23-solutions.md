# Day 23: solutions

---

## Spaced recall answers

1. `KEEPFILTERS` makes a `CALCULATE` boolean filter intersect with the visual's
   existing filter on that column instead of replacing it. You need it whenever the
   column you're filtering in `CALCULATE` is one the visual (rows/columns/slicer)
   is already filtering.
2. `Revenue per FFE := DIVIDE(SUM(FactShipment[Revenue_usd]), SUM(FactShipment[Ffe]))`.
   The naive `AVERAGEX` version gives a 0.1-FFE LCL shipment and a 500-FFE FCL
   contract shipment equal weight in the average, which is nonsensical for a rate
   meant to represent dollars per unit of capacity actually sold.
3. `Period` and `TradeRegion` sync safely (every fact table this page or a
   neighbouring page uses relates to `DimDate` and, through it or `DimLocation`,
   to `TradeRegion`). `Mode`, `CustomerSegment`, `Carrier` and `Warehouse` do not
   sync onto every page - Mode specifically breaks on Landside and Warehouse.
4. Schedule reliability, headhaul load factor, backhaul load factor, revenue per
   FFE (or the page's equivalent four) - fixed height matters because the header
   band is meant to look and sit identically across all five pages, so a reader's
   eye lands in the same place switching pages, per Day 22's grid discussion.
5. Backhaul revenue per FFE runs about **0.52x** headhaul (1,286.66 vs. 2,482.78
   USD/FFE). The structural fact: world trade is imbalanced by the geography of
   manufacturing, not by weak backhaul sales effort - there is not enough export
   volume on the return leg to fill the boxes that arrived full.

---

## Exercise 23.1: header cards, reference thresholds

Use **this project's own validation gate** (0.62-0.70 outside the congestion
window), not the generic Sea-Intelligence industry band, for the conditional
formatting thresholds:

```dax
Schedule Reliability Status :=
VAR v = [Schedule Reliability Rolling 8wk]
RETURN
    SWITCH (
        TRUE (),
        v >= 0.62, "Good",
        v >= 0.45, "Watch",
        "Alert"
    )
```

Reasoning: the industry band (55-70%) is a useful sanity check when *validating*
the model, but this dataset's own contract-specified normal range (0.62-0.70) is
tighter and specific to Meridian's own operating pattern - using the wider,
generic band as the dashboard's live threshold would mean the reliability card
could show "Good" even while sitting meaningfully below this network's actual
normal floor. A threshold pulled from someone else's global average, applied to
your own specific operation, under-alerts.

## Exercise 23.2: the scatter, expected result

Sorted ascending by reliability, Rotterdam and Los Angeles during the congestion
window (0.405) do **not** sit at the very top of the list - several low-volume
ports with a handful of calls each post reliability figures at or below that level
purely from small-sample noise, and rank above the two real crisis ports. On the
scatter, Rotterdam and LA appear as two isolated points: low on the y-axis, **far
right** on the x-axis (high call-volume ports, not sparse ones), which is what
makes them visually distinguishable from the noisy low-volume cluster near the
y-axis's low end but with tiny x-values.

**What a sorted-table-only reader misses:** that a metric's reliability as a signal
scales with the population behind it - a "bad number" from three calls and a "bad
number" from 130 calls are not the same finding, and a plain sort collapses that
distinction entirely.

## Exercise 23.3: the combo chart, expected lag

`Avg Waiting for Berth Hours` visibly rises **before** `Demurrage Revenue` inside
the shaded window - typically by roughly a week to ten days in the underlying
weekly series, consistent with the KPI dictionary's own watch-out for
`OCN.OPS.WAIT` ("this is the leading indicator... it degrades before schedule
reliability and demurrage revenue move"). Vessels queue at anchor first; only once
containers are actually discharged late and sit in the yard does demurrage start
accruing against the free-time clock. The lag is the whole reason waiting-for-berth
belongs on an operational early-warning dashboard rather than only a financial one.

## Exercise 23.4: visual justification, reference sentences

1. Header cards: without them, a reader has to read every chart before knowing
   whether today's overall answer is "fine" or "not fine."
2. Reliability trend: without it, a reader sees the current dip with no way to
   judge whether it is new or a known recurring pattern.
3. Reliability-vs-volume scatter: without it, exactly the Day 1 sorting trap
   recurs - a reader reaches for a sorted list and misses the real crisis ports.
4. Headhaul/backhaul revenue per FFE: without it, a reader might flag backhaul
   yield as a problem to "fix," when it is structural and the real question is
   whether it has moved *outside* its normal ~0.52x band.
5. Congestion callout: without it, rising demurrage revenue reads as commercial
   success in isolation - the single most damaging misread this dataset can
   produce.
6. Crane productivity table: without it, "the terminal is slow" has no specific
   terminal or gross-vs-net distinction attached, so nobody knows which lever to
   pull.
7. Rollover trend: without it, the earliest visible warning sign (rollovers
   doubling before reliability visibly craters) is missing from the page entirely.

A visual you cannot write this sentence for honestly (several drafts of this page
initially included a standalone TEU volume trend with no clear decision attached)
should be cut or demoted to drillthrough-only content.
