# Day 9 — solutions

All figures computed from the built dataset. Reference values in
`04_learning/week2/_reference_answers.json`.

---

## Spaced recall answers

1. `CALCULATE` with no filter arguments performs **context transition** — it
   converts the current row context into filter context.
2. A **measure reference** inside an iterator carries an implicit `CALCULATE`, so
   context transition fires per row. The same expression written out longhand does
   not, so every row evaluates the grand total.
3. Visual rows/columns/legend; slicers; visual, page, report and drill-through
   filters; `CALCULATE` filter arguments; row-level security; context transition
   from a surrounding iterator; cross-filtering from another visual.
4. Schedule reliability is on `FactPortCall` (vessel arrival vs originally
   published ETA, **0.6598**); delivery on-time rate is on `FactShipment`
   (**0.9130**) — and neither one is OTIF, which is a separate, third figure
   (~0.867, `WHS.QLT.OTIF`, Week 3). Schedule reliability and delivery on-time
   differ because the door-delivery promise carries slack the published vessel
   schedule does not.
5. Dry containers get 5 free days, reefers 3. The shorter clock is why reefers are
   **8.3% of container moves but about 20% of D&D charges** — over-representation
   that emerges from the free-time rule rather than being coded in.

---

## Exercise 9.1 — replacement, not intersection

With `DimMode[ModeCode]` on rows:

| Row | `Revenue` | `Revenue FCL` | `Revenue FCL Kept` |
|---|---|---|---|
| FCL | FCL revenue | FCL revenue | FCL revenue |
| LCL | LCL revenue | **FCL revenue** | *(blank)* |
| AIR | AIR revenue | **FCL revenue** | *(blank)* |

**Why.** `DimMode[ModeCode] = "FCL"` expands to
`FILTER(ALL(DimMode[ModeCode]), DimMode[ModeCode]="FCL")`. The `ALL` wipes the
row's own filter on that column first, so the row context is discarded and every
row reports FCL. `KEEPFILTERS` suppresses the `ALL`, so the row's filter survives
and intersects: `LCL ∩ FCL = ∅`, hence blank.

The practical rule: **whenever you filter a column the visual is already
filtering, you almost certainly want `KEEPFILTERS`.** Omitting it is how a matrix
ends up showing the same number in every row — and unlike Day 8's repeated-total
bug, this one looks plausible, because the number is a real number.

---

## Exercise 9.2 — the four percentages

With `TradeLane` on rows and a `Year` slicer on 2025:

| Measure | Sums to 100% down the visual? | Changes when slicer moves? |
|---|---|---|
| `Pct of Grand Total` | **No** — sums to 2025's share of all years | No, denominator is fixed |
| `Pct of Visual Total` | **Yes** | Yes, denominator follows the slicer |
| `Pct of Trade Lane` | No — each row is 100% of itself | Yes |
| `Pct of Customer` | No | Yes |

`Pct of Grand Total` sums to roughly **21.7%** — 2025's 443.6M against the 2.041bn
all-time total.

**Which to use when a reader expects the column to add up: `Pct of Visual Total`,
built on `ALLSELECTED`.** Readers assume a percentage column sums to 100% within
what they are looking at. A column built on `ALL` violates that assumption
silently, and nobody notices until someone adds the column up in their head and
loses confidence in the whole report.

`Pct of Trade Lane` returning 100% on every row is correct, not broken: with
`TradeLane` on rows, `ALLEXCEPT(DimService, DimService[TradeLane])` keeps the lane
filter, so numerator and denominator are the same. It becomes useful one level
down — put `ServiceCode` on rows and each service shows its share of its parent
lane. That is the pattern for any "share of parent" column.

---

## Exercise 9.3 — the averaging trap, measured

### The four numbers

| Measure | Value | vs pooled |
|---|---|---|
| `Lines Per Labour Hour` (pooled) | **38.48** | — |
| `LPH Naive` (mean of per-task ratios) | **46.89** | **+21.9%** |
| `Revenue per FFE` (pooled, `Ffe > 0` scope) | **1,889.30** | — |
| `Revenue per FFE Naive` | **1,889.40** | **+0.01%** |

`Revenue per FFE`'s `KEEPFILTERS(FactShipment[Ffe] > 0)` restriction is not
optional here, unlike `Lines Per Labour Hour`: `FactWarehouseTask` has no
population-mixing problem, but `FactShipment` does — 39,096 air shipments carry
real `Revenue_usd` and `Ffe = 0`, so the unrestricted `DIVIDE(SUM(Revenue_usd),
SUM(Ffe))` returns **2,052.11**, an 8.61% overstatement, by including air revenue
in a ratio air contributes nothing to the denominator of. `Revenue per FFE Naive`
needs no such restriction: `DIVIDE` returns blank on every air row, and
`AVERAGEX` skips blanks, so it restricts itself automatically.

The naive version errs **high** in both cases, but by three orders of magnitude
different amounts.

### The mechanism

Compute the correlation between each per-row ratio and its own denominator:

| Ratio | corr(ratio, denominator) | Naive error |
|---|---|---|
| lines per labour hour vs labour hours | **−0.696** | +21.9% |
| revenue per FFE vs FFE | **−0.000** | +0.01% |

**Short tasks are efficient per hour; long tasks are not.** A five-minute pick line
might run at 90 lines/hour, a two-hour bulk putaway at 12. Unweighted averaging
gives both the same vote, and since the high ratios sit on the small denominators,
the mean is dragged upward. The pooled version weights by labour hours, which is
what "per labour hour" actually means.

Freight rate per FFE has no such relationship — a 1-FFE booking and a 12-FFE
booking pay broadly similar rates per box, so `corr ≈ 0` and the two methods nearly
agree.

### What this is worth knowing for

**Where to look first.** Ratios whose denominator measures effort, duration or
capacity are the dangerous ones, because efficiency and effort are almost always
inversely related. That covers: lines per labour hour, moves per crane-hour, cost
per km, orders per shift, units per pallet position. Ratios whose denominator is a
volume of *demand* — revenue per FFE, yield per kg, revenue per shipment — are
usually safe from this specific error.

Worth checking against the same data: **moves per crane-hour** comes out at
**29.80** pooled versus **29.99** naive, only +0.6%. Crane productivity is
roughly constant per hour regardless of how long the call runs, so the correlation
is weak. So even within the "effort denominator" family it is the correlation, not
the category, that decides.

**Always ship the pooled version.** The reason to measure the gap is not to license
the naive one; it is so that when you inherit somebody else's dashboard you know
which numbers to distrust first.

### Two more sub-cases worth knowing

Averaging over *groups* rather than rows is the same error at a coarser grain:

| What you average | Value | vs pooled 1,889.30 |
|---|---|---|
| unweighted mean of the 11 trade lanes' revenue per FFE | **1,927.69** | +2.0% |
| unweighted mean of per-customer gross margin | **0.18020** | −0.1% vs 0.18039 |
| unweighted mean of weekly schedule reliability | **0.65911** | −0.1% vs 0.65984 |
| unweighted mean of per-port schedule reliability | **0.65992** | +0.01% |
| unweighted mean of per-employee lines per hour | **45.26** | +17.6% |

The lane version errs by 2% because `Intra-Asia` at 602 USD/FFE gets the same vote
as `Asia–LatAm` at 3,045 despite carrying far fewer boxes. It is small here only
because the lanes are not wildly different in volume. **Do not read a small gap as
permission** — it is a property of this data's balance, and a different lane mix
would move it.

---

## Exercise 9.4 — ALL versus ALLSELECTED under a slicer

| Slicer state | `Pct All` total | `Pct AllSelected` total |
|---|---|---|
| Year = 2025 | ~**21.7%** | **100%** |
| Slicer cleared | **100%** | **100%** |

The number that is 100% in both states is **`Pct AllSelected`**. Its denominator
follows the user's selection, so it always totals to the thing the reader can see.

`Pct All` only reaches 100% when the user happens to have selected everything —
which is exactly the case in which the bug is invisible during development and
appears the moment a stakeholder touches a slicer.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Lines per labour hour, pooled | 38.48 |
| Lines per labour hour, naive per-task mean | 46.89 |
| Lines per labour hour, naive per-employee mean | 45.26 |
| corr(lines-per-hour, labour hours) | −0.696 |
| Revenue per FFE, pooled | 1,889.30 |
| Revenue per FFE, naive mean | 1,889.40 |
| corr(revenue-per-FFE, FFE) | −0.000 |
| Revenue per FFE, unweighted lane mean | 1,927.69 |
| Moves per crane-hour, pooled | 29.80 |
| Moves per crane-hour, naive mean | 29.99 |
| Total revenue | 2,040,774,144 USD |
| Revenue 2025 | 443,628,992 USD |
| Revenue per FFE, headhaul | 2,482.78 |
| Revenue per FFE, backhaul | 1,286.66 |
