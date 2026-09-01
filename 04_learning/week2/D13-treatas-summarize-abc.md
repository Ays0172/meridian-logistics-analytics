# Day 13 — Virtual relationships with TREATAS, SUMMARIZE for grouping, and ABC segmentation

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 75 min · Ship 30 min · Log 15 min

Every relationship you have used so far already exists in the model as a physical
line between two tables. Today's tools are for the case where the relationship you
need **cannot** be physical — either because the model would cycle, or because the
two tables simply do not share a key at any common grain — and for turning a raw
column into a business-meaningful category with DAX instead of a spreadsheet.

---

## Spaced recall (10 min, closed book)

1. What is the difference between a periodic snapshot and an accumulating
   snapshot, and which one is `FactShipmentMilestone`?
2. Why does a plain `SUM` of `FactInventorySnapshot[OnHandValueUsd]` with no date
   filter return a number roughly 500× too large?
3. What sentinel value marks a milestone date that has not happened yet, and what
   does averaging over it silently do to a duration measure?
4. Name the two DAX functions used to build the point-in-time inventory measure,
   and what each one is doing.

---

## Concept

### The problem `FactTarget` creates

`FactTarget` holds budget/forecast/plan/actual figures for 16 of the 72 KPIs, at
**KPI × region × month × scenario** grain — a completely different shape from every
other fact table in this model. Look at its actual columns:

```
TargetMonthDateKey, ScenarioKey, KpiCode, KpiName, Region, TradeLane, ModeKey,
WarehouseKey, CurrencyKey, TargetValue, StretchValue, ThresholdValue
```

`ModeKey`, `WarehouseKey`, `CurrencyKey` and `TargetMonthDateKey` are real foreign
keys with real relationships to `DimMode`, `DimWarehouse`, `DimCurrency`,
`DimDate` — you could filter this table the ordinary way on any of those. But
`Region` and `TradeLane` are **plain text columns**, not foreign keys, and there is
**no relationship** from `FactTarget` to `DimLocation` or `DimService` at all.

This is deliberate, not an oversight: `FactTarget` is set at a coarse **monthly,
region-level** grain (targets are planned per macro-region, not per port), while
the transactional facts you would compare it against run at **daily, per-location**
grain. There is no single physical relationship that correctly connects a table
keyed on `(Region, Month)` to one keyed on `(LocationKey, Date)` — a physical
relationship needs a shared column at a shared grain, and these tables share
neither.

**`DimLocation[TradeRegion]` is the bridge.** Check it yourself:
`FactTarget[Region]` takes exactly five values — `Americas`, `Asia`, `Europe`,
`MEA`, `Oceania`. `DimLocation[TradeRegion]` takes exactly the same five (plus a
`#NA` for the unknown-member row). `DimLocation[Region]` — a different, finer-grain
column on the same table — does **not** match (`N America West`, `LatAm East`,
`South Asia`, and so on), which is worth noticing on its own: two columns on one
dimension table can encode the same real-world concept at two different
granularities, and only one of them is the one you want for a given comparison.
Confirm this yourself in Power Query or with `DISTINCT` before building anything —
guessing which column matches, instead of checking, is how this exercise goes
wrong quietly.

### TREATAS: propagating a filter across tables with no relationship

```dax
TREATAS ( <table>, <column1>, <column2>, … )
```

`TREATAS` takes the values currently in `<table>`'s columns and applies them **as
if** they were a filter directly on `<column1>`, `<column2>`, … — even though no
relationship connects them. It is a virtual relationship, built for the duration of
one `CALCULATE`, not a change to the model.

```dax
Actual Schedule Reliability (Target's Regions) :=
CALCULATE (
    [Schedule Reliability Rolling 8wk],
    TREATAS ( VALUES ( DimLocation[TradeRegion] ), FactTarget[Region] )
)
```

Read this as: "take whatever `TradeRegion` values are visible right now (from
wherever the filter context came from — a slicer, a row, a `CALCULATE`), and treat
them as a filter on `FactTarget[Region]`." Put a `FactTarget[Region]` column on
rows in a matrix, and every row now filters `DimLocation` — and everything
downstream of `DimLocation` — as if a real relationship existed.

The direction matters. `TREATAS(VALUES(A[col]), B[col])` filters **B** using
**A**'s current values. Get the two arguments backwards and you filter the wrong
table, silently — no error, just a query that is not actually comparing what you
think it's comparing.

### SUMMARIZE, and why it is not your grouping tool of first choice

```dax
SUMMARIZE ( <table>, <groupBy1>, <groupBy2>, …, "<name>", <expression>, … )
```

`SUMMARIZE` groups a table by one or more columns and can add aggregation columns.
It has a well-known trap: the aggregation-column arguments do not always respect
row context the way you'd expect from a table built manually elsewhere (you will
prove this to yourself in Exercise 13.1). Since 2015, `SUMMARIZECOLUMNS` has been
the recommended tool for the ordinary "group and aggregate" job — it is what visual
queries generate under the hood, it handles blank-row removal correctly, and it
does not have `SUMMARIZE`'s extension-column quirks. Reach for `SUMMARIZE` today
mainly to understand it (you will see it in older code you inherit), and use
`SUMMARIZECOLUMNS` or `ADDCOLUMNS(VALUES(...), ...)` for anything you write going
forward.

### ABC segmentation: turning a ranked list into a business category

The mechanism: rank rows by a value, compute the running (cumulative) share of the
total as you walk down the ranking, and classify by which cumulative-share band
each row falls into — conventionally A = top ~80% of value, B = next ~15%, C = the
remaining ~5%.

```dax
VAR Ranked =
    ADDCOLUMNS (
        SkuTotals,
        "Rank", RANKX ( SkuTotals, [Value],, DESC, DENSE )
    )
VAR WithCumulative =
    ADDCOLUMNS (
        Ranked,
        "CumulativeValue",
            VAR ThisRank = [Rank]
            RETURN SUMX ( FILTER ( Ranked, [Rank] <= ThisRank ), [Value] )
    )
```

Note the `VAR ThisRank = [Rank]` before the inner `FILTER` — capturing the outer
row's value in a variable *before* entering a nested row context is the safe,
readable substitute for `EARLIER()`, which does the same job but reads worse once
you're several row contexts deep. Both exist; use the `VAR` form in anything you
write from today.

This pattern is quadratic (every row re-scans every row at-or-above its own rank) —
fine for a few thousand SKUs computed once, not something to iterate per-visual
over a million-row fact table. That is a genuine engineering constraint, not a
theoretical one, and it is why ABC class is usually materialized as a calculated
column refreshed on load, not recomputed as a measure on every slicer click.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 13.1 — SUMMARIZE's extension-column trap (15 min)
Build this and look closely at the result:
```dax
EVALUATE
VAR WithClass = ADDCOLUMNS ( VALUES ( DimSku[SkuKey] ), "Bucket", IF ( DimSku[SkuKey] > 5000, "High", "Low" ) )
RETURN SUMMARIZE ( WithClass, [Bucket], "Cnt", COUNTROWS ( WithClass ) )
```
Predict the two `Cnt` values before running. If they come back identical (not the
real, different-per-bucket counts), you have reproduced the exact trap this section
warned about — `SUMMARIZE`'s extension expression did not get filtered by the
group the way you'd assume. Rewrite it using two explicit `FILTER`+`COUNTROWS`
expressions in a `ROW()` instead, and confirm you now get the right, different
counts for each bucket. Write one sentence on what this means for any `SUMMARIZE`
you inherit from someone else's report.

### Exercise 13.2 — TREATAS, region grain mismatch (25 min)
Confirm for yourself, with `DISTINCT`, that `FactTarget[Region]` matches
`DimLocation[TradeRegion]` and not `DimLocation[Region]`. Then build
`Actual Schedule Reliability (via TREATAS)` as shown above, and put it beside
`FactTarget`'s own stored `ACT`-scenario value for `KpiCode = "OCN.REL.SCHED"`,
`TradeRegion = "Americas"`, June 2025. Predict, before checking, whether they will
match exactly, be close, or differ meaningfully — and why a recomputed-from-source
number and a separately-recorded "actuals" row in a planning table might not agree
even when both are "correct."

### Exercise 13.3 — dynamic ABC vs the static seed (25 min)
`DimSku[AbcClassStatic]` already holds a class per SKU. Build a dynamic version
instead, ranking SKUs by `SUM(FactInventorySnapshot[OnHandValueUsd])` **at one
snapshot date** — reuse Day 12's point-in-time pattern, this is exactly why you
needed it. Use `2026-08-20`, the most recent snapshot date with full SKU coverage
(check this yourself — not every date since has it, which is itself worth noticing
and is not something you need to explain today).

Predict the three class counts and their share of total value before running.
Then compare against `AbcClassStatic`'s counts. They will not match closely — name
two structural reasons they wouldn't, beyond "the business changed since the seed
was set" (hint: what does `AbcClassStatic` classify that your dynamic version
doesn't, and vice versa?).

### Exercise 13.4 — TREATAS in the wrong direction (10 min)
Swap the two arguments in your Exercise 13.2 measure:
`TREATAS(VALUES(FactTarget[Region]), DimLocation[TradeRegion])`. Predict what
happens before running — will it error, return blank, or return a plausible-looking
wrong number? Explain why, in terms of which table ends up filtered.

---

## Ship

Add to `_Measures`, display folder `04 Targets & Segmentation`:
`Actual Schedule Reliability (via TREATAS)`, with a description noting the
`TradeRegion`-not-`Region` gotcha explicitly, so the next person building a
target-vs-actual measure for a *different* KPI doesn't have to rediscover it.

Add `SkuAbcClassDynamic` as a genuine calculated column on `DimSku` (not a
measure — per the concept section, this one belongs materialized), using the
2026-08-20 snapshot as the basis, with a comment noting the date is a deliberate
anchor, not the current date, and will need revisiting as the live feed advances.

```
git add .
git commit -m "Day 13: TREATAS virtual relationship, SUMMARIZE trap, dynamic ABC shipped"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can explain, without notes, why `FactTarget` cannot have a physical
      relationship to `DimLocation`, and which column actually bridges them.
- [ ] You reproduced `SUMMARIZE`'s extension-column trap yourself and know to
      reach for `SUMMARIZECOLUMNS`/`ADDCOLUMNS(VALUES(...))` instead.
- [ ] `Actual Schedule Reliability (via TREATAS)` exists and you can state, from
      your own numbers, how it compares to `FactTarget`'s stored actual.
- [ ] `SkuAbcClassDynamic` exists as a calculated column, and you can name two
      structural reasons it disagrees with the static seed.
- [ ] Predictions recorded, misses annotated.
