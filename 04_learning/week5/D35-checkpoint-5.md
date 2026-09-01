# Day 35: Checkpoint 5: end-to-end dry run

> Time: 3.5 h · Spaced recall 10 min · Part A 30 min · Part B 40 min · Part C 90 min · Log 15 min

No new mechanism today. Six days built a lot of machinery that only proves
itself under a real run: a scheduled Action, an incremental refresh policy, two
RLS roles, a performance pass, a TMDL-serialized model under source control, and
a landmine audit. Today you run all of it end to end, the same "verify what you
actually built" shape as Checkpoints 2 and 4.

---

## Spaced recall (10 min, closed book)

1. Name the four `LIVE_FEED.md` guarantees and which one makes an unattended
   scheduled run safe even after a missed day.
2. Which column bridges `FactTarget` to `DimLocation`, and what silently breaks
   if an RLS role filters the wrong one of `DimLocation[Region]` /
   `DimLocation[TradeRegion]`?
3. Name one VertiPaq cardinality anti-pattern this model actually had, and the
   fix.
4. What does a `.pbip`'s `.SemanticModel/` folder let a reviewer do that a
   `.pbix` cannot?
5. How many of `LANDMINES.md`'s 10 seeded landmines had you actually confirmed
   present in the live data by the end of Day 34, and how many were still open?

---

## Part A: rebuild the automation surface from memory (30 min)

Closed book except your predictions log. Without opening any file, write down:

1. `live-feed.yml`'s cron schedule, in both UTC and your local time, and the
   three directories it commits.
2. The RLS DAX filter expression for both roles you built on Day 31, including
   the `TREATAS`/`USERELATIONSHIP` piece that makes the second one actually work
   across the inactive relationship.
3. The incremental refresh policy's RangeStart/RangeEnd parameter values and
   which date column they bind to.
4. One VertiPaq anti-pattern Day 32 found in this specific model, and its fix.

Then check yourself against the actual files. Log every mismatch: a forgotten
detail, or a piece you believed was built and wasn't.

---

## Part B: explain the week in five short paragraphs (40 min)

No YAML, no DAX. One paragraph each:

1. **Unattended-automation risk.** What specifically makes it safe to let
   `live_feed.py` run on a schedule with nobody watching, and what would have
   made it unsafe if even one of the four guarantees didn't hold.
2. **Incremental refresh partitioning.** Why the partition boundary has to
   match a column the fact table is actually reliable on, and what happens to a
   refresh policy built against the wrong date column.
3. **RLS testing discipline.** Why "View As" on the role you just wrote is not
   sufficient proof it works, and what Day 31's inactive-relationship case
   specifically taught you to check instead.
4. **VertiPaq cardinality.** In your own words, why a high-cardinality column
   costs more than its row count suggests, and one column in this model you'd
   flag first in a review you didn't do yourself.
5. **TMDL source control.** What a `.pbip` diff actually shows a reviewer that
   a `.pbix` diff can't, and why that matters more for a calculation group or
   an RLS role than for an ordinary measure.

---

## Part C: end-to-end dry run (90 min)

Run this against your own project, not against this document. Every unchecked
box needs a one-line note: fix now, or a named future day.

### Fresh refresh
- [ ] Trigger `live-feed.yml` manually (`workflow_dispatch`) and confirm the run
      completes, commits new Parquet, and updates `manifest.json` without a
      manual step.
- [ ] Refresh the model against the updated manifest and confirm the new day's
      rows appear in a transaction fact table without a full historical reload.
- [ ] Confirm the incremental refresh policy's partition count matches
      expectations (one partition added, not one per table rebuilt from
      scratch) — check via Manage partitions, not by assuming the policy fired
      correctly.

### RLS re-test
- [ ] Re-run both roles' View As tests from Day 31, including the specific
      inactive-relationship case that failed before `USERELATIONSHIP` (or the
      dedicated `FactTarget` rule) was added.
- [ ] Confirm a role with no matching rows (a `TradeRegion` or customer with
      zero visible data) shows a genuinely empty report, not an error and not
      an unfiltered fallback to everything.
- [ ] Confirm RLS survives the fresh refresh above — a role built before an
      incremental refresh add can silently stop covering the newest partition
      if it wasn't written against the right column.

### Performance benchmark, re-run
- [ ] Re-run Performance Analyzer on all five report pages from Week 4 and
      compare against Day 32's baseline numbers — flag any visual that
      regressed by more than the day's own stated threshold.
- [ ] Confirm the anti-pattern fixes from Day 32 are still present after this
      week's other changes (an RLS role or a TMDL merge can reintroduce a
      bidirectional relationship or an unnecessary calculated column without
      anyone noticing).

### Landmine reconciliation
- [ ] Re-run Day 34's checklist against the current data and confirm the
      confirmed/open landmine count from the spaced-recall answer above is
      still accurate — the live feed adds real new rows daily, and a landmine
      seeded only in the frozen history can behave differently once live rows
      are mixed in.

---

## Ship

Commit any same-day fixes Part C turned up, plus a `06_portfolio/notes-week5-dry-run.md`
holding Part B's five paragraphs and Part C's full checklist with fix notes —
this is the artifact Week 6's portfolio write-up and STAR stories will draw the
"I automated and then verified a production pipeline" material from directly.

```
git add .
git commit -m "Day 35: Checkpoint 5 - end-to-end dry run, Week 5 complete"
```

---

## Log

What clicked / what did not / what to re-ask. For this checkpoint specifically:
which part of the dry run exposed something that looked fine in isolation on
its original day but broke once combined with a *later* day's change (an RLS
role plus an incremental refresh, a TMDL merge plus a performance fix)?

---

## Exit criteria

- [ ] Part A rebuilt from memory, checked against the real files, mismatches
      logged with a reason for each.
- [ ] Part B's five paragraphs written, specific to this project, not generic
      Power BI advice.
- [ ] Part C run in full; every unchecked box carries a fix note.
- [ ] The scheduled Action, the incremental refresh policy, both RLS roles, the
      performance fixes, and the TMDL-serialized model all still work together
      after this week's full set of changes, verified in one sitting rather than
      assumed from each day's individual checkpoint.
- [ ] Week 5 committed in full: automation, refresh policy, RLS, performance,
      deployment pipeline, landmine audit, and this checkpoint.
