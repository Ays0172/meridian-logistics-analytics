# Day 10 — Iterators, variables, and getting a weighted average right

> Time: 2.5 h · Spaced recall 10 min · Concept 35 min · Drill 65 min · Ship 45 min · Log 15 min

Yesterday you measured what goes wrong when a ratio is averaged unweighted. Today
you build the tools to do it properly, and to rank, segment and compare — which is
most of what a commercial dashboard does.

---

## Spaced recall (10 min, closed book)

1. Why does a `CALCULATE` boolean filter replace rather than intersect, and what
   restores intersection?
2. Which of `ALL` and `ALLSELECTED` gives a percentage column that sums to 100%
   inside a slicer-filtered page?
3. What quantity predicts how badly an unweighted average of a ratio will err?
4. Which two of these three agree: `SUM(col)`, `SUMX(table, col)`,
   `AVERAGEX(table, [SomeMeasure])`?
5. Name the two fact tables that carry an on-time flag, and what each one's promise
   is measured against.

---

## Concept

### The iterator family, and what distinguishes them

Every `X` function takes a table and an expression, establishes a row context over
the table, evaluates the expression per row, and aggregates the results.

| Function | Aggregates by | Reach for it when |
|---|---|---|
| `SUMX` | sum | you need a row-level product or ratio summed |
| `AVERAGEX` | mean | you genuinely want the mean of per-row values |
| `MINX` / `MAXX` | min / max | earliest, latest, largest single row |
| `COUNTX` / `COUNTAX` | count of non-blanks | counting rows where an expression resolves |
| `RANKX` | rank | ordering members against each other |
| `CONCATENATEX` | text join | listing selected members in a title |
| `FILTER` | *returns a table* | narrowing the row set for another function |

`FILTER` is the odd one out: it does not aggregate, it returns a table. That makes
it the plumbing for everything else.

### The one that matters most: SUMX for row-level products

Some quantities cannot be computed from aggregates because the arithmetic has to
happen per row before summing. The canonical case is a weighted total where the
weight lives on the same row:

```dax
-- WRONG: multiplies two independent sums
Bad Weight := SUM ( FactShipment[ContainerCount] ) * SUM ( DimEquipment[TeuFactor] )

-- RIGHT: multiplies per row, then sums
Total TEU Recomputed :=
SUMX ( FactShipment, FactShipment[ContainerCount] * RELATED ( DimEquipment[TeuFactor] ) )
```

The wrong version multiplies a count of containers by a sum of TEU factors across
the whole equipment dimension — a number with no meaning. The right version does
the multiplication in each row's own context, where both values belong together.

**Rule of thumb: if the calculation involves two columns multiplied or divided
together, and the answer must respect each row's own pairing, you need an
iterator.** Sum-then-multiply and multiply-then-sum are different numbers, and only
one of them is the one you want.

### `RELATED` and `RELATEDTABLE`

Inside a row context on the many side of a relationship, `RELATED(dim[col])`
fetches the matching value from the one side. It only works in a row context, and
only in the many-to-one direction.

Going the other way, `RELATEDTABLE(fact)` returns the fact rows related to the
current dimension row — it is `CALCULATETABLE` with context transition, so it
carries the same implicit filtering you learned on Day 8.

### Variables: correctness, not just tidiness

```dax
Revenue per FFE :=
VAR Revenue = SUM ( FactShipment[Revenue_usd] )
VAR Ffe     = SUM ( FactShipment[Ffe] )
RETURN
    DIVIDE ( Revenue, Ffe )
```

Three things variables buy you:

1. **Each `VAR` is evaluated once**, in the filter context where it is declared, and
   reused. Repeating an expensive expression twice can double the query cost.
2. **A `VAR` is evaluated where it is written, not where it is used.** This is the
   subtle one. If you declare a variable outside a `CALCULATE` and reference it
   inside, it keeps the *outer* context — which is how you capture "the value
   before I changed the filter". That is the whole technique behind
   comparison measures.
3. **Readability that survives debugging.** A named intermediate you can `RETURN`
   on its own is how you find which half of a ratio is wrong.

The classic use of point 2:

```dax
Rank Within Lane :=
VAR ThisRevenue = [Total Revenue]          -- captured in the current row's context
RETURN
    COUNTROWS (
        FILTER (
            CALCULATETABLE ( VALUES ( DimService[ServiceCode] ),
                             ALLEXCEPT ( DimService, DimService[TradeLane] ) ),
            [Total Revenue] > ThisRevenue
        )
    ) + 1
```

`ThisRevenue` is frozen before the filter context is widened, so the comparison is
"this service against its siblings" rather than against itself.

### `DIVIDE` versus `/`

Always `DIVIDE`. `/` returns infinity or an error on a zero denominator and
propagates it into every total that touches it; `DIVIDE` returns blank, or a third
argument you supply. Blank is almost always the right answer for "no denominator" —
a ratio with nothing underneath it is not zero, it is undefined, and blank is how
you say that to a visual.

The one case for a third argument is when zero genuinely is the answer:

```dax
Deadhead Pct := DIVIDE ( SUM ( FactTransportLeg[EmptyKm] ),
                         SUM ( FactTransportLeg[DistanceKm] ), 0 )
```

A leg with no distance ran no empty kilometres either, so zero is honest there.

### `SELECTEDVALUE` and `HASONEVALUE`

Reading the current selection is how a measure becomes context-aware:

```dax
Rate Basis Label :=
VAR Mode = SELECTEDVALUE ( DimMode[ModeCode] )
RETURN
    SWITCH ( Mode,
        "AIR", "Chargeable weight, 1:6000 divisor",
        "LCL", "Revenue tons, 1:1000 rule",
        "FCL", "Per container",
        "Mixed modes — select one"
    )
```

`SELECTEDVALUE(col)` returns the single visible value, or blank when there are
several. `HASONEVALUE(col)` is the test on its own, for when you want to guard a
calculation rather than label it. Use them to make a measure refuse to answer a
question that does not make sense at the current grain, instead of quietly
returning a number that looks fine.

---

## Drill

Predictions in `predictions.md` first, as always.

### Exercise 10.1 — sum-then-multiply versus multiply-then-sum (15 min)
Build `Bad Weight` and `Total TEU Recomputed` as above. Compare
`Total TEU Recomputed` against the stored `SUM(FactShipment[Teu])`. Predict whether
they match exactly, approximately, or not at all — and predict the order of
magnitude of `Bad Weight` before you look.

Then explain why `Total TEU Recomputed` and `SUM(FactShipment[Teu])` should agree,
and what it would mean about the data if they did not.

### Exercise 10.2 — the correct weighted rate, three ways (20 min)
Compute revenue per FFE three ways at the grand total and by trade lane:
```dax
RPF Pooled  := DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) )
RPF SumX    := DIVIDE ( SUMX ( FactShipment, FactShipment[Revenue_usd] ),
                        SUMX ( FactShipment, FactShipment[Ffe] ) )
RPF Naive   := AVERAGEX ( FactShipment, DIVIDE ( FactShipment[Revenue_usd], FactShipment[Ffe] ) )
```
Predict which two agree and which is the odd one out. Then predict what happens to
`RPF Naive` specifically on **air freight rows**, where `Ffe = 0` — and check
whether `DIVIDE`'s blank changes the `AVERAGEX` result.

That last part is the exercise. Work out whether blanks are skipped or counted as
zero, and what that does to your number.

### Exercise 10.3 — rank the lanes two ways (20 min)
```dax
Lane Rank by Yield :=
RANKX ( ALL ( DimService[TradeLane] ), [Revenue per FFE], , DESC, DENSE )

Lane Rank by Revenue :=
RANKX ( ALL ( DimService[TradeLane] ), [Total Revenue], , DESC, DENSE )
```
Put `TradeLane` on rows with revenue, revenue per FFE, and both ranks. Predict
before running: **which lane is first by yield but not first by revenue?** Then
write one sentence on which ranking a trade manager should be shown first, and why.

### Exercise 10.4 — guard a measure against the wrong grain (15 min)
Build `Rate Basis Label`. Put it on a card with no slicer, then with
`DimMode[ModeCode]` on rows. Predict both. Then build a measure that *refuses* to
compute rather than mislabel:
```dax
Chargeable Weight Basis :=
IF ( NOT HASONEVALUE ( DimMode[ModeCode] ),
     "Select a single mode",
     [Rate Basis Label] )
```
Explain when a blank or a refusal is a better answer than a number.

### Exercise 10.5 — variables that capture the outer context (15 min)
Build `Rank Within Lane` as written in the concept section. Then break it
deliberately: move `VAR ThisRevenue = [Total Revenue]` so it is declared *inside*
the `FILTER`. Predict what every row now shows before you run it. The answer tells
you exactly what "a variable is evaluated where it is written" means.

---

## Ship

Add to `_Measures` in display folder `03 Iterators`: `Total TEU Recomputed`,
`RPF Pooled`, `Lane Rank by Yield`, `Lane Rank by Revenue`,
`Chargeable Weight Basis`, `Rank Within Lane`.

Delete `Bad Weight` and `RPF Naive` once you have recorded their values in
`predictions.md` — you have learned what they teach, and leaving a wrong measure in
a model is how it ends up on a report.

```
git add .
git commit -m "Day 10: iterators, RELATED, variables, weighted rates, ranking"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can explain why sum-then-multiply and multiply-then-sum differ, and name
      a case from this data where it matters.
- [ ] You know what `DIVIDE` returns on a zero denominator and why blank beats zero
      there — and you have checked what `AVERAGEX` does with those blanks.
- [ ] You can state where a `VAR` is evaluated, and you have proved it by breaking
      `Rank Within Lane`.
- [ ] You can name the lane that ranks first by yield but not by revenue.
- [ ] Predictions recorded, misses annotated.
