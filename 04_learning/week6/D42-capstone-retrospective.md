# Day 42: Capstone retrospective, six weeks reviewed honestly

> Time: 2.5 h · Spaced recall 15 min · Concept 15 min · Retrospective 95 min · Ship 20 min · Log 15 min

Forty-two days ago you didn't know what a filter context was. Today is not a new
skill: it's the last, and in some ways most important, discipline this course
has been building all along: looking at your own work honestly, without a
reference-answers file to check against, and deciding what's actually solid,
what's still shaky, and what comes next. Grade yourself the way you graded every
DAX measure since Day 1, against the real number, not against how you feel about
it.

---

## Spaced recall (15 min, closed book)

One question per week, if any of these takes more than a minute to answer, that
week is worth a re-skim before you finish today.

1. **Week 1**, what are the three fact-table shapes this model uses, and name a
   real table from this project as an example of each (you'll need this from
   Day 12 too, but the shapes themselves start in Week 1's modelling work).
2. **Week 2**, what determines how badly a naive average of a ratio errs, and
   what tool solved "one measure gets five time-intelligence variants for free"?
3. **Week 3**, how many KPIs does the measure library cover, and across how many
   domains?
4. **Week 4**, which of the five dashboard pages is built to answer "is the
   company healthy," and on which *other* page does the Rotterdam/LA
   congestion event actually get its full visual (Day 27 deliberately keeps
   only a one-line footnote on the health page itself — why)?
5. **Week 5**, what does `.pbip`/TMDL source control let you do that a `.pbix`
   file can't, and what's the daily-refresh limit on Power BI Pro licensing?
6. **Week 6**, state, without notes, the number that reconciles (or fails to
   reconcile) `FactTarget`'s stored actual against the recomputed truth for
   Americas, June 2025.

---

## Concept

### Why the retrospective is graded the same way everything else was

Every day of this course asked you to predict before you ran a query, then check
the miss. A retrospective is that same discipline applied to six weeks instead of
one exercise: write down what you think you know before you go check the actual
artifacts (the measures, the dashboards, the STAR stories, Day 41's mock scores),
then compare. The gap between what you assumed and what's actually true is the
real content of today, not the checklist itself.

### What "done" actually means for a capstone

A capstone isn't "I finished all 42 days." It's "I can point at specific,
checkable artifacts and specific, honest weaknesses, and I know which is which."
The difference matters in an interview: "I built a Power BI project" is a claim;
"I built a 150-measure library across five KPI domains, and I can tell you my SQL
window-function skills are newer and shakier than my DAX" is a credible one,
because it has texture an interviewer can probe and you won't collapse under.

---

## Retrospective

### Part A, the full skill checklist (30 min)

Go through every item below and mark it honestly: **Solid** (could rebuild from a
blank model today, unaided), **Rusty** (did it once, would need to re-read my own
notes), or **Gap** (never actually got comfortable with this).

**Week 1, modelling foundations**
- [ ] Can explain the domain (ocean/landside/warehouse/air freight) and this
      model's four business areas without notes.
- [ ] Can distinguish a fact table from a dimension table and state this model's
      grain conventions (surrogate keys, `-1` unknown member, `_doc`/`_usd` money
      pairs) from memory.
- [ ] Can write a Power Query cleaning step (trim/case/dedupe) for a specific
      landmine from `00_docs/LANDMINES.md`.
- [ ] Can explain why relationships need a single active path and what
      `USERELATIONSHIP` is for.
- [ ] Can explain SCD2 and point to `DimCustomer`'s implementation of it.

**Week 2, DAX semantics**
- [ ] Can state, unaided, why `CALCULATE` replaces rather than intersects filters.
- [ ] Can state the pooled-vs-naive averaging rule and what predicts the gap size.
- [ ] Can build a rolling trailing-window measure and explain why the window
      length matters.
- [ ] Can explain the three fact-table shapes and the semi-additive trap.
- [ ] Can explain `TREATAS` and name this project's real bridge-column gotcha.
- [ ] Can explain what a calculation group solves and its one sharp edge.

**Week 3, the measure library**
- [ ] Can state how many KPIs the library covers and across how many domains.
- [ ] Can name one measure per domain (ocean/landside/warehouse/air/cross-cutting)
      from memory.
- [ ] Can explain how Checkpoint 3 verified the library against README §6.

**Week 4, the five dashboards**
- [ ] Can name all five pages and which business question each answers.
- [ ] Can explain why the Rotterdam/LA congestion story's full visual lives on
      the Ocean Liner page (Day 23), not the Executive Summary, and what the
      Executive page carries instead (a one-line footnote, by deliberate
      design per Day 27).
- [ ] Can explain one UX decision from the Checkpoint 4 polish pass (a bookmark,
      a drillthrough, an accessibility fix).

**Week 5, automation, security, performance**
- [ ] Can explain the GitHub Actions live-feed pattern and what it automates.
- [ ] Can state the Pro vs PPU refresh limits and why they matter here.
- [ ] Can explain one RLS role you built and tested with View As.
- [ ] Can name one performance fix found with Performance Analyzer.
- [ ] Can explain what `.pbip`/TMDL buys a team over a `.pbix` file.
- [ ] Can name at least 6 of the 10 seeded landmines from memory.

**Week 6, SQL and interview readiness**
- [ ] Can re-derive at least one DAX measure in SQL and explain what transferred
      and what didn't.
- [ ] Can run through the five-part case-answer skeleton unaided.
- [ ] Can tell all four STAR stories, timed, without notes.
- [ ] Can state at least five genuine PL-300 gaps honestly.
- [ ] Scored Day 41's mock interview and knows the total and the weak spots.

### Part B, Day 1 vs today, concretely (15 min)

Pick one specific thing, a measure, a query, a diagnosis, you genuinely could
not have done on Day 1, and write two or three sentences on exactly what changed.
Not "I know more DAX now", something specific: "on Day 1 I would not have known
that a relationship returning zero rows on a date filter means the join is wrong,
not that the data is empty; I know that now because I traced it myself in
[Day 39's Story 1 / your own inherited-model exercise]." Specificity here is the
same discipline the whole course asked of your DAX, a vague claim is worth
nothing, a checkable one is worth a lot.

### Part C, candid weak spots (25 min)

No hedging in this section. Answer directly:

1. Which of the six weeks would you feel *least* comfortable being interviewed
   cold about right now, and why, knowledge, or just rust from time passed?
2. Pick your single weakest score from Day 41's mock (or, if you haven't run it
   yet, your gut sense of your weakest question type) and write exactly what you'd
   need to do to move it up one full point on the rubric.
3. Of the honest PL-300 gaps from Day 38, which one would actually block you from
   a job you'd want, versus which ones are genuinely fine to have as open gaps for
   now? Not every gap is equally urgent, say which is which and why.
4. Is there a measure, dashboard, or query anywhere in this project you built once,
   got working, and never actually understood at the level you understood
   everything else? Name it. (If the honest answer is "no," say that too, but
   check honestly before writing it.)

### Part D, what's next (25 min)

Write a concrete plan, not a vague intention. For each of the following, one or
two sentences with something specific and checkable:

- **A real-world dataset.** This project was seeded and synthetic on purpose, for
  reproducibility, the next one should not be. Name a specific real dataset
  (a Kaggle competition, an open-government logistics/transit dataset, a public
  company's investor-relations data) and one question you'd answer with it.
- **The live feed, kept running.** Day 29's GitHub Actions automation doesn't stop
  because the curriculum did, decide, specifically, whether you're going to keep
  it appending daily and whether you'll build anything new on top of the growing
  history (a genuinely new year-over-year comparison becomes possible only once
  the feed has run a full year).
- **Closing the PL-300 gaps that matter.** From Part C's answer, name the one gap
  you decided is actually urgent, and the specific first step to close it (not
  "learn dataflows", "build one dataflow reproducing the DimDate/DimLocation
  cleaning logic already written in Power Query," the way Day 38's worked example
  did it).
- **Interview applications.** A date, not a someday. If you've run Day 41's mock
  and scored above the "ready" threshold, name the date you'll apply to the first
  role. If you scored below it, name the date you'll re-run the mock, not the date
  you'll apply.

---

## Ship

Write `06_portfolio/retrospective.md` with Parts A–D in full, the checklist with
your honest Solid/Rusty/Gap marks, the Day-1-vs-today comparison, the candid weak
spots, and the concrete what's-next plan with real dates. This is the last file
this curriculum asks you to write, and it's the one most worth rereading in three
months to see whether the plan actually happened.

```
git add .
git commit -m "Day 42: capstone retrospective, six weeks reviewed, plan for what's next"
```

---

## Log

One paragraph: looking back at all 42 days, what single day or exercise changed
how you think about data the most, and why that one.

---

## Exit criteria

- [ ] The full Part A checklist completed honestly, no item skipped.
- [ ] Part B's Day-1-vs-today comparison is specific and checkable, not vague.
- [ ] Part C's candid weak-spots answers are actually candid, reread them and ask
      whether a skeptical friend would believe they're honest.
- [ ] Part D's what's-next plan has at least one real date in it, not just
      intentions.
- [ ] `06_portfolio/retrospective.md` written and committed.
- [ ] You know, right now, whether you consider this course complete for your
      purposes or whether there's a specific week you're going back to first.
