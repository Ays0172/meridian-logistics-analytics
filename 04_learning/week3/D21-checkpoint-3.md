# Day 21: Checkpoint 3

> Time: 3.5 h · Spaced recall 10 min · Verification pass 90 min · Checkpoint 90 min · Log 15 min

No new mechanism today. Six days ago you had a method and an empty `_Measures`
table; today you should have a ~150-measure library covering all 72 KPIs, organised
into five domain folders each with its own function subfolders, with every naive
trap named and every measure traceable back to `00_docs/KPI_DICTIONARY.md`. Before
you trust any of it, verify it, closed book except your own model and the
dictionary itself.

---

## Spaced recall (10 min, closed book)

1. State the `[KpiCode]` description convention and why the code matters more than
   the folder name.
2. Name the two arithmetic-operator traps this week that are mirror images of each
   other, and which KPI each one belongs to.
3. Why does `MAX(GrossWeightKg, VolumeCbm)` collapse to `GrossWeightKg` for
   essentially every real air shipment, and what does that do to a volumetric-driven
   shipment's billing if someone applies it by mistake?
4. Why is `Cash-to-Cash Cycle Time` shipped as "partial," and which single fact
   would need to exist in this contract to complete it?
5. Restate why ranking by `CustomerCode` rather than `CustomerKey` changes
   `Top-10 Customer Share`, in one sentence naming the mechanism.

---

## Verification pass (90 min)

This is the actual job, not a formality: a measure library nobody has checked
against its source of truth is not verified: it is merely built. Do all four
exercises against your own live model.

### Exercise 21.1: target/benchmark spot-check (30 min)
Pick at least ten shipped measures spanning all five domains and compare each
against the target/benchmark band or `README` §6 headline figure the dictionary
states. A starter list, extend it:

| Measure | Expected band / value |
|---|---|
| `Laden Share of TEU` | 66–70% |
| `Headhaul Load Factor` | 0.88–0.96 |
| `Schedule Reliability Rolling 8wk` | 0.6598 network-wide (README §6) |
| `Rollover Ratio` | ~9% baseline |
| `Pick Accuracy %` | 99.1% overall baseline |
| `OTIF %` | 0.85–0.88 gate, ~0.867 headline |
| `Perfect Order Rate (Warehouse-touched)` | 0.84–0.89 |
| `Perfect Order Rate (Company-wide)` | 0.8574 (README §6) |
| `Top-10 Customer Share` | 27.8% (README §6) |
| `Gross Margin % Std Dev` / mean margin context | mean 14–22% |

For any measure that falls **outside** its stated band, do not assume the
dictionary is wrong, walk the DAX against the dictionary's formula line by line
first. A mismatch is far more often a wrong filter, a wrong table, or a forgotten
`KEEPFILTERS`/sentinel exclusion than a bad benchmark. Log every mismatch and its
resolution.

### Exercise 21.2: description and traceability audit (20 min)
List every measure in `_Measures`. For each of the 72 codes in
`KPI_DICTIONARY.md` §0's summary table, confirm it appears in exactly one shipped
measure's `[KpiCode]` description, or is explicitly logged as not yet built.
Reconcile your tally against the domain counts (22 + 16 + 18 + 9 + 7 = 72). If you
are short of 72, that is fine: this week's checklists existed precisely so you
could triage under real time pressure, but the gap must be **known and listed**,
not silently missing. A measure library with an unknown number of untranslated
KPIs is a worse state than one that honestly says "9 of 72 remain, here they are."

While you're in Model view for this pass, also confirm the Day 15 two-level
taxonomy held, against the actual per-domain expectation, not "four everywhere":

| Domain folder | Function subfolders it should show |
|---|---|
| `05 Ocean Liner` | Volume & Mix, Rate & Utilisation, Revenue & Cost |
| `06 Landside` | Rate & Utilisation, Revenue & Cost, Quality & Service |
| `07 Warehouse & Inventory` | all four |
| `08 Air & LCL` | Volume & Mix, Rate & Utilisation, Revenue & Cost |
| `09 Cross-Cutting` | Revenue & Cost, Quality & Service |

Flag any domain with a subfolder outside this list (a sign a measure was
misclassified) or missing one it should have, and confirm no measure sits loose at
the domain level with no subfolder, `XCT.SCOR.MAP` excepted. A stray top-level
folder that looks like `05 Ocean Liner - Revenue & Cost` (a hyphen where the
backslash separator belongs) instead of nesting properly is the Exercise 15.1 typo
trap, now caught for real instead of on a placeholder.

### Exercise 21.3: calculation-group cross-check (20 min)
Apply Day 14's `Time Intelligence` calculation group to one measure from each
domain: an additive one (`Demurrage Revenue`), a ratio (`Truck Utilisation %`), and
one you suspect might misbehave under `YoY %` the way `Active Carrier Count` did on
Day 14. Predict, before checking, which of the three behaves sensibly under every
calculation item and which does not. Then specifically check whether
`Carrier Composite Score` even *can* sit in the same visual as the calculation
group, it was shipped Day 17 as a table-valued expression backing a matrix, not a
single scalar measure. Write one sentence on what that structural difference means
for which of this week's ~150 measures a calculation group can reshape at all.

### Exercise 21.4: naive-variant audit (10 min)
List every naive/correct pair shipped this week. There should be roughly a dozen:
`OCN.REL.SCHED`, `OCN.UTL.LF.HEAD`, `OCN.OPS.MPCH.GROSS`, `LND.CST.KM`,
`LND.UTL.DEADHEAD`, `LND.SUS.CO2`, `LND.CAR.SCORE`, `WHS.QLT.PICKACC`,
`WHS.INV.TURNS`, `ALC.REV.YIELDKG`, `XCT.CUS.CONC`. Confirm every naive measure is
named `[DO NOT USE] <Name> (naive)`, sits in the **same** domain-and-function
subfolder as its correct sibling, and has a description stating the error
mechanism in one line.
Any pair that fails this check gets fixed now, not logged for later: this is the
cheapest week to fix it in.

---

## Checkpoint 3 (90 min)

Closed book except your own predictions log and reference answers.

**Part A, rebuild without looking (30 min).** From memory, write the DAX for:
`OTIF %` (correct, multiplicative), `DIFOT %` (joint condition, not the product of
marginals), and one naive/correct pair of your own choosing, with a one-sentence
justification of exactly why the naive version is wrong. Check each against your
own files afterward, do not peek first. For every mismatch, note whether it was a
syntax slip or an actually-forgotten mechanism.

**Part B, explain the week in five answers (30 min).** One paragraph each, no DAX:

1. OTIF's trap is averaging when you should multiply; DIFOT's trap is multiplying
   when you should count a joint condition. What is the common thread linking both,
   and why does the "right" combining operator depend on whether the underlying
   events are independent?
2. What is the actual difference between the air 1:6000 and 1:5000 chargeable-weight
   divisors, and why does ocean LCL use a structurally different rule (flat 1:1000)
   instead of a third divisor on the same scale?
3. Why is `Cash-to-Cash Cycle Time` shipped labelled "partial," and what would need
   to exist in this contract to complete it?
4. Why does ranking `Top-10 Customer Share` by `CustomerCode` instead of
   `CustomerKey` change the answer, and what model feature from Week 1/2 makes this
   necessary?
5. Day 14 introduced calculation groups as a mechanism with one sharp edge, tested
   on a single count-distinct measure. What did building ~150 real measures across
   five domains this week make concretely true about that edge that was only
   theoretical when you had 20 measures?

**Part C, the number that should worry you (30 min).** From this week's library,
find one measure that would mislead a reader if shown without context, a naive
variant someone forgot to mark, a partial figure someone might relabel as complete,
a ratio computed at the wrong grain, a percentage that doesn't sum the way a reader
expects. Write three sentences: what the misleading number is, what the correct
number is, and what you would tell someone about to put the wrong one on a
dashboard. Keep what you write: this is Week 6 portfolio material, same as
Checkpoint 2's Part C.

---

## Log

What clicked / what did not / what to re-ask. Specifically: which of the four
verification exercises found a real problem in your own model, and what was it?

---

## Exit criteria

- [ ] At least ten measures spot-checked against their dictionary/README target
      band, mismatches resolved or explained.
- [ ] Every one of the 72 KPI codes accounted for, either shipped with a
      `[KpiCode]` description, or explicitly logged as an open item.
- [ ] Calculation-group behaviour checked against at least one measure per domain,
      and you can state which of this week's measures the calculation group cannot
      meaningfully apply to, and why.
- [ ] All ~11 naive/correct pairs verified: naive named `[DO NOT USE]`, same
      domain-and-function subfolder as its correct sibling, error mechanism stated
      in its description.
- [ ] Checkpoint 3 Parts A–C complete, mismatches logged.
- [ ] You can state, without notes, all five Week 3 domains and one representative
      trap from each, in one sentence per domain.
