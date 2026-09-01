# Day 14 — Calculation groups, and Checkpoint 2

> Time: 3.5 h · Spaced recall 10 min · Concept 40 min · Drill 60 min · Checkpoint 90 min · Log 15 min

The last new DAX mechanism of Week 2, then a full review. Calculation groups solve
a problem you have been quietly creating all week: every measure you have built —
`Revenue`, `Lines Per Labour Hour`, `Actual Schedule Reliability` — has no time
intelligence yet. Multiply that by MTD, QTD, YTD, PY and YoY%, and a ~150-measure
library becomes a ~750-measure library, all but impossible to keep consistent.

---

## Spaced recall (10 min, closed book)

1. What does `TREATAS` do, and which argument supplies the values versus which
   gets filtered?
2. Why did `SUMMARIZE`'s extension columns give both ABC test buckets the same
   count, and what do you use instead?
3. State, from your own numbers, the gap between recomputed and stored-actual
   schedule reliability for Americas in June 2025, and the two reasons it exists.
4. What anchor date did you use for dynamic ABC, and why not "today"?

---

## Concept

### The problem: measure multiplication

Without calculation groups, "give me Revenue as MTD, QTD, YTD, PY, and YoY%" means
five separate measures per base measure:

```dax
Revenue MTD := TOTALMTD ( [Revenue], DimDate[Date] )
Revenue QTD := TOTALQTD ( [Revenue], DimDate[Date] )
Revenue YTD := TOTALYTD ( [Revenue], DimDate[Date], "09-30" )   -- fiscal year end, per README §7
Revenue PY  := CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
Revenue YoY% := DIVIDE ( [Revenue] - [Revenue PY], [Revenue PY] )
```

Do that for even 30 of the ~150 measures you'll build in Week 3 and you have 150
extra measures, each one a place a typo or a copy-paste error can hide, and each
one that has to be independently kept correct if the time-intelligence logic ever
changes.

### The fix: one set of calculation items, applied to any measure

A **calculation group** is a table of **calculation items** — each item is a DAX
expression built around `SELECTEDMEASURE()`, a placeholder for "whichever measure
is in the visual right now." Put the calculation group's column on a slicer or in
rows, and every measure in the visual gets reshaped by whichever item is selected,
without a single new measure written.

```dax
-- Calculation group: "Time Intelligence", column: "Time Calc"
Current    := SELECTEDMEASURE ()
MTD        := TOTALMTD ( SELECTEDMEASURE (), DimDate[Date] )
QTD        := TOTALQTD ( SELECTEDMEASURE (), DimDate[Date] )
FYTD       := TOTALYTD ( SELECTEDMEASURE (), DimDate[Date], "09-30" )
PY         := CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( DimDate[Date] ) )
YoY %      := DIVIDE ( SELECTEDMEASURE () - CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( DimDate[Date] ) ),
                        CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( DimDate[Date] ) ) )
```

Five calculation items now apply to **every** measure in the model — `Revenue`,
`Lines Per Labour Hour`, all ~150 measures you will build next week — with zero
additional measures. This is the single highest-leverage thing you will build all
week: it is what turns "150 correct measures" into "150 correct measures × 5
time-intelligence variants, maintained in one place."

### Where they live, and their one sharp edge

Calculation groups are created as their own special table (Model view → **New
calculation group**, or via TMDL/the modelling MCP tools you have watched me use
this session). A model can hold more than one calculation group for genuinely
different axes of reshaping — a second one for unit conversion (USD/local currency)
is a natural next candidate, not covered today.

**The edge: calculation groups apply to *every* measure that touches the model by
default**, including ones where a time-intelligence reshape is meaningless — a
count-distinct of active carriers, a static target value, a percentage that is
already a ratio of two time-shifted things. Left unmanaged, selecting `YoY%` in a
report can silently apply to a measure that should have ignored it, producing a
number that means nothing. The fix is **precedence** and the
`Calculation Group Precedence` property, alongside excluding specific measures from
a calculation group's effect — a real setting, worth knowing exists even though
today's drill will not need it at this model's current scale.

---

## Drill

### Exercise 14.1 — build the group (30 min)
Build the `Time Intelligence` calculation group exactly as shown, with all five
items. Put `Revenue` and `Time Calc` together in a matrix with `DimDate[Year]` on
rows. Predict, before checking: which item goes **blank** for every row in the
very first year of data (2021), and why — and separately, which item matches
plain `Revenue` in *every* year shown, 2021 included, simply by how it's defined
rather than anything specific to 2021.

### Exercise 14.2 — apply it to a measure it should not touch (20 min)
Put `DISTINCTCOUNT ( DimCarrier[CarrierKey] )` (wrapped as a measure,
`Active Carrier Count`) into the same matrix as `Time Calc`. Predict what `YoY %`
produces for a count-distinct measure before checking — is a "year over year % of
active carrier count" even a sensible question, and does the calculation group
know that, or does it apply anyway? Write one sentence on what this tells you about
auditing a calculation group before shipping it widely.

### Exercise 14.3 — fiscal year check (10 min)
Confirm `FYTD` uses the fiscal year end from `README` §7 (`"09-30"`, not calendar
year end) by comparing `FYTD` at 30 September against `TOTALYTD` with no fiscal
argument at the same date. Predict which will differ and by roughly how much
before checking.

---

## Checkpoint 2 (90 min)

No new concept — this is the review the whole week has been building toward.
Closed book except for your own predictions log and the reference answers file.

**Part A — rebuild without looking (30 min).** From memory, write the DAX for:
`Revenue FCL Kept` (Day 9's `KEEPFILTERS` exercise), the point-in-time
`On Hand Value (as of)` pattern (Day 12), and `Actual Schedule Reliability (via
TREATAS)` (Day 13). Check each against your own files afterward — do not peek
first. Every mismatch is worth a note in your log: was it a syntax slip, or did
you actually forget the mechanism?

**Part B — explain the week in five answers (30 min).** Write one paragraph each,
no DAX:
1. Why does `CALCULATE` replace instead of intersect, and when do you need
   `KEEPFILTERS`?
2. Why is "never average an average" imprecise, and what determines how badly the
   naive version actually errs?
3. What makes a fact table semi-additive, and name one column from this model that
   is, and one that is fully additive, and explain the difference in one sentence
   each.
4. When do you reach for `TREATAS` instead of a physical relationship, and what is
   the one thing you must always verify before trusting the join?
5. What problem do calculation groups solve, and what is their one sharp edge?

**Part C — the number that should worry you (30 min).** Using anything you built
this week, find one number in this model that would mislead a reader if shown
without context (a naive average, an unweighted regional roll-up, a `SUMMARIZE`
extension trap, a `-1` sentinel slipping into an aggregate — your choice). Write
three sentences: what the misleading number is, what the correct number is, and
what you would tell someone who is about to put the wrong one on a dashboard. This
is the exact shape of answer that turns into a portfolio story in Week 6 — keep
what you write.

---

## Log

What clicked / what did not / what to re-ask. For Checkpoint 2 specifically: which
of the five Part B questions took you longest to answer well, and why.

---

## Exit criteria

- [ ] The `Time Intelligence` calculation group exists with all five items,
      verified against a measure you already trust.
- [ ] You can explain, from your own test, why calculation groups need auditing
      before being applied model-wide.
- [ ] Checkpoint 2 Parts A–C complete, mismatches logged.
- [ ] You can state, without notes, all five Week 2 mechanisms in one sentence
      each: `CALCULATE` replacement, the averaging trap, semi-additivity,
      `TREATAS`, and calculation groups.
- [ ] `03_powerbi` now has real committed measures from Days 9, 12, 13 and this
      calculation group — this is the seed of Week 3's full measure library.
