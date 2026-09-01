# Day 8 — solutions

Every number here was computed from the built dataset, not estimated. If your
model gives a materially different figure, something is wrong with your model
rather than with the answer — the reference values live in
`04_learning/week2/_reference_answers.json`.

Read this only after attempting the exercises.

---

## Spaced recall answers

1. **`FactContainerMove` grain:** one row is one equipment event on one leg of one
   container's journey. 1,939,641 rows (README §1).
2. **`FactInventorySnapshot` is a periodic snapshot.** Summing `OnHandUnits` across
   a date range double-counts: the same physical box appears on every day's
   snapshot. It is semi-additive — additive across SKU and site, non-additive
   across date, where you need the value at a single point in time
   (`LASTNONBLANKVALUE`).
3. **Master vs house B/L:** the master is issued by the carrier to the
   forwarder/NVOCC; the house is issued by the forwarder to the actual shipper. One
   master can cover many houses, which is what makes consolidation possible and
   what creates the two grains in this model.
4. **Why `-1` not null:** a null foreign key silently drops rows from a join and
   removes them from totals. An explicit unknown member keeps the row countable, so
   "revenue we cannot attribute to a customer" is visible instead of missing. It
   also lets a relationship stay enforced.
5. **Schedule reliability lives on `FactPortCall`,** not `FactShipment`. It compares
   vessel `AtaTs` against the originally published `PromisedEtaTs`. `FactShipment`
   carries *delivery* on-time (`IsOnTime`), which is a different promise with more
   slack. Actual values: schedule reliability **0.6598**, delivery on-time
   **0.9130**. Conflating them is the most common error in this domain.
6. **Fourth character of an ISO 6346 owner prefix** is the equipment category
   identifier: `U` for freight containers, `J` for detachable freight-container
   equipment, `Z` for trailers and chassis.

---

## Exercise 8.1 — the failing measure

`Bad Revenue := FactShipment[Revenue_usd]` fails with a message to the effect that
a single value for the column cannot be determined.

**Why:** a measure is evaluated in filter context only. There is no row context, so
"the value of `Revenue_usd`" is not a well-defined question — there are 491,765
candidate values (README §1's `FactShipment` row count). The error is DAX telling you it has no row to read.

The same expression as a **calculated column** works, because a calculated column
is evaluated once per row and therefore always has a row context.

---

## Exercise 8.2 — SUM is SUMX

They are identical everywhere, including at the grand total: **2,040,774,144 USD**.

`SUM(col)` is defined as `SUMX(table, col)`. There is no performance difference for
this case either — the engine recognises the simple pattern. The reason to know
they are the same is that it makes context transition comprehensible: if `SUM`
iterates, then everything true of iterators is true of `SUM`.

---

## Exercise 8.3 — the repeated-total column

| Column | What you see |
|---|---|
| `Cust Revenue No Calc` | **2,040,774,144** on every single row |
| `Cust Revenue With Calc` | that customer's own revenue |

**Why.** Both columns have a row context — one `DimCustomer` row each. Row context
does not filter. Without `CALCULATE`, `SUM` sees the whole of `FactShipment`
because nothing has restricted it, so every row of the column shows the grand
total.

`CALCULATE` with no filter arguments performs **context transition**: the current
row context's columns become filter context. The customer key becomes a filter on
`DimCustomer`, that propagates across the one-to-many relationship to
`FactShipment`, and `SUM` now sees only that customer's shipments.

The tell for this bug in the wild is a column where every value is the same large
number. If you ever see that, you are looking at a missing context transition.

---

## Exercise 8.4 — the same trick in a measure

**With `CALCULATE`:** a sensible count of customers whose revenue exceeds 1M USD.

**Without `CALCULATE`:** you get either **0** or the **full customer count**
(4,171 versions / 3,200 distinct codes), never anything in between.

**Why.** `FILTER` supplies a row context over `VALUES(DimCustomer[CustomerCode])`,
but without `CALCULATE` the inner `SUM` ignores it and returns grand-total revenue
of 2,040,774,144 for every candidate row. That figure is either greater than the
threshold or it isn't — so the predicate is constant, and `FILTER` keeps all rows
or none. Total revenue exceeds 1M, so you get all of them.

**A constant answer where you expected variation is the signature of a missing
context transition.** That is the diagnostic to carry forward.

---

## Exercise 8.5 — implicit CALCULATE around a measure

`Avg Margin Per Shipment` and `Avg Margin Longhand` **disagree**.

- `Avg Margin Per Shipment := AVERAGEX(FactShipment, [Gross Margin Pct])` gives
  **0.18016** — the mean of per-shipment margins. A measure reference inside an
  iterator is implicitly wrapped in `CALCULATE`, so context transition fires on
  each row and each row gets its own margin.
- `Avg Margin Longhand` writes the division out without a measure reference. No
  implicit `CALCULATE`, so no context transition: every row evaluates the same
  grand-total margin, and averaging identical values returns that value —
  **0.18039**, the pooled margin.

So the pair that agrees is *`Gross Margin Pct` (pooled, 0.18039)* and
*`Avg Margin Longhand` (0.18039)*, and the odd one out is the one that looks most
innocent.

Two lessons:

1. **A measure reference is not a macro.** Substituting a measure's text for its
   name changes the result, because the reference carries an implicit `CALCULATE`
   and the text does not.
2. In this dataset the two margin numbers are almost identical (0.18016 vs
   0.18039, a 0.1% gap) because margin is nearly independent of shipment size.
   That is luck, not safety — Day 9 shows a case where the same structural mistake
   is out by 22%.

---

## Exercise 8.6 — count the contexts

**1. Card with a Year slicer on 2025.**
Filter context: the slicer's `DimDate[Year] = 2025`. Nothing else — a card has no
rows or columns of its own. Revenue: **443,628,992**.

**2. Same card, RLS role limiting to South Asia.**
Filter context: the Year slicer, **plus** the RLS predicate on the security anchor
(here `DimLocation[Region]` or `DimCustomer[SalesRegion]`, depending on how the
role is written). RLS is applied before anything in the report and is invisible on
the page — which is exactly why "the same report shows different numbers to
different people" is correct behaviour rather than a bug, and why a bookmark can
never be a security control.

**3. Matrix cell, plus a measure with its own `CALCULATE`.**
Four sources: the row's `TradeLane`, the column's `Year`, any page or report
filters, and the measure's own `DimMode[ModeCode] = "FCL"`. Note the fourth
**replaces** any existing filter on `ModeCode` rather than intersecting with it —
so if `ModeCode` were also on the matrix rows, the cell would show the FCL number
regardless of which mode the row claims. That is tomorrow's first exercise.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Total revenue, all shipments | 2,040,774,144 USD |
| Revenue, 2025 | 443,628,992 USD |
| Pooled gross margin | 0.18039 |
| Unweighted mean of per-shipment margin | 0.18016 |
| Schedule reliability (port calls) | 0.65984 |
| Delivery on-time rate (shipments) | 0.91304 |
| Perfect order rate | 0.85742 |
