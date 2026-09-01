# Day 38: solutions

This is a worked example of the self-audit and gap-answer exercises, not a graded
answer key, your own honest percentages in Exercise 38.1 are the real deliverable.
Use this to calibrate tone and depth, not to copy numbers.

---

## Spaced recall answers

1. Ocean Liner (D23), Landside (D24), Warehouse & Inventory (D25), Air & LCL
   (D26), Executive/cross-cutting summary (D27), matching the five KPI domains
   split in `00_docs/KPI_DICTIONARY.md`.
2. 8 refreshes/day on Pro, 48/day on Premium Per User. A once-daily live feed
   append needs exactly one of those slots, so Pro licensing is not a constraint
   for this project's cadence: it would only bind if the feed moved to
   intraday/hourly appends.
3. `.pbip`/TMDL stores the model as readable text files (one per table/measure/
   relationship), so `git diff` shows exactly what changed in a model edit,
   merge conflicts are resolvable, and code review is possible, none of which a
   binary `.pbix` supports.
4. Example: a per-customer RLS role filtering `DimCustomer[CustomerCode] =
   USERPRINCIPALNAME()` (or a mapped email-to-customer table), propagated down
   through the relationships to every fact table transitively.
5. A calculation group is a table of `SELECTEDMEASURE()`-based calculation items
   that reshape any measure in a visual (MTD/YTD/PY, etc.) without duplicating
   measures. It belongs to **"model the data"**: it's a modelling-layer object,
   even though its effect is visible in "visualize", a distinction worth having
   ready if asked to categorize it.

---

## Worked example, Exercise 38.1, self-audit

A sample honest self-audit (yours will differ; this shows the *shape*, not a
target to match):

| Domain | Gut estimate | Checklist count | Gap between the two |
|---|---|---|---|
| Prepare the data | "80% confident" | 6/7 exit-criteria boxes still true without re-reading | close, gut was accurate |
| Model the data | "90% confident" | 24/31 boxes across Weeks 2–3 | gut over-estimated, TREATAS and calc-group syntax had gone rusty |
| Visualize/analyze | "60% confident" | 11/14 boxes | gut under-estimated, most of what felt shaky was AI-visual-adjacent content (which was never covered, so the low confidence is *correct*, not a training gap) |
| Deploy/maintain | "50% confident" | 9/18 boxes | matches: this is genuinely the least-drilled domain, since Week 5 is furthest from Week 6 and covers the widest range of Service-UI mechanics that don't stick without repetition |

**What this kind of table is for:** the gap between gut-feel and checklist-count is
the actual finding. A domain where your gut matches the checklist means your
self-assessment is calibrated, trust it. A domain where gut and checklist
disagree is where you're either overconfident (dangerous in an interview) or
underconfident (wastes prep time re-studying something you actually know). The
"Deploy" row above matching in the worked example, with a genuinely low score, is
a legitimate finding, not a failure, Week 5 was true content deepest, spread
across the most Service-UI mechanics, and mechanics fade fastest without
repetition. That itself is worth a sentence in the log: "re-skim Day 30–33 the day
before any interview that mentions deployment," which is a much more useful output
than a vague "I should review everything."

---

## Worked example, Exercise 38.2/38.3, a full gap answer

**Gap chosen:** Dataflows (Gen1/Gen2).

**Two-sentence plan (38.2):** Build one Gen1 dataflow in a Power BI Service
workspace that reproduces the `DimDate` and `DimLocation` cleaning steps already
written in Power Query for Week 1 Days 4–5 (trim/proper-case the location name,
conform the two country-name spellings), reusing logic I've already built and
verified once makes the comparison meaningful rather than starting from
nothing. Estimate: half a day, since the M code is already written and the new
part is purely "where does it live and how does refresh scheduling differ."

**Written interview answer (38.3):**

> "I haven't built a production dataflow, everything in my portfolio project uses
> Power Query inside the .pbix/.pbip directly. I understand the value
> proposition: centralising the cleaning logic once so multiple downstream models
> can share it instead of each one re-implementing the same transform, which
> matters a lot at the point a company has more than one Power BI model reading
> similar source data. My project actually has a concrete case for this, the
> location-name cleaning and country-spelling conformance I built in Power Query
> for the semantic model would be exactly the kind of logic worth centralising
> into a dataflow if a second model needed the same dimension. I'd plan to build
> that as my next concrete step, since I already have the M code and just need to
> relocate and test it."

Notice the shape: one sentence of honest gap, one sentence of the underlying
concept stated correctly (proving you understand *why* the feature exists even
without hands-on time), one sentence connecting it to something concrete you
already built, one sentence of a specific next step. That is a stronger four
sentences than a vague "I'm familiar with dataflows" that invites a follow-up
question you can't answer.

**Self-check:** read your own 38.3 answer out loud. If it takes longer than about
30 seconds to say, it's over-explaining, trim to the four-sentence shape above. If
it doesn't name a concrete adjacent thing you actually built, go back and find one;
almost every PL-300 gap in this course has *some* adjacent Week 1–5 deliverable to
point at, and finding that connection is the actual point of the exercise.
