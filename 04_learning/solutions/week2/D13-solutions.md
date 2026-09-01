# Day 13 — solutions

All figures computed live against the connected model.

---

## Spaced recall answers

1. A periodic snapshot records a balance as of a point in time, repeated at
   intervals; an accumulating snapshot has one row per entity, updated in place as
   it progresses. `FactShipmentMilestone` is **accumulating**.
2. Because it sums the same rotating stock once per snapshot date instead of
   reading the balance at one point in time — with 581 snapshot dates in the
   history, the naive sum is inflated by roughly that same order of magnitude.
3. `-1`. Averaging over it blends real `yyyymmdd` integers with a sentinel that is
   not a date at all, producing a number with no meaning that does not error.
4. `LASTNONBLANK` (finds the most recent date the fact table actually has rows
   for) wrapped in `CALCULATE` (applies that single date as the filter for the
   aggregation).

---

## Exercise 13.1 — SUMMARIZE's extension-column trap

Running the query as given returns:

```
[Bucket]  [Cnt]
High      12000
Low       12000
```

Both buckets return the **same** count — 12,000, all of `DimSku`'s rows, not a
per-bucket count at all — which is the bug: `COUNTROWS(WithClass)` inside the
extension expression is evaluated against the whole `WithClass` table, not the
subset of rows belonging to the current `Bucket` group, so `SUMMARIZE`'s grouping
had no effect on it whatsoever. This is `SUMMARIZE`'s extension-column
context-transition quirk reproducing exactly as described. (`DimSku[SkuKey]` runs
`-1` plus `1..11999`, so the correct, filtered counts are **6,999 High**
(`SkuKey > 5000`, keys 5001-11999) and **5,001 Low** (`SkuKey <= 5000`, keys `-1`
and 1-5000) — roughly a 58/42 split, and the two numbers should differ, which is
the tell that something is wrong with the identical 12,000/12,000 result above.)

The fix — bypass `SUMMARIZE`'s grouping mechanism entirely and filter explicitly:

```dax
EVALUATE
VAR WithClass = ADDCOLUMNS ( VALUES ( DimSku[SkuKey] ), "Bucket", IF ( DimSku[SkuKey] > 5000, "High", "Low" ) )
VAR HighRows = FILTER ( WithClass, [Bucket] = "High" )
VAR LowRows  = FILTER ( WithClass, [Bucket] = "Low" )
RETURN ROW ( "High Cnt", COUNTROWS ( HighRows ), "Low Cnt", COUNTROWS ( LowRows ) )
```

This returns the correct, different counts for each bucket.

**What this means for inherited `SUMMARIZE` code:** any report you inherit that
uses `SUMMARIZE` with extension columns over a *derived* (not base model) table is
suspect until proven otherwise — check its numbers against an independently-built
equivalent before trusting it, especially if every group's aggregate looks
suspiciously identical.

---

## Exercise 13.2 — TREATAS, region grain mismatch

`FactTarget[Region]` values: `Americas, Asia, Europe, MEA, Oceania`.
`DimLocation[TradeRegion]` values: the same five (plus `#NA`) — **exact match.**
`DimLocation[Region]` values: `South Asia, East Asia, SE Asia, N Europe,
Mediterranean, Middle East, N America West, N America East, LatAm West, LatAm
East, Africa, Oceania` — a finer-grained, non-matching set (only `Oceania`
coincides). `TradeRegion` is the bridge; `Region` is a decoy that looks equally
plausible until you actually check it.

**Recomputed live, Americas, June 2025 (`TREATAS` on `TradeRegion`):**

```dax
Actual Schedule Reliability (via TREATAS) :=
CALCULATE (
    DIVIDE ( CALCULATE ( COUNTROWS ( FactPortCall ), FactPortCall[IsOnTimeArrival] = 1 ),
             COUNTROWS ( FactPortCall ) ),
    TREATAS ( VALUES ( DimLocation[TradeRegion] ), FactTarget[Region] )
)
```

| Source | Value |
|---|---|
| Recomputed from `FactPortCall` (376 calls, 249 on time), Americas, June 2025 | **66.22%** |
| `FactTarget`'s stored `ACT` rows, unweighted mean across 7 trade lanes, same scope | **74.71%** |

**They do not match — an 8.5 percentage-point gap.** The tempting first
explanation is the Day 9 averaging trap wearing a new disguise — `FactTarget`
stores one `ACT` row per trade lane, so an unweighted mean across those 7 rows
would give every lane equal vote regardless of call volume, unlike the recomputed
figure which pools all 376 raw port calls. **Check this against the generator
before reporting it, though: it is not what actually produced the gap here.**
`01_generator/meridian/facts_land.py`'s `build_fact_target` sets every
`TargetValue` — for every scenario, `ACT` included — from an independent
`rng.uniform(0.60, 0.98, ...)` draw, with no read of any transactional fact table
at all. `FactTarget`'s `ACT` rows are not an aggregation of real port-call data
by any method, weighted or not; they are a separately-generated planning-system
snapshot with no arithmetic relationship to `FactPortCall` whatsoever, which is
also the honest, complete version of the explanation available before you check
the source: a stored "actual" from a separate system of record is not guaranteed
to reconcile with a live recomputation, and the *specific reason* it doesn't here
turned out to be "unrelated data," not "a real but avoidable weighting choice."
**The lesson to keep**: name a mechanism as the explanation only after you've
checked it produces the gap, not because it's the most recently learned trap that
would explain a gap this shape.

---

## Exercise 13.3 — dynamic ABC vs the static seed

Anchored on 2026-08-20 (the last snapshot date with full SKU coverage — the live
feed's daily appends after this date only touch a handful of SKUs each day, which
is a live-feed simulator characteristic worth knowing about, not a data-quality bug
to chase):

| Class | Dynamic (by on-hand value, 2026-08-20) | Static seed (`AbcClassStatic`, whole `DimSku`) |
|---|---|---|
| A | **269 SKUs** (17.5% of 1,537 stocked SKUs) — **80.0%** of value ($2,406,613,662) | **1,276 SKUs** (10.6% of all 12,000) |
| B | **389 SKUs** (25.3%) — **15.0%** of value ($452,872,936) | **3,509 SKUs** (29.2%) |
| C | **879 SKUs** (57.2%) — **5.0%** of value ($150,514,874) | **7,214 SKUs** (60.1%) |

Total on-hand value at this snapshot: **$3,010,001,472** across 1,537 SKUs that
actually carry stock (of 12,000 SKUs total).

**Two structural reasons these disagree, beyond "the business changed":**

1. **Different populations.** `AbcClassStatic` classifies all 12,000 SKUs in the
   dimension, including ones with zero current on-hand stock. Your dynamic version
   can only classify the 1,537 that actually have inventory on the anchor date —
   an inactive or discontinued SKU can hold a static `A` class from whenever it was
   set, permanently, with nothing in the live data left to re-earn or lose it.
2. **Different bases.** `AbcClassStatic` is a seed value with no documented basis
   in this schema — it could have been set from historical sales velocity, from
   unit cost, from a completely different snapshot date, or by hand. Your dynamic
   version is explicitly anchored to **current on-hand dollar value on one date**.
   Two ABC classifications built on different bases will disagree even on a
   population where both apply — the mismatch alone is not proof either one is
   wrong, but it is proof they are answering different questions, and a report
   that mixes the two without saying so is misleading by omission.

---

## Exercise 13.4 — TREATAS in the wrong direction

```dax
TREATAS ( VALUES ( FactTarget[Region] ), DimLocation[TradeRegion] )
```

This does not error — it runs and returns a **plausible-looking wrong number**,
which is the dangerous outcome, not the safe one. `TREATAS`'s first argument
supplies the *values*; the *columns after it* are what gets filtered. Swapped this
way, whatever `FactTarget[Region]` values are currently in context get applied as
a filter onto `DimLocation[TradeRegion]` — which, since the two columns share the
same five text values, actually "succeeds" at filtering `DimLocation` correctly by
coincidence. The real danger surfaces once you also try to pull a `FactTarget`-side
column (like `TargetValue`) into the same visual: now `FactTarget` itself is
**not** filtered by anything, because the filter direction only ever reached
`DimLocation`, and every row of `FactTarget` looks identical regardless of which
region row you're looking at. Get the direction backwards and the failure mode
is silent, correct-looking numbers on one side of the visual and silently-wrong
identical numbers on the other — exactly the kind of bug that survives a casual
glance at a dashboard.

---

## Reference values used above

| Quantity | Value |
|---|---|
| `FactTarget[Region]` distinct values | Americas, Asia, Europe, MEA, Oceania |
| `DimLocation[TradeRegion]` distinct values | same 5 (+ #NA) |
| `DimLocation[Region]` distinct values | 12 finer sub-regions, does not match `FactTarget[Region]` |
| Live schedule reliability, Americas, Jun 2025 | 66.22% (376 calls, 249 on time) |
| `FactTarget` ACT mean across 7 lanes, Americas, Jun 2025 | 74.71% |
| ABC anchor date | 2026-08-20 |
| Total on-hand value at anchor | $3,010,001,472 |
| Dynamic Class A / B / C counts | 269 / 389 / 879 |
| Dynamic Class A / B / C value share | 80.0% / 15.0% / 5.0% |
| `AbcClassStatic` counts (A/B/C/#NA) | 1,276 / 3,509 / 7,214 / 1 |
