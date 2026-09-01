# Day 9 — CALCULATE's filter modifiers, and where averaging an average actually hurts

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 70 min · Ship 40 min · Log 15 min

Yesterday was about the two contexts. Today is about the one function that
manipulates filter context deliberately, and about a mistake that is taught as an
absolute rule when it is really a question of degree — a distinction you can
measure in your own data.

---

## Spaced recall (10 min, closed book)

1. What does `CALCULATE` with no filter arguments do, and what is that called?
2. Why does `AVERAGEX(FactShipment, [Some Measure])` behave differently from
   `AVERAGEX(FactShipment, <that measure's expression written out>)`?
3. Name five sources of filter context.
4. Which fact table holds vessel schedule reliability, and which holds delivery
   OTIF? Why are they different numbers?
5. What is the free-time difference between a dry container and a reefer in this
   dataset, and what does that do to their demurrage rates?

---

## Concept

### CALCULATE's anatomy

```dax
CALCULATE ( <expression>, <filter1>, <filter2>, … )
```

The filters are applied first, producing a new filter context, and then the
expression is evaluated in it. Two rules govern what "applied" means:

**Filter arguments REPLACE existing filters on the same column, they do not
intersect with them.** This is the opposite of what most people assume.

```dax
Revenue FCL := CALCULATE ( [Total Revenue], DimMode[ModeCode] = "FCL" )
```

In a matrix with `DimMode[ModeCode]` on rows, the `LCL` row shows the **FCL**
number, not blank. The row's own filter on `ModeCode` was overwritten. If you
wanted intersection you must say so:

```dax
Revenue FCL Kept := CALCULATE ( [Total Revenue], KEEPFILTERS ( DimMode[ModeCode] = "FCL" ) )
```

Now the `LCL` row is blank, because `LCL ∩ FCL` is empty. `KEEPFILTERS` is how you
ask for "and also" instead of "instead of".

**A boolean filter argument is sugar for a table filter.** `DimMode[ModeCode] =
"FCL"` is shorthand for `FILTER(ALL(DimMode[ModeCode]), DimMode[ModeCode] = "FCL")`.
Note the `ALL` in there — that is where the replacing behaviour comes from, and
seeing it explains the rule rather than making you memorise it.

### The filter modifiers, and what each is actually for

| Modifier | What it does | Use it when |
|---|---|---|
| `REMOVEFILTERS(t)` | clears filters from a table or columns | you want a denominator that ignores the current slice |
| `ALL(t)` | same as `REMOVEFILTERS` in a `CALCULATE` filter slot | legacy spelling; `REMOVEFILTERS` says what it means |
| `ALLEXCEPT(t, c…)` | clears everything on `t` except the named columns | percentage within a parent group |
| `ALLSELECTED(t)` | clears filters from *inside* the visual but keeps what the user selected outside it | "% of visual total" that respects slicers |
| `KEEPFILTERS(f)` | intersects instead of replacing | adding a condition on a column the visual already filters |
| `USERELATIONSHIP(a, b)` | activates an inactive relationship for this evaluation | role-playing dimensions |
| `CROSSFILTER` | changes filter direction for this evaluation | narrow, deliberate many-to-many |

`ALL` versus `ALLSELECTED` is the pair people get wrong, and the difference only
appears when a slicer is present. `ALL` gives you the whole table, ignoring the
user's slicer entirely. `ALLSELECTED` gives you what the user's slicer left,
ignoring only the visual's own row and column filters. A "% of total" built with
`ALL` will not add to 100% inside a slicer-filtered page; one built with
`ALLSELECTED` will. Neither is wrong — they answer different questions — but only
one matches what a reader assumes when they see a percentage column.

### Now the interesting part: averaging an average

The rule you have been taught is "never average an average". It is good advice and
it is imprecise, which makes it hard to apply under pressure. Let us make it exact
and then measure it.

Two ways to compute a per-unit ratio over a group:

```dax
-- POOLED (almost always what you want)
Lines Per Labour Hour := DIVIDE ( SUM ( FactWarehouseTask[LinesProcessed] ),
                                  SUM ( FactWarehouseTask[LabourHours] ) )

-- UNWEIGHTED MEAN OF PER-ROW RATIOS (almost always wrong)
LPH Naive := AVERAGEX ( FactWarehouseTask,
                        DIVIDE ( FactWarehouseTask[LinesProcessed],
                                 FactWarehouseTask[LabourHours] ) )
```

The pooled version weights each row by its denominator. The naive version gives a
task that took six minutes the same vote as one that took four hours.

`Revenue per FFE` needs one more thing the pattern above doesn't show, because
`FactShipment` mixes populations in a way `FactWarehouseTask` doesn't: air
shipments carry real `Revenue_usd` but always `Ffe = 0` (an air consignment isn't a
container), so a plain `SUM(Revenue_usd) / SUM(Ffe)` puts air revenue on top of
ocean containers — mathematically well-formed, silently wrong. The scope has to be
made explicit on **both** sides of the ratio:

```dax
-- POOLED, scope-restricted to container traffic
Revenue per FFE :=
CALCULATE (
    DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) ),
    KEEPFILTERS ( FactShipment[Ffe] > 0 )
)

-- UNWEIGHTED MEAN OF PER-ROW RATIOS (DIVIDE returns blank on air rows,
-- and AVERAGEX skips blanks, so this one restricts itself automatically)
Revenue per FFE Naive := AVERAGEX ( FactShipment,
                                    DIVIDE ( FactShipment[Revenue_usd], FactShipment[Ffe] ) )
```

`KEEPFILTERS` matters here for the same reason it mattered above: the restriction
should intersect with whatever a visual is already filtering, not replace it.

**How far apart they land depends on the correlation between the per-row ratio and
its own denominator.** If small denominators come with large ratios, the naive
average over-weights the inflated ones and reads high. If the ratio is unrelated
to the denominator, the two answers nearly agree.

You can see both cases in Meridian, and the numbers are in today's solutions:

| Measure | corr(ratio, denominator) | Naive error |
|---|---|---|
| Lines per labour hour | strongly negative | badly wrong |
| Revenue per FFE | essentially zero | nearly right |

Short tasks are efficient per hour, long tasks are not — so lines-per-hour and
labour-hours move against each other, and the naive average is out by roughly a
fifth. Freight rate per FFE, by contrast, does not systematically depend on how
many FFE are on the booking, so the naive average lands within **0.01%** of the
pooled figure — as close to "doesn't matter" as this dataset ever gets, precisely
because `corr(ratio, denominator) ≈ 0` here. (A *different* averaging mistake on
this same measure — an unweighted mean across trade lanes, rather than across
individual shipments — does move the number by about two percent; that's a
separate exercise later this week, not this row-level comparison.)

This is worth internalising for two reasons. First, it tells you *where to look*:
the ratios most corrupted by naive averaging are the ones whose denominator is a
measure of effort or duration, because effort and efficiency are almost always
inversely related. Second, it is a much better interview answer. "Never average an
average" is a slogan. "The error scales with the correlation between the ratio and
its denominator, which is why productivity metrics are the dangerous ones and
freight rates mostly are not" is an answer from someone who has actually looked.

**Always write the pooled version.** The point of measuring the gap is not to
license the naive one; it is to know which numbers on somebody else's dashboard to
distrust first.

### Percentages at four different scopes

The same "% of total" reads four different ways depending on the denominator's
filter context. Build all four today and keep them; you will need each one in the
dashboards.

```dax
Revenue := SUM ( FactShipment[Revenue_usd] )

-- of everything, ignoring every filter including the user's slicers
Pct of Grand Total :=
DIVIDE ( [Revenue], CALCULATE ( [Revenue], REMOVEFILTERS ( ) ) )

-- of what the visual is showing, respecting slicers outside it
Pct of Visual Total :=
DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALLSELECTED ( ) ) )

-- of the parent trade lane, whatever else is filtered
Pct of Trade Lane :=
DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALLEXCEPT ( DimService, DimService[TradeLane] ) ) )

-- of this customer's own total, across all lanes and dates
Pct of Customer :=
DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALLEXCEPT ( DimCustomer, DimCustomer[CustomerCode] ) ) )
```

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 9.1 — replacement, not intersection (10 min)
Build `Revenue FCL` and `Revenue FCL Kept` as above. Put `DimMode[ModeCode]` on
rows with `Revenue`, `Revenue FCL`, `Revenue FCL Kept`. Predict all three columns
for the `LCL` row and the `AIR` row before running. Explain the difference in one
sentence.

### Exercise 9.2 — the four percentages (20 min)
Build all four percentage measures. Put `TradeLane` on rows and add a
`DimDate[Year]` slicer set to 2025. Predict, for one lane:
- which of the four columns sum to 100% down the visual,
- which change when you move the slicer to 2024,
- which stay identical.

Then verify. Write down which measure you would use for a report where the reader
expects the percentage column to add up, and why.

### Exercise 9.3 — the averaging trap, measured (25 min)
Build the pooled and naive versions of **both**:
```dax
Lines Per Labour Hour       -- pooled
LPH Naive                   -- AVERAGEX of per-row ratios
Revenue per FFE             -- pooled
Revenue per FFE Naive       -- AVERAGEX of per-row ratios
```
Predict, for each pair, whether the gap will be large or small, and which
direction the naive one will err. Then compute all four at the grand total.

Now explain the difference between the two pairs. If your explanation is "one is
warehouse data and one is ocean data", you have described it rather than explained
it — keep going until your answer mentions the denominator.

Finally, compute the correlation that drives it. In DAX that is awkward, so do it
in Python against the Parquet — that is a legitimate part of the job, and
cross-checking DAX against pandas is a habit worth building:

```python
import pandas as pd, numpy as np
wt = pd.read_parquet('02_data/raw/FactWarehouseTask',
                     columns=['LinesProcessed','LabourHours'])
print(np.corrcoef(wt.LinesProcessed / wt.LabourHours, wt.LabourHours)[0,1])
```

### Exercise 9.4 — ALL versus ALLSELECTED under a slicer (15 min)
With `TradeLane` on rows and a `Year` slicer, add:
```dax
Pct All := DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALL ( ) ) )
Pct AllSelected := DIVIDE ( [Revenue], CALCULATE ( [Revenue], ALLSELECTED ( ) ) )
```
Predict both columns' totals with the slicer on 2025, then with it cleared. One of
the four numbers is 100% in both states; predict which before checking.

---

## Ship

Add to `_Measures`, in a display folder `02 Ratios`: the four percentage measures,
`Lines Per Labour Hour`, `Revenue per FFE`, and both naive variants **named
explicitly as naive** so nobody ever picks one up by accident:

```dax
[DO NOT USE] LPH Naive := ...
```

Add a short note to `06_portfolio/notes-averaging.md` recording the two
correlations and the two error sizes you measured. That paragraph is an interview
answer you now own.

```
git add .
git commit -m "Day 9: CALCULATE modifiers, four percentage scopes, averaging trap measured"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can state, without notes, why a `CALCULATE` boolean filter replaces
      rather than intersects, and what `KEEPFILTERS` changes.
- [ ] You can say when `ALLSELECTED` is the right denominator and when `ALL` is.
- [ ] You measured both averaging gaps and can explain the mechanism in terms of
      the correlation between ratio and denominator — not in terms of which
      business area the data came from.
- [ ] All four percentage measures exist and you know which one a reader expects.
- [ ] Predictions recorded, misses annotated.
