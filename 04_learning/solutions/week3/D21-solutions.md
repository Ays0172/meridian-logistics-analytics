# Day 21: solutions

---

## Spaced recall answers

1. `[KpiCode] <definition>. <watch-out>.` The code is the join key back to
   `KPI_DICTIONARY.md`; a folder can be renamed or reorganised (it's just a
   string), but the code is what makes a measure traceable to its authoritative
   definition and target band regardless of where it sits in the Fields pane.
2. `WHS.QLT.OTIF` (Day 18): naively averages three marginals that should be
   multiplied. `LND.SVC.DIFOT` (Day 17): naively multiplies two marginals that
   should be counted as a joint condition. They are mirror images, one trap goes
   `+` where it should go `×`, the other goes `×` where it should go "count the
   joint event directly."
3. `VolumeCbm` is a bare cubic-metre count (typically two-to-three digits);
   `GrossWeightKg` is a kilogram count (typically three-to-five digits). For the
   volume term to win the `MAX`, density would need to fall below ~1 kg/cbm,
   physically impossible. Applied to a volumetric-driven shipment, this silently
   under-bills it to actual weight, missing exactly the population the real 1:6000
   rule exists to catch.
4. It is partial because true DSO (actual collection speed) and DPO (days payable
   outstanding) cannot be computed under this contract, there is no cash-receipt
   date anywhere, and no vendor payment-terms field or accounts-payable fact table
   at all. Completing DPO alone would need `DimCarrier.PaymentTermsDays` or a new
   `FactAccountsPayable` table with invoice/payment dates.
5. `DimCustomer` is SCD2, one durable customer can have multiple `CustomerKey`
   surrogate rows over its history but only one `CustomerCode`. Ranking by
   `CustomerKey` can split one real customer's revenue across several key versions,
   each individually smaller, understating that customer's true concentration.

---

## Exercise 21.1: target/benchmark spot-check, reference guidance

There is no single "correct" live number to check against here, your own build's
exact figures depend on your data. What is checkable, unconditionally, against the
frozen `KPI_DICTIONARY.md` and `SCHEMA_CONTRACT.md`:

| Measure | Band/value to check against | Source |
|---|---|---|
| `Laden Share of TEU` | 66–70% | `SCHEMA_CONTRACT.md` §4 gate 3 |
| `Headhaul Load Factor` / `Backhaul Load Factor` | 0.88–0.96 / 0.55–0.70 | §4 gate 4 |
| `Schedule Reliability Rolling 8wk`, network-wide | 0.6598 | `README` §6 |
| `Schedule Reliability Rolling 8wk`, congestion window | 0.28–0.34 | §4 gate 5, §3.3 |
| `OTIF %` | 0.85–0.88 | §4 gate 6 |
| `Perfect Order Rate (Company-wide)` | 0.84–0.89, headline 0.8574 | §4 gate 6, README §6 |
| `Top-10 Customer Share` | 27.8% | README §6 |
| Gross margin mean (context for `Margin Dispersion`) | 0.14–0.22, left tail below zero | §4 gate 7 |
| `Pick Accuracy %` | 99.1% overall, 97.4% night shift, 98.2% agency <6mo | §3.4 |
| `Rollover Ratio` | ~9% baseline, ~19% congestion window | §2.1, §3.3 |

**If any of your own figures fall outside these bands**, the highest-probability
causes, in order, are: (1) a missing `KEEPFILTERS` or sentinel exclusion (`<> -1`)
somewhere in the chain, (2) a filter applied to the wrong table (a `FactPortCall`
filter that should be on `DimVoyage` via `RELATED`, or vice versa), (3) a measure
accidentally built against a different fact table than the dictionary specifies.
Genuinely wrong dictionary values are the least likely explanation, this contract
is frozen and validated, per its own status line, so the burden of proof is on your
DAX, not on the source.

---

## Exercise 21.2: description and traceability audit, reference guidance

The tally to reconcile against: **22 Ocean + 16 Landside + 18 Warehouse & Inventory
+ 9 Air & LCL + 7 Cross-cutting = 72.** A realistic outcome for most learners
completing Days 15–20 at pace: all 8–11 "worked in full" measures per domain
shipped with descriptions, most checklist items completed, a handful genuinely
outstanding (commonly `WHS.OPS.OCT`'s `SUMMARIZE`-grain measure and the full 72-row
`SCORMap` table are the two most often left partial, since both take longer than
their single checklist line suggests). **The number that matters is not "72/72",
it is "you know the exact number and can name every gap."** A measure library that
claims completeness without a reconciled count is a worse deliverable than one that
honestly states "63 of 72 shipped, here are the 9 remaining and why."

---

## Exercise 21.3: calculation-group cross-check

`Demurrage Revenue` (additive) and `Truck Utilisation %` (a bounded 0–1 ratio) both
behave sensibly under every `Time Intelligence` calculation item, `MTD`/`QTD`/
`FYTD`/`PY` all produce interpretable numbers, `YoY %` is a legitimate question for
both (did demurrage revenue grow year over year; did utilisation improve year over
year).

**`Carrier Composite Score` cannot sit in the same visual as the calculation group
at all**, for a structural reason distinct from Day 14's `Active Carrier Count`
finding: it was shipped as a **table-valued DAX expression** backing a matrix
visual (one row per carrier, computed via `ADDCOLUMNS`/`SUMMARIZE`-style logic),
not a single scalar measure that returns one number in a filter context.
`SELECTEDMEASURE()` inside a calculation item expects to reshape a scalar-valued
measure reference, there is no single "the measure" for a calculation item to
wrap when the underlying DAX itself produces a table with several computed
columns. **What this means for the ~150-measure library:** any measure built this
week as a table-valued expression for a matrix (`Carrier Composite Score` is the
one example so far) sits **outside** the calculation group's reach entirely, not
merely "reshaped in a way that happens to be meaningless" (Day 14's finding for
`Active Carrier Count` under `YoY %`). This is a sharper, structural version of Day
14's edge: it is not just that some measures produce nonsense under some
calculation items: it is that some "measures" in this library are not scalar
measures at all and the calculation group cannot touch them regardless of which
item is selected.

---

## Exercise 21.4: naive-variant audit, the complete list

| KPI | Correct measure | Naive measure name |
|---|---|---|
| `OCN.REL.SCHED` | `Schedule Reliability Rolling 8wk` | `[DO NOT USE] Schedule Reliability Rolling 8wk (naive)` |
| `OCN.UTL.LF.HEAD` | `Headhaul Load Factor` | `[DO NOT USE] Headhaul Load Factor (naive)` |
| `OCN.OPS.MPCH.GROSS` | `Moves per Crane-Hour Gross` | `[DO NOT USE] Moves per Crane-Hour Gross (naive)` |
| `LND.CST.KM` | `Cost per km` | `[DO NOT USE] Cost per km (naive)` |
| `LND.UTL.DEADHEAD` | `Deadhead %` | `[DO NOT USE] Deadhead % (naive)` |
| `LND.SUS.CO2` | `CO2 per Tonne-km (g)` | `[DO NOT USE] CO2 per Tonne-km (naive)` |
| `LND.CAR.SCORE` | `Carrier Composite Score` | `[DO NOT USE] Carrier Score (naive)` |
| `WHS.QLT.PICKACC` | `Pick Accuracy %` | `[DO NOT USE] Pick Accuracy % (naive)` |
| `WHS.INV.TURNS` | `Inventory Turns` | `[DO NOT USE] Inventory Turns (naive)` |
| `ALC.REV.YIELDKG` | `Yield per kg` | `[DO NOT USE] Yield per kg (naive)` |
| `XCT.CUS.CONC` | `Top-10 Customer Share` | `[DO NOT USE] Top-10 Customer Share (naive)` |

Eleven pairs. Each naive measure's description should name its specific error
mechanism (which denominator/operator/basis is wrong), not just say "do not use
this", the description is what turns a warning label into a teaching tool for the
next person who opens the folder.

---

## Checkpoint 3: Part B reference answers (compare, don't copy)

1. Both traps come from treating correlated events as if a simple arithmetic
   shortcut (mean, or independent product) could stand in for the true joint
   computation. Whether the correct operator is `×` (OTIF, a genuine joint AND
   requirement across independently-generated marginals) or "count the joint
   condition directly" (DIFOT, where the two conditions are positively correlated
   in reality) depends on whether the underlying events are actually independent,
   OTIF's three components are generated independently in this dataset, so their
   true joint probability is the product; DIFOT's two components (late, partial)
   are not independent, so multiplying their marginals systematically understates
   the true joint rate and only directly counting the joint condition is correct.
2. Both air divisors compute volumetric weight as `Volume_cbm × 1,000,000 ÷
   divisor`; 6,000 is the IATA standard, 5,000 is used by some carriers and
   historically some express networks, and because 5,000 is the smaller divisor,
   the same volume produces a *higher* (more expensive) volumetric weight under
   it. Ocean LCL uses a structurally different rule, a flat 1,000 kg-per-cbm
   weight-or-measure equivalence with no divide-by-thousands step at all, because
   ocean freight economics are conventionally priced on a direct tonne-for-cbm
   basis, not on the same kind of volumetric-density formula air freight uses; the
   two are different pricing conventions, not two points on the same scale.
3. `Cash-to-Cash Cycle Time` is partial because true DSO (actual collection speed)
   and DPO cannot be computed under this contract, no cash-receipt date exists
   anywhere, and there is no vendor payment-terms field or accounts-payable fact.
   Completing it would need, at minimum, `FactFreightCharge.PaymentReceivedDateKey`
   (or a `FactCashApplication` table) for true DSO, and either
   `DimCarrier.PaymentTermsDays` or a new `FactAccountsPayable` table for DPO.
4. `DimCustomer` is SCD2 (Day 8/13 territory), one durable customer can carry
   multiple `CustomerKey` surrogate versions across its history (triggered by
   changes to `AccountManager`, `CreditTier`, `SizeTier`, `ContractType`), but only
   one durable `CustomerCode`. Ranking by the surrogate key can split one real
   customer's revenue across several smaller slices, none of which individually
   ranks as high as the customer's true combined revenue would, understating
   concentration risk exactly where it matters most, at the largest accounts most
   likely to have accumulated SCD2 history.
5. Day 14 tested the calculation-group edge on one measure (`Active Carrier
   Count`) and found that a calculation item applies even where it's meaningless.
   Building ~150 real measures across five domains made two things concretely true
   that a 20-measure library only gestured at: first, the sheer *number* of
   measures where a reshape is questionable is large enough that "audit before
   shipping widely" is a real, non-trivial task, not a one-line caveat; second, and
   newly discovered this week (Exercise 21.3), some of this library's measures
   (`Carrier Composite Score`) are not scalar measures at all, so the calculation
   group's reach has a structural boundary Day 14's single-measure test never
   revealed, because Day 14 had no table-valued measures in the library yet to
   surface it.

Part C has no reference answer: it is your own finding, written for your own
portfolio, the same as Checkpoint 2's Part C.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Total KPI count (72) domain split | Ocean 22 / Landside 16 / Warehouse 18 / Air & LCL 9 / Cross-cutting 7 |
| Schedule reliability, network / congestion window | 0.6598 / 0.28–0.34 |
| OTIF gate / headline | 0.85–0.88 / ~0.867 |
| Perfect order rate, company-wide | 0.8574 |
| Top-10 customer share | 27.8% |
| Naive/correct pairs shipped this week | 11 |
