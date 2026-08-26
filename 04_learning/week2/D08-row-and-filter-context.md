# Day 8 — Row context, filter context, and the transition between them

> Time: 2.5 h · Spaced recall 10 min · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

This is the first day of the week that fixes the gap you named. Nothing visual gets
built for the next six days. That is deliberate: every measure in every dashboard
you build in Weeks 3 to 5 rests on what you learn now, and the fastest way to
waste those weeks is to start them without this.

---

## Spaced recall (10 min, closed book)

1. State the grain of `FactContainerMove` in one sentence.
2. Which of the three fact types is `FactInventorySnapshot`, and what breaks if you
   `SUM` its `OnHandUnits` across a date range?
3. What is the difference between a master and a house bill of lading?
4. Why is `-1` used as the unknown member rather than null?
5. Which two `FactShipment` columns would you use to compute schedule reliability,
   and why would that be the wrong table for it?
6. In ISO 6346, what does the fourth character of the owner prefix denote?

---

## Concept

### The two contexts, stated precisely

DAX evaluates every expression inside an **evaluation context**. There are exactly
two kinds, and almost every confusing result in Power BI comes from misreading
which one is active.

**Row context** is "the current row". It exists inside a calculated column and
inside the second argument of any iterator (`SUMX`, `AVERAGEX`, `FILTER`,
`RANKX`, …). When a row context is active, a bare column reference such as
`FactShipment[Revenue_usd]` means *the value in this row*.

**Filter context** is "the set of rows currently visible". It is created by
visuals, slicers, page filters, report filters, rows and columns of a matrix, and
by `CALCULATE`. When only a filter context is active, a bare column reference is
**not** a single value and DAX cannot evaluate it — which is why

```dax
Wrong Revenue := FactShipment[Revenue_usd]
```

fails as a measure but works fine as a calculated column. The measure has no row
context to resolve the reference against.

That single fact explains a large fraction of "why does this work in a column but
not in a measure" confusion.

### Aggregations create their own row context

```dax
Total Revenue := SUM ( FactShipment[Revenue_usd] )
```

`SUM` is shorthand. Internally it iterates the rows visible in the current filter
context, creating a row context for each, reads the column, and adds them up.
`SUM(X)` is exactly `SUMX(FactShipment, FactShipment[Revenue_usd])`. Knowing they
are the same thing is what makes the next section make sense.

### Context transition: the one mechanism worth memorising

Row context does **not** filter. This surprises everyone once.

Suppose you write a calculated column on `DimCustomer`:

```dax
-- calculated column on DimCustomer
Revenue Wrong = SUM ( FactShipment[Revenue_usd] )
```

You are in a row context — one customer per row — and you might expect that
customer's revenue. You get **total revenue for every customer**, the same number
repeated 4,171 times. The row context knows which customer row you are on, but it
does not restrict what `SUM` can see. Nothing has filtered `FactShipment`.

To make the row context act as a filter you must ask for it:

```dax
-- calculated column on DimCustomer
Revenue Right = CALCULATE ( SUM ( FactShipment[Revenue_usd] ) )
```

`CALCULATE` with no filter arguments looks pointless. It is the most important
`CALCULATE` in DAX. It performs **context transition**: it takes every column of
the current row context and converts them into filter context. Now the row
context's customer becomes a filter on `DimCustomer[CustomerKey]`, that filter
propagates down the relationship to `FactShipment`, and `SUM` sees only that
customer's rows.

Two things follow, and both matter more than they look:

**1. A measure referenced inside an iterator has an invisible `CALCULATE` around
it.** This is why

```dax
Margin per Shipment := AVERAGEX ( FactShipment, [Gross Margin Pct] )
```

works at all. `[Gross Margin Pct]` is a measure; inside `AVERAGEX`'s row context
it is implicitly wrapped in `CALCULATE`, so context transition fires per row and
each row gets its own margin. Replace the measure reference with its definition
written out longhand and remove the wrapper, and you get the same number
repeated.

**2. Context transition transitions ALL columns of the row context, not just the
ones you were thinking about.** Iterating `FactShipment` and calling a measure
transitions every column of that fact row — including columns you never
mentioned. On a table with a unique key per row, that filters down to exactly one
row, which is usually what you want but is worth knowing when it isn't.

### Filter context comes from more places than you think

In descending order of how often people forget them:

- the visual's own rows, columns, and legend
- slicers on the page
- filters on the visual, page, report, or applied by a drill-through
- `CALCULATE` filter arguments in the measure itself
- **row-level security**, which is invisible in the report but absolutely present
- context transition from a surrounding iterator
- cross-filtering from another visual's selection

A number that "looks wrong" is almost always right for a filter context that
differs from the one in your head. The skill being trained this week is reading
the actual context rather than the intended one.

### Why predicting matters more than running

For the rest of this week, every drill asks you to write down your predicted
answer *before* you run it. This is not busywork and it is not about being right.
Being wrong on paper is the moment the mechanism becomes visible; being right in
the visual teaches you nothing about why. If you run first and rationalise after,
you will finish the week able to produce measures that happen to work and unable
to fix one that doesn't — which is precisely the state you said you want out of.

---

## Drill

Work in a new Power BI file over your Week 1 model, or in DAX Studio against it.
Create a blank page with a single table visual and no slicers, so you control the
filter context completely.

**For every exercise: write your prediction in `04_learning/week2/predictions.md`
BEFORE you run anything.** Note whether you were right, and if not, what you had
misread.

### Exercise 8.1 — the failing measure (5 min)
Create `Bad Revenue := FactShipment[Revenue_usd]`. Predict what happens. Then
create it and read the error message carefully — it names the missing thing.
State in your own words which context is absent.

### Exercise 8.2 — SUM is SUMX (10 min)
Create both:
```dax
Revenue A := SUM ( FactShipment[Revenue_usd] )
Revenue B := SUMX ( FactShipment, FactShipment[Revenue_usd] )
```
Put both in a table with `DimService[TradeLane]` on rows. Predict whether they
differ anywhere. Then check.

### Exercise 8.3 — the repeated-total column (15 min)
Add a **calculated column** to `DimCustomer`:
```dax
Cust Revenue No Calc = SUM ( FactShipment[Revenue_usd] )
```
Predict what you will see. Then add a second column:
```dax
Cust Revenue With Calc = CALCULATE ( SUM ( FactShipment[Revenue_usd] ) )
```
Predict again before refreshing. Put `CustomerCode` and both columns in a table.
Explain the difference out loud before reading the solution.

### Exercise 8.4 — the same trick in a measure (10 min)
```dax
Customers Above 1M :=
COUNTROWS (
    FILTER (
        VALUES ( DimCustomer[CustomerCode] ),
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ) ) > 1000000
    )
)
```
Predict the value at the grand total. Then remove the `CALCULATE` and predict
again before running. One of the two answers is a number that tells you
immediately that context transition is missing — work out which and why.

### Exercise 8.5 — implicit CALCULATE around a measure (10 min)
Create:
```dax
Gross Margin Pct := DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), SUM ( FactShipment[Revenue_usd] ) )
Avg Margin Per Shipment := AVERAGEX ( FactShipment, [Gross Margin Pct] )
Avg Margin Longhand := AVERAGEX ( FactShipment, DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), SUM ( FactShipment[Revenue_usd] ) ) )
```
Predict which two of the three agree. Run it. The one that differs is the whole
lesson of today.

### Exercise 8.6 — count the contexts (10 min)
For each of these, list every source of filter context acting on the highlighted
number:
1. A card visual showing `Total Revenue`, with a `DimDate[Year]` slicer set to 2025.
2. The same card, viewed by a user assigned an RLS role limiting them to South Asia.
3. A cell in a matrix with `TradeLane` on rows, `Year` on columns, inside a
   measure that itself calls `CALCULATE(..., DimMode[ModeCode] = "FCL")`.

---

## Ship

Create `04_learning/week2/predictions.md` with today's six predictions, your
actual results, and a one-line note on each miss.

Create a measure table in your model (a blank table named `_Measures`) and put
`Total Revenue`, `Gross Margin Pct` and `Avg Margin Per Shipment` in it, in a
display folder called `01 Core`. You will add to this all week.

```
git add .
git commit -m "Day 8: row vs filter context, context transition, first measures"
```

---

## Log

Three lines in `04_learning/progress.md`:
- What clicked
- What did not
- What to re-ask tomorrow

---

## Exit criteria

- [ ] You can say, without notes, why a bare column reference fails in a measure
      but works in a calculated column.
- [ ] You can explain what `CALCULATE` with no filter arguments does, and why it
      is not a no-op.
- [ ] You predicted Exercise 8.3 correctly, or you can now explain exactly what
      you had misread.
- [ ] You can name at least five distinct sources of filter context.
- [ ] `predictions.md` exists with all six exercises recorded, including the misses.
