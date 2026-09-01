# Day 33 — TMDL, `.pbip`, and a real branch-and-PR workflow for model changes

> Time: 3 h · Spaced recall 10 min · Concept 40 min · Drill 70 min · Ship 40 min · Log 15 min

Every measure, relationship and RLS role you've built this week lives inside
a `.pbix` — a single opaque binary file that git can store but cannot
meaningfully diff. Today that changes. This is also, like Day 29, not a
hypothetical: `03_powerbi/data_quality_findings.md` §4 lists **"TMDL export
of the finished model into this folder"** as still-pending, real, unfinished
project work. Today is that work.

---

## Spaced recall (10 min, closed book)

1. Why does an RLS role filter need its own explicit rule on `FactTarget`,
   separate from the `DimLocation`-based rule that covers most of the model?
2. What is the difference between a calculated column and a measure in terms
   of when each is evaluated, and why does that difference matter for
   VertiPaq memory?
3. Name the two things `data_quality_findings.md` records as "still open, not
   part of this pass" besides the TMDL export itself.
4. What did the relationship audit find and fix on `FactContainerMove`, and
   why didn't `validate.py`/`crosscheck.py` catch it (13 of 14 gates still
   passed)?
5. State the incremental refresh archive/incremental window sizes from Day
   30, and which column each table's partition boundary is built on.

---

## Concept

### What `.pbip` actually is

Power BI Desktop's **"Save as → Power BI Project (.pbip)"** replaces one
binary `.pbix` with a folder of plain text and JSON, split into two halves
that version-control independently:

```
yLogistics_Live.Report/         ← pages, visuals, layout, bookmarks
yLogistics_Live.SemanticModel/
    database.tmdl
    model.tmdl
    expressions.tmdl
    relationships.tmdl
    cultures/en-US.tmdl
    tables/
        DimCustomer.tmdl
        FactShipment.tmdl
        ... one file per table
```

This is not a hypothetical layout — it's the real structure your own model
takes the moment you do this. **TMDL** (Tabular Model Definition Language) is the text
format inside those `.tmdl` files: every table, column, measure, relationship
and role is a small, human-readable block. This is the whole point — a
`.pbix` diff is "binary files differ," telling you nothing; a `.tmdl` diff is
actual lines of DAX and metadata, reviewable the same way you'd review a
Python change.

### Why the repo is already set up for this

Check `.gitignore` — `03_powerbi/*.pbix` and `03_powerbi/.pbi/` are already
excluded. That is not an oversight, it is a decision already made on your
behalf: **the `.pbix` itself is never meant to be the thing under version
control here.** Desktop still needs it locally to actually open and edit the
model, but the artifact that goes in git is the `.pbip` + its two folders.
Committing the `.pbix` alongside them would defeat the purpose twice over —
it's both redundant with the TMDL (Desktop regenerates it from the folders)
and it reintroduces the exact opaque-binary-diff problem TMDL exists to
solve.

### What a real diff looks like, using today's own fixes

Day 32 had you remove Auto Date/Time bloat. In TMDL, that change is visible,
reviewable, and small. Before — one of 14 relationships tying a raw
timestamp to its own private hidden calendar:

```tmdl
relationship 58a1e260-9ab8-4b94-9450-2f6e117459c1
	joinOnDateBehavior: datePartOnly
	fromColumn: FactContainerMove.EventTs
	toColumn: LocalDateTable_10f18e27-9894-40cd-af4b-7aa1f7ed2e78.Date
```

After — the same column relating to the one real `DimDate`, via its already
existing `EventDateKey` sibling instead:

```tmdl
relationship EventDateKey_to_DimDate
	fromColumn: FactContainerMove.EventDateKey
	toColumn: DimDate.DateKey
```

A reviewer reading this diff sees exactly what changed and why, without
opening Power BI Desktop at all. The same is true of measures: Day 14's
calculation group becomes one `.tmdl` file with five small, individually
diffable `calculationItem` blocks; a display-folder reorganisation across 30
tables becomes a mechanical, greppable multi-file diff instead of an
unreviewable "trust me" binary change.

**One honest limit, worth stating rather than glossing over:** TMDL solves
the *semantic model* half beautifully. The `.Report/` folder's page and
visual layout is still large, auto-generated JSON — every visual's exact
pixel position, every bookmark's full state. Moving one card 3 pixels can
produce a sprawling diff that says nothing useful. Treat `.SemanticModel/`
changes as the unit you actually review line-by-line; treat `.Report/`
changes as "trust the rendered preview, don't hand-parse the JSON."

### The workflow: branch per model change, PR to review the diff

Power BI Desktop can open a `.pbip` directly from any git branch checkout —
no import/export step, no "publish then pull" dance. That makes an ordinary
software branching workflow apply here with almost no adaptation:

1. **Branch per change.** `git checkout -b day31-rls-roles` before opening
   Desktop, exactly like you would before touching any other code — one
   feature, one branch, same discipline Weeks 1–4 already put into commit
   messages naming the day's specific deliverable.
2. **Edit in Desktop, save as `.pbip`.** Desktop writes straight back into the
   `.tmdl` files on disk as you work — there is no separate "export" step to
   remember.
3. **Diff before committing.** `git diff --stat 03_powerbi/` to see which
   tables/relationships/measures actually changed, before `git add`. This is
   your own first review pass, and it catches the same class of mistake Day
   29's `git add .` discipline was built around — an unrelated table getting
   swept in because Desktop touched its `lineageTag` on open, for instance.
4. **PR, review the `.SemanticModel/` diff specifically.** A reviewer (even a
   future version of yourself) reads the measure/relationship/role changes as
   text, the same way they'd review a DAX snippet pasted into a Slack
   message — because that is now literally what it is.
5. **Merge, and Desktop on `main` picks it up on next open.** No republish
   step, no separate deployment pipeline needed to get a reviewed model
   change into the file Desktop actually opens.

**The one real constraint this doesn't remove:** Desktop can only have one
process actively editing a given `.pbip`'s model at a time — there is no
live co-authoring the way Word or Excel offers. Branch-per-change isn't just
good hygiene here, it's what makes concurrent model work possible at all
without two people's Desktop sessions silently clobbering each other's
`.tmdl` files on disk.

### Where this connects to what you've already built

Every calculation group item from Day 14, every measure from Week 3, every
RLS role and its `TREATAS` rule from Day 31 — all of it becomes reviewable
text the moment the model is under this workflow. A colleague (or an
interviewer looking at your portfolio) can read the actual DAX of
`Actual Schedule Reliability (via TREATAS)` in a diff, not just take your
word for what the model contains. That is the entire pitch for treating a
semantic model as source code rather than as a deliverable you hand over and
hope nobody has to modify later.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 33.1 — do the actual export (30 min)
Save the live model as `.pbip` into `03_powerbi/` — this is the first time
this model has been exported to TMDL, per `data_quality_findings.md` §4
("TMDL export... still pending"), so there is nothing to replace, only to
create. Predict, before opening any `.tmdl` file, whether the relationship
count you'll find matches 108 (the audited figure `data_quality_findings.md`
§3 states after its fixes: "108 total, was 81") — then check
`relationships.tmdl` and count `relationship` blocks yourself.

### Exercise 33.2 — read a real diff (20 min)
Make one small, deliberate model change — rename a display folder, or add a
measure description — commit it, then run `git diff HEAD~1 --
03_powerbi/.../tables/<table>.tmdl`. Confirm the diff shows exactly the lines
you changed and nothing else. Now open the `.Report/` folder's page layout
JSON for any page and look for what changed there even though you touched
nothing visual — explain in 1–2 sentences why it's not zero.

### Exercise 33.3 — branch-per-change, for real (15 min)
Create a branch, make a model change in Desktop, save, and diff it against
`main` before merging. Predict whether Desktop touched any file you didn't
intentionally edit (a `lineageTag`, a `culture` file, an ordering change) —
then check. This is the same "predict, then verify the diff is what you
expect" discipline as Exercise 29.1, one layer up the stack.

### Exercise 33.4 — the review that would have caught the mis-wired relationship (15 min)
Look at `FactContainerMove`'s relationship to `DimDate` in the current
(fixed) `relationships.tmdl`. Write two sentences: what would a PR reviewer
reading only the `.tmdl` diff of the original bug (joined on
`FactContainerMoveKey` instead of `EventDateKey`) have been able to catch
just from the column names in the diff, without running any DAX at all?

---

## Ship

Commit the real `.pbip` export to `03_powerbi/` — the first TMDL export this
model has had, closing out `data_quality_findings.md` §4's last open item.
Add a short `03_powerbi/README.md` documenting the branch-per-change
workflow from the Concept section, so the next person to touch this model
(including future you) doesn't have to rediscover it.

```
git add .
git commit -m "Day 33: model exported as .pbip/TMDL, branch-and-PR workflow documented"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] `.pbip` and its `.SemanticModel`/`.Report` folders exist in
      `03_powerbi/`, reflecting the current, fixed model state (108
      relationships, matching `data_quality_findings.md` §3's audited figure).
- [ ] You produced and read at least one real `.tmdl` diff, and can state
      what it shows that a `.pbix` diff never could.
- [ ] You can explain, in one sentence, the one honest limitation of this
      workflow (the `.Report/` layout JSON) and why it doesn't undermine the
      `.SemanticModel/` half.
- [ ] `03_powerbi/README.md` documents the branch-per-change workflow.
- [ ] Predictions recorded, misses annotated.
