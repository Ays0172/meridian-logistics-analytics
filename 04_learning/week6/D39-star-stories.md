# Day 39: STAR stories, written from this project's real debugging history

> Time: 3 h · Spaced recall 10 min · Concept 15 min · Drill 110 min · Ship 20 min · Log 15 min

Every interview eventually asks some version of "tell me about a time you found a
bug in a dashboard" or "walk me through debugging a data quality issue." Most
candidates answer with something vague and generic, because they're improvising
from memory under pressure. You don't have to: this project's build and cleanup
history contains four real, specific, technically substantive debugging stories,
already verified against this exact dataset. Today writes them out fully, in
STAR format, so they're ready to say out loud rather than reconstructed live.

---

## Spaced recall (10 min, closed book)

1. Why does averaging `FactTarget`'s own actuals across lanes reproduce the exact
   same error class Day 9 taught you to distrust in DAX measures (Day 13/36/37)?
2. What is `-1` reserved for in this project's conventions, and its own text
   label per README §7? Separately — for a *real, non-unknown-member* row whose
   text attribute genuinely doesn't apply, what should the column hold instead
   of a placeholder string (Story 2, below)?
3. Why does `FactInventorySnapshot[OnHandValueUsd]` become roughly 500× too large
   under a naive `SUM` with no date filter (Day 12)?
4. What does `EventDateKey` mean on `FactContainerMove`, versus the table's own
   surrogate key `ContainerMoveKey`, and why would confusing the two break a
   relationship to `DimDate` in a way that's obvious rather than silent?
5. Day 14 said a specific kind of write-up "turns into a portfolio story in
   Week 6." What was that Part C prompt asking for?

---

## Concept

### Why STAR, and why these four specifically

STAR (Situation, Task, Action, Result) works because it forces you to include the
two things a rambling technical war-story usually drops: what was actually at
stake (Task) and what changed because of what you did (Result), quantified. A
technically accurate but result-free story ("I found that the relationship was
wired wrong and fixed it") is weaker than one that closes the loop ("...which
meant every date-filtered container report had been silently returning zero rows,
and after the fix the container dashboards started reflecting reality for the
first time").

The four stories below all come from real work on this project's own model: two
from a live data-quality cleanup pass on the finished semantic model (Stories 1
and 2), two from building it earlier in the curriculum (Story 3, Day 12; Story 4,
Day 13). They share a structure worth noticing before you write your own version:
each one is a case where the model *looked* fine (no error, no crash, a plausible
number) and was actually wrong, which is the single most interview-relevant shape
of bug in analytics work. Lead with that framing in your own delivery: "the
dangerous bugs in BI don't crash, they just look plausible" is a stronger opening
line than diving straight into DAX syntax.

### The two-length rule

Prepare each story at two lengths: a **15-second headline** (for "any recent
challenges?" small talk or a resume bullet) and the **full 90-second STAR**
(for "walk me through it"). Practice both. The failure mode isn't not knowing the
story, it's either running the 90-second version when 15 seconds was asked for, or
freezing on the 90-second version because you only ever rehearsed the headline.

---

## Drill

Write all four stories in full below, then run Exercise 39.5.

### Story 1: the mis-wired FactContainerMove relationship

**Headline:** "Found and fixed a relationship silently wired to the wrong key,
using a DAX validation query rather than staring at the diagram."

**Situation.** During a data-quality pass on the finished semantic model,
`FactContainerMove` (the largest fact table in the project, at nearly 2 million
rows) had its relationship to `DimDate` built on `ContainerMoveKey`, the table's
own transaction-grain surrogate key, instead of `EventDateKey`, the actual foreign
key that identifies which calendar date each container-move event happened on.

**Task.** Any report or measure that filtered container-move activity by date
(month-over-month volume trends, the free-time/demurrage-days calculations, any
slicer on `DimDate[Year]` touching this table) needed to actually work, and
nothing in the model's visual diagram flagged the relationship as wrong. A
mis-wired relationship between two integer key columns doesn't throw an error; it
just silently returns nothing, or the wrong thing, for anything that depends on it.

**Action.** I didn't spot this by eyeballing the relationship diagram: a
one-to-many line from `DimDate` to `FactContainerMove` looks correct at a glance
regardless of which column it's actually bound to. It surfaced through DAX
validation: a straightforward date-filtered `CALCULATE` against
`FactContainerMove` (something as simple as "container moves in March 2025")
returned **zero rows**, which is the tell. A real, populated fact table returning
an empty result for an ordinary filter almost always means the relationship
connecting it to the filtering table is wrong, not that the data genuinely has
none. I confirmed by checking what `ContainerMoveKey`'s value range actually was
(a plain row-number surrogate key, nothing date-shaped about it) against
`EventDateKey`'s (a real `yyyymmdd` integer matching `DimDate[DateKey]`'s domain),
then deleted the bad relationship and recreated it correctly on `EventDateKey`.

**Result.** Every date-filtered measure touching `FactContainerMove` (dwell time,
demurrage/detention days-past-free-time, laden/empty move counts by month) went
from returning zero or blank to returning real, populated numbers immediately
after the fix, with no DAX changes required anywhere; the measures had been
correct the whole time, only the relationship underneath them was wrong.

**Likely follow-ups, and how to answer them:**
- *"How did you know to check the relationship instead of the measure?"* Because
  the failure mode was total (zero rows), not partial or slightly-off. A DAX bug
  in the measure itself usually produces a wrong-but-plausible number; a "returns
  nothing at all for an ordinary filter" failure on a table you know is populated
  points at the join, not the arithmetic.
- *"Why didn't the model flag this automatically?"* Because a relationship
  between two syntactically valid integer columns is not an error to the engine;
  it's only wrong semantically, which nothing but a value-range sanity check or a
  known-good query result can catch.

---

### Story 2: the systemic "#NA" placeholder bug (two different bugs wearing the same disguise)

**Headline:** "Found that one text placeholder was hiding two unrelated
problems (one cosmetic, one a real filter-logic trap), and fixed only the one
that mattered, after checking which was which."

**Situation.** Seventeen columns across nine dimension tables carried the literal
text string `"#NA"` instead of a real value. At first glance this looked like one
bug to fix uniformly.

**Task.** Determine, column by column, whether `"#NA"` was doing the job the
schema contract intends (marking the deliberate `-1` unknown-member row: e.g.
`DimVessel[FuelType] = "#NA"` on the single synthetic "Unknown" vessel row is
expected, per this project's own convention) or whether it had also leaked into
real, populated rows as a stand-in for a genuine missing value, which is a
materially different and more dangerous problem — and each category still needed
its own fix, not the same one.

**Action.** I checked each of the seventeen columns' `"#NA"` rows individually
rather than assuming uniformity. Twelve, across seven tables, behaved as
designed: `"#NA"` appeared only on each dimension's single `-1` unknown-member
row — correct in principle, but still an ugly, code-like label to surface in a
report ("Carrier: #NA" instead of "Carrier: Unknown"), so I relabelled those
twelve to `"Unknown"` in Power Query, a pure cosmetic fix that changes no
filtering behaviour. Five columns, across four tables
(`DimCommodity[ImdgClass]`, `DimCommodity[UnNumber]`, `DimCarrier[AllianceName]`,
`DimLocation[IataCode]`, `DimMilestone[EdifactMessageType]`), had `"#NA"` on
**many** real, non-unknown-member rows: a text placeholder standing in for what
should have been a true `BLANK()`. That's the dangerous version: a DAX filter
like `FactShipment.Commodity[ImdgClass] <> BLANK()`, written by anyone reasonably
assuming that column follows normal null conventions, silently returns **every**
row, including the ones that are genuinely not dangerous goods, because nothing
in that column is ever actually blank: it's always either a real IMDG class or
the string `"#NA"`. I fixed those five with `Table.TransformColumns` steps in
Power Query, replacing `"#NA"` with `null` conditionally — a different fix from
the twelve cosmetic columns, because a genuinely-blank case and a mislabelled
unknown-member case need different treatment even though they present
identically in a column preview.

**Result.** All seventeen columns are fixed, but not identically: the five
structural cases now support correct `<> BLANK()` filtering, so any measure or
visual built on them from this point forward behaves the way its author would
reasonably expect; the twelve cosmetic cases now display a real label instead of
a placeholder string, without changing any filter's behaviour. Treating all
seventeen the same way — either "fix them all like the dangerous ones" or "leave
them all alone because most are cosmetic" — would have been wrong in both
directions.

**Likely follow-ups:**
- *"How would you have found this without already knowing where to look?"* Audit
  every text placeholder column with a `DISTINCT`/value-count query before trusting
  any of them uniformly; the mistake to avoid is assuming all seventeen columns
  share one root cause just because they share one placeholder string.
- *"What would a downstream symptom of the un-fixed version have looked like?"*
  Not a crash. A dangerous-goods exposure report, or a customs-documentation
  completeness check, that silently includes rows it should have excluded: the
  worst kind of bug, because the output looks like a real, reasonable number.

---

### Story 3: the semi-additive trillion-dollar trap in FactInventorySnapshot

**Headline:** "Caught a naive inventory-value rollup that was off by roughly
500×, before it reached a dashboard, by sanity-checking the number against a
plausible real-world range."

**Situation.** `FactInventorySnapshot` records on-hand inventory value at
SKU × warehouse × customer grain, sampled repeatedly over time (weekly for
older history, daily for the most recent year), roughly 581 distinct snapshot
dates across the full history.

**Task.** Produce a trustworthy total on-hand inventory value, the kind of figure
that would plausibly headline a warehouse/inventory dashboard page.

**Action.** A plain `SUM(FactInventorySnapshot[OnHandValueUsd])` with no date
filter returned approximately **$1.3 trillion**, a number that fails a basic
plausibility check the moment you compare it against this company's actual scale
(total revenue across the whole multi-year history is about $2.04 billion, not
trillion). I didn't accept the number and move on; I traced it to the table's
grain: `OnHandValueUsd` is additive across SKU, warehouse, and customer at a
single snapshot date, but is **not** additive across snapshot dates. A
`SUM` with no date filter adds the same physical stock to itself once per
snapshot date it happened to be counted on, roughly 581 times over. The fix is a
point-in-time filter (take the value as of the most recent snapshot date on or
before the date being reported, never a range sum), which brought the figure
down to roughly **$2 billion**, consistent with the company's actual scale.

**Result.** A genuinely severe bug (off by roughly 500×) caught before it reached
a report, purely by asking "does this number make sense" rather than trusting a
`SUM` because it compiled and ran without error. The general pattern (point-in-time
filter, never a raw sum, for any semi-additive balance column) now applies to
every measure built on this table going forward.

**Likely follow-ups:**
- *"How did you know to suspect the number instead of trusting it?"* Order-of-
  magnitude sanity checks against something independently known (total revenue,
  headcount, fleet size) should be a reflex on any aggregate before it ships, not
  an afterthought. A number that's wrong by 3 orders of magnitude usually still
  "looks like a number": it doesn't announce itself.
- *"Would this bug have been caught by a unit test?"* Only if the test asserted
  a plausible range, not just that the query ran without error, which is itself
  worth saying explicitly, since "the query executed successfully" and "the query
  is correct" are different claims.

---

### Story 4: the TREATAS budget-vs-actual reconciliation gap

**Headline:** "Reconciled a budget-vs-actual discrepancy that turned out to be
two separate problems stacked on top of each other: a grain mismatch and a
recurring averaging error, in a table that had nothing physically wrong with it."

**Situation.** `FactTarget` stores planning figures (budget/forecast/plan/actual)
at Region × TradeLane × Month grain, with no physical relationship to any
transactional fact table, a deliberate design choice since targets are set at a
coarse regional level while operational facts run daily and per-location.

**Task.** Reconcile `FactTarget`'s own recorded "Actual" schedule-reliability
figure for Americas, June 2025, against the figure recomputed live from the
transactional data, to determine which one (if either) should go in a board
deck.

**Action.** Bridging `FactTarget` to the transactional facts required `TREATAS`
against `DimLocation[TradeRegion]`, and specifically that column, not the more
obvious-looking `DimLocation[Region]`, which encodes a finer geography
(`N America West`, `LatAm East`, and so on) that simply doesn't match
`FactTarget[Region]`'s five coarse values at all. I verified the match with
`DISTINCT` before building anything, rather than assuming the more granular-looking
column was the right one. With the correct bridge in place, the live-recomputed
figure for Americas/June 2025 came out to **66.22%**. `FactTarget`'s own stored
`Actual` scenario for the same KPI, region, and month read **74.71%**: an
**8.5-point gap**. I traced the gap and found it wasn't the bridge column (already
verified correct); it was that `FactTarget`'s own "Actual" row had itself been
populated as an **unweighted mean across trade lanes**, the exact same
naive-averaging error that a call-weighted pooled figure avoids: the identical
mechanism as the "never average an average" lesson, just recurring inside a static
planning table instead of a live DAX measure, which is why nothing in ordinary
model validation had caught it.

**Result.** Identified and explained an 8.5-point discrepancy between two
plausible-looking "correct" numbers, traced it to its actual two-part cause (a
subtle-but-verified grain bridge, plus a genuinely wrong averaging method baked
into the comparison data itself), and recommended the call-weighted recomputed
figure as the more defensible one for reporting, with the underlying fix flagged
as belonging upstream (in how `FactTarget`'s actuals get produced), not as a
one-off patch.

**Likely follow-ups:**
- *"How did you know which of the two numbers to trust?"* By understanding the
  mechanism behind each one, not by picking the number that "felt right." A
  pooled, call-weighted figure computed directly from the underlying events is
  more defensible than a static planning-table figure whose own construction
  method wasn't verified.
- *"Isn't this the same mistake twice: first almost joining the wrong column,
  then finding the comparison figure was wrong too?"* Yes, and that's the
  point worth making explicitly: real reconciliation problems are often two
  independent issues stacked together, and fixing only the more obvious one (the
  join) would have left you confidently reporting a still-wrong number.

### Exercise 39.5: the 15-second versions (20 min)

Write a one-to-two-sentence "headline" version of each story (the kind you'd say
in response to "any interesting bugs you've found recently?" in casual
conversation, not a formal interview answer). Time yourself saying each one out
loud; if any one runs past about 15 seconds, cut it down. These four headlines,
plus the four full STAR stories above, are what Day 41's mock interview will draw
on directly.

---

## Ship

Save all four stories, both lengths, to `06_portfolio/star-stories.md`. This file
is not private notes: write it at the polish level you'd want a hiring manager to
actually read, since a well-written version of this file is portfolio material in
its own right, not just interview prep.

```
git add .
git commit -m "Day 39: four STAR stories written from this project's real debugging history"
```

---

## Log

Which of the four stories felt weakest when you said it out loud, and specifically
why (too much DAX jargon, too little "why this mattered," or a Result that didn't
actually quantify anything)?

---

## Exit criteria

- [ ] All four STAR stories written in full (Situation/Task/Action/Result) with
      real, specific numbers from this project, no placeholder figures.
- [ ] Each story has a 15-second headline version you can say from memory.
- [ ] You can answer at least one likely follow-up question per story without
      re-reading your own notes.
- [ ] `06_portfolio/star-stories.md` exists at publish-ready quality.
- [ ] You said all four stories out loud at least once, timed.
