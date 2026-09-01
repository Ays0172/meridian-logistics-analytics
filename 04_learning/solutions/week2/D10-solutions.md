# Day 10 — solutions

All figures computed from the built dataset. Reference values in
`04_learning/week2/_reference_answers.json`.

---

## Spaced recall answers

1. A boolean filter argument expands to `FILTER(ALL(col), predicate)` — the `ALL`
   is what discards the existing filter. `KEEPFILTERS` suppresses that and
   intersects instead.
2. `ALLSELECTED`.
3. The **correlation between the per-row ratio and its own denominator**. Strongly
   negative correlation means a large error; near-zero correlation means the two
   methods nearly agree.
4. `SUM(col)` and `SUMX(table, col)` agree — they are the same operation.
   `AVERAGEX(table, [Measure])` is a different quantity.
5. `FactPortCall.IsOnTimeArrival` (vessel arrival against the originally published
   ETA, ±24 h) and `FactShipment.IsOnTime` (cargo delivered against the promised
   delivery date). 0.6598 and 0.9130 respectively.

---

## Exercise 10.1 — sum-then-multiply versus multiply-then-sum

`Total TEU Recomputed` matches `SUM(FactShipment[Teu])` **exactly** at every grain:
**1,988,953.00 TEU** at the grand total.

(Note the relationship worth carrying in your head: total FFE is **994,476.50**, and TEU is almost exactly twice it. A forty-foot box is two twenty-foot equivalents, so any dataset where TEU and FFE are close to *equal* has one of them mislabelled.)

They agree because `FactShipment[Teu]` was itself computed per row as
`ContainerCount × TeuFactor` when the data was generated. Recomputing it row by row
reproduces it. **If they had disagreed, the stored `Teu` column would be wrong** —
which is exactly the reconciliation habit worth building: recompute a stored
measure from its inputs and confirm you get it back.

`Bad Weight` is a meaningless number in the tens of millions. It multiplies a count
of containers (about 1.2 million) by the sum of `TeuFactor` across all 59 equipment
types (about 90). Neither operand belongs with the other; the answer has no unit.

The general rule: **sum-then-multiply and multiply-then-sum are different numbers.**
Only the second respects each row's own pairing of quantity and rate.

---

## Exercise 10.2 — the correct weighted rate, and a fourth trap

### The four numbers

| Measure | Value |
|---|---|
| `RPF Pooled` (ocean revenue ÷ ocean FFE, `KEEPFILTERS`-scoped) | **1,889.30** |
| `RPF SumX` | **1,889.30** — identical |
| `RPF Naive` (`AVERAGEX` of per-row ratios) | **1,889.40** |
| `RPF Mismatched Scope` (all revenue ÷ ocean FFE, no restriction) | **2,052.11** |

`RPF Pooled` and `RPF SumX` agree, because `SUM` *is* `SUMX`. `RPF Naive` is close
but not identical — off by only 0.01%, for the reason you measured yesterday:
revenue per FFE is essentially uncorrelated with FFE. `RPF Mismatched Scope` is the
dangerous outlier, and it is the version most people write first.

### The trap that actually matters here

The dataset holds **39,096 air shipments** carrying **161.9M USD of revenue** — 7.9%
of the total — and **zero FFE**, because an air consignment is not a container.
`RPF Mismatched Scope`'s numerator is `SUM(FactShipment[Revenue_usd])` over
everything while its denominator only has ocean rows to contribute to (`Ffe = 0`
for every air row), so it puts air revenue on top of ocean containers:

```dax
-- WRONG: numerator includes air, denominator cannot
RPF Mismatched Scope :=
DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) )
```

That returns **2,052.11** — an **8.61% overstatement** against the correctly-scoped
1,889.30. It is not a rounding artefact and it is not obviously wrong on sight:
2,053 USD per FFE is a perfectly plausible figure. It would sail through a review —
which is exactly why `RPF Pooled` and `RPF SumX` restrict scope explicitly rather
than relying on how the formula happens to look:

```dax
-- RIGHT: both sides restricted to container traffic
RPF Pooled :=
CALCULATE (
    DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) ),
    KEEPFILTERS ( FactShipment[Ffe] > 0 )
)
```

Note `KEEPFILTERS`, so the restriction intersects with whatever the visual is
already filtering rather than replacing it — yesterday's lesson doing real work.

**The general principle: a ratio is only meaningful if its numerator and its
denominator describe the same population.** Whenever a fact table mixes grains —
and this one mixes containers, revenue tons and chargeable kilograms — every ratio
needs an explicit scope, and "it looks plausible" is not a check.

### What `AVERAGEX` does with the blanks

`DIVIDE` returns **blank** on the air rows, and `AVERAGEX` — like `AVERAGE` —
**skips blanks rather than treating them as zero**. So `RPF Naive` is computed over
**452,669 of 491,765 rows**, the air rows silently dropping out. That is why the
naive measure accidentally lands on the right scope while the "obvious" pooled
version does not.

Had blanks been counted as zero, the answer would be **1,739.19** — a 7.9%
understatement, the mirror image of the other error. Knowing which convention your
aggregator uses is not trivia; here it is the difference between three different
answers to the same question.

| Version | Value | Error vs correct |
|---|---|---|
| Correct (both sides ocean) | 1,889.30 | — |
| Mismatched scope | 2,052.11 | **+8.61%** |
| Naive, blanks skipped (DAX behaviour) | 1,889.40 | +0.01% |
| Naive, blanks as zero (hypothetical) | 1,739.19 | −7.94% |

---

## Exercise 10.3 — rank the lanes two ways

Revenue per FFE, descending:

| Rank | Trade lane | Revenue per FFE | Total revenue (M USD) |
|---|---|---|---|
| 1 | Asia–LatAm | 3,041.50 | see below |
| 2 | Transpacific East | 2,878.09 | |
| 3 | Asia–N Europe | 2,581.25 | |
| 4 | Asia–Mediterranean | 2,430.09 | |
| 5 | Europe–LatAm | 2,170.66 | |
| 6 | ISC–Europe | 1,931.22 | |
| 7 | Transatlantic | 1,714.88 | |
| 8 | Asia–ISC | 1,389.66 | |
| 9 | Asia–MEA | 1,315.98 | |
| 10 | Transpacific West | 1,149.46 | |
| 11 | Intra-Asia | 601.78 | |

**The lane that tops the yield ranking without topping the revenue ranking is
`Asia–LatAm`.** It earns the most per box but does not carry the most boxes, so it
is not the largest revenue line. `Intra-Asia` is the mirror image: the worst yield
per FFE at 602 USD, but a high-volume lane, so it contributes far more revenue than
its yield rank suggests. Check your own model for the exact revenue ordering — the
point is that the two rankings genuinely differ.

**Which to show a trade manager first: revenue.** Yield tells you which lane is
most attractive per unit; revenue tells you which lane you cannot afford to lose.
A dashboard that leads on yield invites the conclusion "exit Intra-Asia", which
would remove a large revenue line and a lot of network density feeding the
deep-sea services. Show both, lead with the one that carries the consequence.

This is why the Week 3 Ocean dashboard puts volume and revenue on the left and
yield on the right, rather than sorting the page by yield.

### On `DENSE` versus `SKIP`

`DENSE` gives 1, 2, 2, 3 on a tie; `SKIP` gives 1, 2, 2, 4. With 11 distinct lane
yields there are no ties here, so both behave identically — but pick deliberately,
because on a customer ranking with thousands of members ties are common and the two
conventions produce visibly different tables.

---

## Exercise 10.4 — guard a measure against the wrong grain

- On a **card with no slicer**: `SELECTEDVALUE(DimMode[ModeCode])` returns blank
  because eight mode values are visible, so `SWITCH` falls through to the default
  and you get *"Mixed modes — select one"*.
- With **`ModeCode` on rows**: each row has exactly one visible value, so each row
  gets its correct basis label.

`Chargeable Weight Basis` with the `HASONEVALUE` guard behaves the same way but
states the reason explicitly rather than relying on a `SWITCH` default.

**When a refusal beats a number.** Any measure whose meaning depends on the grain
should refuse rather than average across grains. Chargeable weight is the sharp
example: air uses a 1:6000 volumetric divisor, ocean LCL uses the 1:1000
revenue-ton rule, and FCL charges per container. A single "average chargeable
weight" across all three is arithmetic performed on incompatible units. It will
render as a number, and that number will be quoted at you later.

The same argument applies to revenue per FFE on a page filtered to air, and to
lines per labour hour across two warehouses on different WMS conventions. A blank
prompts a question; a wrong number ends the conversation.

---

## Exercise 10.5 — variables that capture the outer context

**As written** — `VAR ThisRevenue = [Total Revenue]` declared before the `FILTER` —
each row shows its rank among the services in its own trade lane: 1, 2, 3 and so on.

**Moved inside the `FILTER`**, every row shows **1**.

**Why.** A variable is evaluated where it is *written*, in the filter context
prevailing at that point. Declared outside, `ThisRevenue` captures the current
row's revenue before `CALCULATETABLE(... ALLEXCEPT ...)` widens the context — so
the comparison is this service against its siblings.

Declared inside the `FILTER`, it is re-evaluated in the row context of the service
currently being tested. The predicate becomes `[Total Revenue] > [Total Revenue]`
for that same service — always false — so `COUNTROWS` returns blank, and `+ 1`
makes every row 1.

**Everything shows 1** is the signature of a comparison measure whose captured
value was not captured. It sits alongDay 8's two other diagnostics:

| Symptom | Cause |
|---|---|
| Every row shows the same large total | Missing context transition |
| Every row shows the same non-total number | Filter replaced instead of intersected (missing `KEEPFILTERS`) |
| Every row shows 1, or 0, or blank | Variable evaluated in the wrong context |

Those three cover most of what goes wrong in practice. Learn to read the symptom
and you can skip most of the debugging.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Total TEU | 1,988,953.00 |
| Total FFE | 994,476.50 |
| Revenue per FFE, correct (ocean only) | 1,889.30 |
| Revenue per FFE, mismatched scope | 2,052.11 (+8.61%) |
| Revenue per FFE, naive with blanks skipped | 1,889.40 |
| Revenue per FFE, naive with blanks as zero | 1,739.19 |
| Air shipments / revenue / FFE | 39,096 rows / 161.9M USD / 0 FFE |
| Air share of total revenue | 7.92% |
| Rows with FFE > 0 | 452,669 of 491,765 |
| Best-yield lane | Asia–LatAm, 3,041.50 USD/FFE |
| Worst-yield lane | Intra-Asia, 601.78 USD/FFE |
