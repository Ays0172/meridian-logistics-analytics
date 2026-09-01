# Day 42: solutions

There is no single correct retrospective. This file shows a worked example of
each part at the honesty and specificity level to aim for, and a grading rubric
for your own Part C/D, which are the two sections most tempting to soften.

---

## Spaced recall answers

1. Transaction fact (`FactShipment`), periodic snapshot (`FactInventorySnapshot`),
   accumulating snapshot (`FactShipmentMilestone`).
2. The correlation between the per-row ratio and its own denominator determines
   the naive-average error size; calculation groups solved the "one measure needs
   five time-intelligence variants" multiplication problem.
3. 72 KPIs across 5 domains (Ocean liner, Landside, Warehouse & inventory, Air &
   LCL, Cross-cutting).
4. The Executive/cross-cutting page (Day 27) answers "is the company healthy."
   The Rotterdam/LA congestion event's full visual (the combo chart, the shaded
   window, the callout) lives on the **Ocean Liner** page instead (Day 23) —
   Day 27 deliberately keeps only a one-line footnote on the SCOR Reliability
   row of the Executive page, reasoning that duplicating the full callout
   across two pages would cost more in page-purpose clarity than it gains.
5. `.pbip`/TMDL gives a diffable, mergeable, code-reviewable text representation
   of the model; Power BI Pro allows 8 scheduled refreshes/day, PPU allows 48.
6. `FactTarget`'s stored actual reads 74.71%; the recomputed, correctly-bridged
   figure reads 66.22%, an 8.5-point gap.

---

## Worked example, Part B, Day 1 vs today

> On Day 1 I would have built a "% of total" measure with a plain `ALL()` and
> called it done. By Day 42, I know that's wrong the moment a slicer is on the
> page: `ALL` ignores the user's selection entirely, so the percentages stop
> summing to 100% the instant someone filters the report to one year, and nobody
> notices until a stakeholder adds up a column in their head. I now default to
> `ALLSELECTED` for anything a reader will expect to sum to 100%, and I can state
> exactly why in one sentence rather than just knowing "there's a difference."
> That's a small, specific thing, and it's a better answer than "I understand
> filter context better now" because it's checkable: I could rebuild both
> versions right now and show you the difference on real data.

**Why this works:** it names one specific, small, checkable capability rather than
a vague sense of overall growth: the same specificity Day 39's STAR stories asked
for.

---

## Worked example, Part C, candid weak spots

> 1. Week 5 is the one I'd feel least comfortable being interviewed cold about,
>    not because the content was hard, but because it's the furthest week from
>    today and the most UI-mechanics-heavy (Service refresh settings, RLS role
>    configuration screens) rather than concept-heavy, and UI mechanics fade
>    fastest without repetition. I'd re-skim Days 30-33 before any interview that
>    mentions deployment specifically.
> 2. My weakest Day 41 score was Q8 (the SQL averaging trap): I gave the right
>    mechanism but couldn't state the correlation-driven "why" cleanly under time
>    pressure, which is the exact distinction Day 9 spent real effort building. To
>    move it up a point: re-run Day 36's Exercise 36.2 and actually say the
>    explanation out loud three times until it's not something I have to
>    reconstruct live.
> 3. The DirectQuery/composite-model gap (Day 38) would actually block me from a
>    role at a company running Power BI over a live warehouse rather than
>    imported files: that's common enough to be a real risk. The dataflows gap
>    and the paginated-reports gap are genuinely fine to leave open for now; I've
>    never seen either come up as a hard requirement in the roles I'm targeting.
> 4. Being honest: the dynamic ABC segmentation measure from Day 13. It works; it
>    matches the reference values, but I built the ranking/cumulative-share DAX
>    from the pattern given rather than fully re-deriving why the quadratic
>    `FILTER`-inside-`ADDCOLUMNS` shape is necessary. I should rebuild it from a
>    blank model without looking, the way Checkpoint 2's Part A asked, before I'd
>    call it solid.

**Why this works:** every claim is specific enough to be falsifiable: a reader
(including future-you) could check each one and confirm or refute it. Compare
against a soft version: "I feel pretty good about most of it, Week 5 could use
some review" (technically not false, but useless as a diagnostic, because it
gives you nothing to actually go do).

---

## Grading your own Part C and D

Two checks, applied honestly to what you wrote:

**The specificity test.** For every sentence in Part C and D, ask: could someone
else check whether this is true? "I'm weak on Week 5" fails: there's nothing to
check. "I can't rebuild the Americas RLS role from a blank model without notes"
passes: you could sit down right now and find out if that's actually still true.
Rewrite any sentence that fails this test before moving on.

**The friend test.** Reread your own Part C answers and ask: if a close friend who
knows you well read this, would they nod and say "yeah, that's genuinely you being
honest," or would they say "you're being harder on yourself than the facts
support" or, more commonly, "you're letting yourself off easy there"? Both
directions are worth catching: an unnecessarily harsh self-assessment is as
useless for planning as an inflated one, because both give you a wrong signal
about where to actually spend the next month.

---

## What "done" looks like for Part D

A plan passes if every bullet has one thing in it that would be embarrassing to
still not have done in three months if you reread this file then. "Apply to
roles" with no date is not embarrassing to have skipped: it was never really a
commitment. "Apply to the first role by [specific date]" is. The whole value of
writing a retrospective instead of just thinking one is that it becomes a promise
you can check yourself against later; treat Part D that way, or don't bother
writing it down at all.
