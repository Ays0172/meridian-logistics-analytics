# Day 37: Case drills, business questions, timed, on the finished model

> Time: 3.5 h · Spaced recall 10 min · Concept 35 min · Drill 125 min · Ship 25 min · Log 15 min

Everything so far has been "build this measure" or "write this query", a known
target, a known right answer. A real analytics job is the opposite shape: someone
asks a vague, urgent question in a hallway or a Slack DM, and you have to translate
it into a metric, find the number, and hand back something a non-technical
stakeholder can act on, in one sitting, without a reference-answers file to check
against. Today is five of those, timed, using the model and (if you have reached
that point) the dashboards you built in Weeks 3–4.

---

## Spaced recall (10 min, closed book)

1. What is the difference between schedule reliability and delivery OTIF, and why
   does conflating them matter in a stakeholder conversation (Day 9)?
2. State the congestion event's dates, locations, and one quantified effect from
   `SCHEMA_CONTRACT.md` §3.3.
3. Why did sorting ports ascending by rolling reliability *fail* to surface the
   Rotterdam/LA crisis (Day 11), and what fixed it?
4. What does `FactTarget`'s own stored "Actual" scenario get wrong, and which day's
   drill made you find the correct recomputed figure (Day 13 / Day 36)?
5. What is the reefer free-time gap versus dry containers, and what did it do to
   reefers' share of demurrage charges (Day 9, spaced recall Q5)?

---

## Concept

### The shape of a case drill, and how it differs from a syntax drill

A syntax drill has one correct number and you either got there or you didn't. A
case drill has a **defensible answer**, not a single correct one: the grading
question is not "did you get 66.22%" but "did you notice it needed to be 66.22%
and not the number sitting in a stale planning table." That distinction is most of
what an interviewer or a manager is actually testing when they hand you a vague
business question.

Every drill below is graded against the same five-part skeleton. Use it out loud
in an interview, not just on paper:

1. **Define**: restate the ask as a specific, checkable metric. "Margin
   dispersion" is not a metric until you say whether you mean standard deviation,
   an interquartile spread, or the loss-making share.
2. **Locate**: name the exact table(s), column(s), and grain before touching a
   query. This is where the wrong-grain mistakes from Days 12–13 happen if skipped.
3. **Compute**: build it, pooled not naive by default (Day 9), sanity-checked
   against a number you already trust from Weeks 2–3 or README §6.
4. **Caveat**: state the one thing that could make this number misleading: a
   small sample (Day 11), a naive average hiding in the comparison data itself
   (Day 13/36), a landmine (`00_docs/LANDMINES.md`), a definitional mismatch.
5. **Recommend**: one sentence telling the stakeholder what to do, not just what
   the number is. A number with no action attached is not an answer to a business
   question.

Time yourself on each drill including all five steps. If you are still on step 2
when the clock runs out, that is real, useful information about where your
practice needs to go: note it in the Log, don't just extend the clock.

### Grading yourself honestly

For each drill, before reading the rubric, write down your five-part answer as if
you were saying it out loud to the person who asked. Then check it against the
rubric bullets. A rubric item you missed is worth writing a sentence about in your
log, not just ticking as "missed" and moving on, because the *reason* you missed
it (didn't know the table existed vs. knew but ran out of time vs. got the metric
definition wrong) is different information each time.

---

## Drill

### Case 37.1, the CFO asks about margin dispersion (25 min)

> "I keep hearing that the Rotterdam/LA congestion hurt us badly this summer, but
> our average margin barely moved. Did margin *dispersion* actually change for
> shipments touching those two ports, comparing the crisis window against the same
> calendar window a year earlier? I don't want the same 'the average hid it' story
> again. This time, show me you looked underneath it."

**What a complete answer needs:**
- A defined dispersion metric (standard deviation of `GrossMarginPct`, or the share
  of loss-making shipments, or an interquartile spread), pick one and say why.
- The right population: `FactShipment` filtered to shipments whose origin or
  destination port (`LocationKeyPol`/`LocationKeyPod` via `DimLocation`) is `NLRTM`
  or `USLAX`, for 14 Jul–14 Sep **2025** versus the same calendar window in 2024.
- A sanity check against the model-wide gross margin mean of 0.1802 and
  loss-making share of 2.26%: your crisis-window figures should sit worse than
  network baseline, and you should be able to say by how much.
- The caveat that demurrage revenue (a `FactFreightCharge` line, not a component of
  `FactShipment[GrossMarginPct]` unless your model rolls it up) rose sharply in the
  same window per `SCHEMA_CONTRACT.md` §3.3, so the honest answer may be "shipment
  margin compressed, but ancillary demurrage revenue partly offset it," not a flat
  story either way.
- A recommendation: does this justify a surcharge, a claim against the terminal, or
  neither?

### Case 37.2, a key account asks why their DIFOT dropped (20 min)

> "This is [a Global Key Account]. Our on-time-in-full rate is clearly worse this
> quarter than last. What happened, and is it going to keep happening?"

**What a complete answer needs:**
- The customer's `IsPerfectOrder` rate by quarter, `FactShipment` filtered to their
  `CustomerKey` (remember Day 6/Week 1: resolve to the SCD2-current version, or the
  version valid at shipment date, and say which you chose and why).
- A decomposition into components (`IsOnTime`, `IsInFull`, `NOT IsDamaged`,
  `IsDocumentationClean`) to identify which one is actually driving the drop,
  the same structure Case 36.3 used network-wide.
- A volume check before concluding anything: how many shipments is this customer's
  quarterly rate built from? Apply Day 11's lesson directly: a rate built on a
  handful of shipments is exactly the kind of number that looks dramatic and means
  nothing.
- A check for whether this customer's lanes or ports overlap the congestion window
  and locations, which would make the answer "you got caught in a network-wide
  event, not something specific to your account": a materially different message
  to send back.
- A one-sentence answer that names the driving component and states whether it's
  customer-specific or systemic.

### Case 37.3, ops asks whether to push for reefer free-time (20 min)

> "Reefers keep showing up in our demurrage numbers more than their share of the
> fleet would suggest. Before I go to the carriers asking for a longer free-time
> window on reefers, quantify how much exposure we're actually carrying."

**What a complete answer needs:**
- The baseline fact, stated with a number: reefers get 3 free days against dry
  containers' 5 (`DimEquipment.FreeDaysDemurrage`), and are roughly 8.7% of
  container moves but around 20% of demurrage charge value: state both shares,
  not just one, because the ask is specifically about *disproportion*.
- The join path: `FactFreightCharge` (`IsDemurrage = 1`) to `DimEquipment` via
  `EquipmentKey`, aggregated by `IsReefer`.
- An honest limitation: you cannot perfectly simulate "what if free time were 4
  days" without re-running the generator or building a day-by-day demurrage-tier
  model from `FactContainerMove[FreeTimeDaysUsed]`/`DemurrageDays`: say what you
  *can* estimate (how many currently-charged demurrage days fall in what would
  become the newly-free 4th day) and flag the rest as an estimate, not a fact.
- A recommendation that is proportionate to the evidence, "worth quantifying
  further with carrier-level data" is a legitimate answer when the model can't
  fully close the loop, and saying so is worth more than overclaiming precision.

### Case 37.4, finance asks which number goes in the board deck (30 min)

> "Our Q2 planning packet says Americas hit 74.7% schedule reliability against
> target. The dashboard you built says 66%. Which number is right, and why don't
> they match? I need an answer before Thursday's board prep, not just 'they're
> different.'"

**What a complete answer needs:**
- Reproduction of the exact gap: `FactTarget`'s stored `ACT` scenario for
  `KpiCode = 'OCN.REL.SCHED'`, `TradeRegion = 'Americas'`, June 2025 reads
  **74.71%**; the value recomputed live from `FactPortCall` via the
  `TradeRegion` bridge reads **66.22%**, an 8.5-point gap (Days 13 and 36 already
  built both sides of this; today's job is to explain it in one paragraph a
  finance director will trust).
- The mechanism: `FactTarget`'s "Actual" figure is itself an **unweighted mean
  across trade lanes**, not a call-weighted pooled figure, the same naive-
  averaging error Day 9 taught you to distrust, except this time it is sitting in
  a static planning table instead of a live measure, which is why it never got
  caught by anything you built in Week 2.
- A clear recommendation, not a shrug: the recomputed, pooled, call-weighted
  figure is the more defensible number for a board deck, and the fix belongs
  upstream, in how `FactTarget`'s `ACT` rows get produced, not in picking
  whichever number is more flattering this month.
- One sentence anticipating the obvious follow-up: "will this happen for other
  KPIs in `FactTarget`?" Yes, wherever the planning table's actuals were built
  as an unweighted roll-up across an uneven population, which is worth a
  standing check rather than a one-off fix.

### Case 37.5, the board wants one slide on lane recovery (30 min)

> "One slide: is trade-lane profitability recovering post-congestion? Headhaul and
> backhaul, before/during/after the crisis window."

**What a complete answer needs:**
- Pooled revenue per FFE (Day 9's lesson: never the naive per-shipment mean) by
  `DimVoyage[Direction]`, bucketed into three periods around 14 Jul–14 Sep 2025.
- An explicit correction for the fact that headhaul and backhaul are not
  comparable in absolute terms: backhaul revenue per FFE runs at roughly 0.52×
  headhaul structurally (`SCHEMA_CONTRACT.md` §3.2), so a raw side-by-side bar
  chart invites the wrong read. Index each direction to its own pre-congestion
  baseline (e.g., "backhaul recovered to 97% of its own pre-crisis rate") instead.
- A one-line customer-concentration caveat if the board is likely to ask "who's
  exposed": top-10 customers carry 27.8% of total revenue, so a lane-level story
  can be dominated by a handful of accounts, worth a footnote, not necessarily
  the headline.
- One slide-ready sentence: which direction recovered faster, by how much, and
  whether "recovering" or "still depressed" is the honest verdict as of the latest
  data.

---

## Ship

Write each case as a one-page memo in `06_portfolio/case-drills/case-3X-<slug>.md`
using the five-part skeleton (Define/Locate/Compute/Caveat/Recommend), your
timing, and the actual number you landed on. These are draft material for Day 40's
portfolio packaging and Day 41's mock interview; do not skip writing them just
because you said the answer out loud already.

```
git add .
git commit -m "Day 37: five timed case drills, memos written for portfolio"
```

---

## Log

For each of the five cases: time taken, which rubric step you were weakest on, and
whether the gap was knowledge (didn't know where the number lived), speed (knew but
too slow), or communication (had the number, answer wasn't stakeholder-ready).

---

## Exit criteria

- [ ] All five case memos written in `06_portfolio/case-drills/`, each following
      Define/Locate/Compute/Caveat/Recommend.
- [ ] You can state, from memory, the Americas schedule-reliability gap (74.71%
      stored vs 66.22% recomputed) and explain its mechanism in one paragraph.
- [ ] At least one case timing came in over budget, and you know specifically
      which step ate the time, not just "it took too long."
- [ ] You can name, without notes, the one caveat that most changes each case's
      recommendation (the small-sample risk in 37.2, the estimation limit in
      37.3, the naive-average-in-the-comparison-data trap in 37.4).
- [ ] Predictions/timings recorded, misses annotated.
