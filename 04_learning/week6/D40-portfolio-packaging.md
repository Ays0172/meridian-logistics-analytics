# Day 40: Packaging the project, case study, screenshots, and the portfolio README

> Time: 3 h · Spaced recall 10 min · Concept 30 min · Drill 100 min · Ship 25 min · Log 15 min

Six weeks of real, checkable work is worth nothing to a hiring manager who never
sees it framed as a story. Today is not new analysis: it is packaging what
already exists (the five dashboards, the STAR stories, the case memos, README §6's
verified numbers) into the two artifacts that actually get read: a case-study
writeup and a portfolio README, plus the screenshots and captions that make both
credible instead of just claimed.

---

## Spaced recall (10 min, closed book)

1. Name the five report pages (Week 4) and which one is built to be "the thing you
   put in front of a CFO."
2. What are this project's headline numbers, from README §6, schedule
   reliability, OTIF, perfect order rate, revenue per FFE headhaul/backhaul, total
   revenue, and revenue CAGR?
3. What does `.pbip`/TMDL source control let you show in a portfolio that a
   `.pbix`-only project cannot (Day 33)?
4. Pick one of Day 39's four STAR stories and state its Result in one sentence,
   with the number in it.
5. Why does a raw screenshot of a dashboard, with no caption stating what the
   viewer is supposed to notice, usually fail to land the point it was meant to
   make?

---

## Concept

### The case-study writeup structure

A portfolio case study is not a lab report. Use a five-part structure, in this
order, because it mirrors how a reader's attention actually decays: lead with
the payoff, not the methodology:

1. **The headline claim:** one sentence, with a number in it. "Built a
   19-dimension, 11-fact logistics analytics platform (7.5M rows) and found an
   8.5-point discrepancy between a budget system's stored actuals and the
   underlying transactional data" beats "I built a Power BI project about
   logistics."
2. **The problem:** 2-3 sentences on what the project set out to answer (five
   KPI domains across ocean/landside/warehouse/air freight) and why a synthetic,
   seeded dataset is a legitimate choice for demonstrating the skill (reproducible,
   checkable, deliberately seeded with real-world data-quality defects rather than
   a scrubbed textbook example).
3. **What was built:** the model (19 dims, 11 facts), the measure library
   (~150 measures), the five dashboards, the SQL layer (Week 6), briefly. This is
   the section most candidates over-invest in; keep it to a paragraph, because the
   next section is what actually gets remembered.
4. **What was found:** this is the section to spend the most words on. Pull
   directly from Day 39's STAR stories and Day 37's case memos: the mis-wired
   relationship, the `"#NA"`-vs-`BLANK()` bug, the semi-additive trillion-dollar
   trap, the TREATAS budget-reconciliation gap. Each one gets a sentence of
   Situation, a sentence of Action, a sentence of quantified Result.
5. **What it demonstrates:** one closing paragraph connecting the specific
   findings to general skill: you can debug a model, not just build one; you know
   when a number that "looks fine" needs a second look; you can reconcile
   conflicting sources rather than pick the more convenient one.

### What to capture, and why each shot earns its place

A screenshot with no reason for existing (a plain page with no caption, no
highlighted number) is worse than no screenshot: it takes up space a reader's
attention could have spent on the numbers. Every shot on the list below has a
specific job:

| Capture | Why it earns a place |
|---|---|
| The Executive/cross-cutting page (Day 27), full-page | The "hero" image: this is what a reader who only looks at one screenshot should see. Caption it with the headline number it's showing (e.g. schedule reliability or perfect order rate). |
| The Rotterdam/LA congestion story, on whichever page renders it | This is the single best "what would you put on an executive dashboard" answer this project produces (Day 11); a screenshot proves you actually built the visual that makes the arithmetic point, not just that you can describe it. |
| A drillthrough or bookmark interaction, as a short GIF | Static screenshots cannot show interactivity: a 5-8 second GIF of drilling from the exec summary into a domain page demonstrates UX work a still image can't. |
| The DAX formula bar for one non-trivial measure (the `TREATAS` budget measure, or the rolling-8-week reliability measure) | Proves the underlying technical work, not just the visual layer: a reader who can read DAX will trust the rest of the project more after seeing one real measure. |
| A `.pbip`/TMDL folder structure in an editor, or a `git log`/commit history screenshot | Shows the project is source-controlled like real team software, not a single `.pbix` file emailed around: a genuinely differentiating signal for a portfolio (Day 33). |
| An RLS "View As" screenshot showing two different roles seeing different data on the same page | Proves the security work is real and tested, not just configured and never verified. |

Name files with a convention a reader (or you, six months later) can navigate
without opening each one: `01-exec-summary.png`, `02-congestion-story.png`,
`03-drillthrough.gif`, `04-treatas-measure.png`, `05-source-control.png`,
`06-rls-viewas.png`, numbered in the order a reader should see them, not the
order you happened to capture them.

### The portfolio README, and leading with numbers

A GitHub README that opens with "This is a Power BI project I built to learn
DAX" gets scrolled past. One that opens with a table of verified numbers gets
read, because it makes a concrete, checkable claim in the first five seconds:

```markdown
# Meridian Logistics Analytics

A synthetic but industry-faithful logistics BI platform, 19 dimensions, 11 facts,
7.5M rows, seeded and reproducible, built to demonstrate real-world Power BI/DAX
and SQL analytics skill against a dataset deliberately built with real-world data
quality defects, not a scrubbed textbook example.

| Metric | Value |
|---|---|
| Schedule reliability (vessel vs published ETA) | 0.6598 |
| Delivery on-time rate | 0.9130 |
| Perfect order rate | 0.8574 |
| Total revenue, full history | $2,040,774,144 |
| Revenue CAGR, 2022→2025 | 5.78% |
| Revenue per FFE, headhaul / backhaul | $2,482.78 / $1,286.66 |

**Found and fixed while building this:** a relationship silently bound to the
wrong key, a text placeholder masquerading as BLANK() across five columns, a
semi-additive rollup off by roughly 500×, and an 8.5-point budget-vs-actual gap
traced to a naive average baked into a planning table. Full write-ups: [STAR
stories](06_portfolio/star-stories.md).
```

Notice the shape: the numbers table comes **before** the description of what
tools were used. A reader deciding whether to keep reading in the next five
seconds is deciding based on "does this person clearly know what they built," and
a specific, verified number does that faster than any adjective.

The rest of the README (below the fold) is the normal project-README material:
architecture, tech stack, how to run it, screenshots embedded inline with
captions, a link to the case study and STAR stories for anyone who wants the full
depth. Keep that material genuinely below the numbers table, not above it.

---

## Drill

### Exercise 40.1, draft the case-study writeup (35 min)
Write the five-part case study in full, pulling directly from Day 37's case memos
and Day 39's STAR stories rather than writing new prose from scratch: you have
already done the hard writing; today is assembly and framing. Read it back and
time how long it takes to read the headline claim plus "what was found" section
alone: that combination should carry the whole story even if a reader stops
there.

### Exercise 40.2, build the shot list (20 min)
Using the table above as a starting point, write your own numbered shot list
(file name, one-sentence caption, and which section of the case study or README
each one supports). You do not need Power BI Desktop access to do this exercise;
the deliverable is the planned list with captions, ready to fill in once you have
the dashboards open. If any shot on your list doesn't map to a specific sentence
in your case study, cut it: an uncaptioned, unconnected screenshot is clutter.

### Exercise 40.3, write the portfolio README (30 min)
Draft the full README: the numbers table (verbatim from README §6, no rounding
changes), the one-paragraph "found and fixed" teaser linking to
`06_portfolio/star-stories.md`, architecture/tech-stack section, and a
placeholder for each screenshot from 40.2 with its caption already written in.
Predict, before you write it, how many words the whole README should be to stay
readable in one scroll. Then check your draft against that number and cut if
you overshot.

### Exercise 40.4, the 60-second elevator pitch (15 min)
Write and time a 60-second spoken version of the whole project, not read from
the README, said the way you'd answer "so what have you been working on lately?"
at the start of an interview. It should compress the headline claim, one of the
four STAR findings (your strongest), and one sentence on what you'd build next.
This is the spoken opening Day 41's mock interview will expect you to have ready.

---

## Ship

Write `06_portfolio/case-study.md` (Exercise 40.1) and `06_portfolio/README.md`
(Exercise 40.3, with the shot list from 40.2 as inline placeholders). Save the
elevator pitch script from 40.4 at the top of `06_portfolio/README.md` or in a
separate `06_portfolio/pitch.md`: either is fine, but it should exist somewhere
you'll actually reread before an interview.

```
git add .
git commit -m "Day 40: portfolio case study, README, and shot list drafted"
```

---

## Log

What clicked / what did not / what to re-ask. Note specifically which of the four
STAR findings you chose to lead with in the 60-second pitch, and why that one over
the other three.

---

## Exit criteria

- [ ] `06_portfolio/case-study.md` exists, following the five-part structure, with
      "what was found" as its longest section.
- [ ] `06_portfolio/README.md` exists, leads with a verified numbers table before
      any tooling description, and links to the STAR stories.
- [ ] A numbered, captioned shot list exists, with every entry mapped to a
      specific sentence it supports.
- [ ] You can deliver the 60-second elevator pitch from memory, timed, without
      reading it.
- [ ] Predictions recorded, misses annotated.
