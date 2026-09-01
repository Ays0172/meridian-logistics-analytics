# Day 32 — VertiPaq cardinality, Performance Analyzer, and star-schema anti-patterns

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 80 min · Ship 30 min · Log 15 min

Every day so far has been about getting a number right. Today is about what
that number costs to compute, and what a badly-shaped model costs before a
single measure ever runs. Some of what you'll audit today is already fixed —
verified in `03_powerbi/data_quality_findings.md`. Some of it is a real,
unresolved decision this project has been carrying forward, and today is
where you make it.

---

## Spaced recall (10 min, closed book)

1. What DAX pattern gates a fact table with no physical relationship to the
   dimension you need, and what did Day 31 add to that pattern to make it
   work as a *security* rule rather than a measure?
2. Why does an RLS role filtering `DimLocation[TradeRegion]` fail to restrict
   a fact table's *inactive* location role-playing relationship, and what
   would a member see instead of a restricted number?
3. Why does this schema's incremental refresh design skip the "detect data
   changes" accelerator, and what does it rely on instead?
4. Name the table `factio.py` routes sentinel-dated (`-1`) rows into, and why
   that bucket can never be reached by a normal recent-months refresh window.
5. What is the practical difference between a calculated column and a
   measure, in terms of when each is evaluated?

---

## Concept

### How VertiPaq actually spends memory, in one sentence

VertiPaq is a **column store**: every column is compressed independently,
mostly by building a dictionary of its **distinct values** and storing each
row as a small integer pointing into that dictionary, then run-length- and
bit-packing the result. **The size of a column's dictionary — its
cardinality, not the table's row count — is what drives memory and scan
cost.** A column with 5 distinct values across 7.5M rows compresses to almost
nothing. A column with 400,000 distinct values across the same 7.5M rows
needs a dictionary nearly as large as the data itself, and every scan that
touches it pays for that dictionary whether or not the visual needed most of
those distinct values.

### Where this model's cardinality actually lives

Three concrete offenders, checkable directly against the real schema:

**Text business keys.** `TaskNo`, `OrderNo` on `FactWarehouseTask`,
`HouseBlNo` on `FactShipmentMilestone`, `BookingNo` on `FactBooking` — every
one of these is `dataType: string`, `summarizeBy: none`, and close to
one-distinct-value-per-row by construction (a business key exists precisely
to be unique). These need to exist for lookups and traceability, but they
should never be dragged into a visual that also aggregates a measure — doing
so forces VertiPaq to materialize one row per distinct key, defeating
aggregation entirely.

**Raw timestamp columns, and the hidden tables they silently create.** Eight
columns across three fact tables carry second-level `dateTime` precision:
`FactWarehouseTask.TaskStartTs`/`TaskEndTs`, `FactContainerMove.EventTs`,
`FactPortCall.PromisedEtaTs`/`AtaTs`/`AtdTs`/`BerthTs`/`UnberthTs` — eight
columns just from this list, and Auto Date/Time isn't limited to only these:
it fires on *any* `Date`/`DateTime`-typed column a visual touches, so other
date-typed dimension attributes (e.g. `DimCustomer.OnboardedDate`,
`ScdValidFrom`/`ScdValidTo`) can trigger it too. Each one is close to unique
per row — a timestamp to the second, across millions of rows, essentially
never repeats. Left with Power BI's **Auto Date/Time** setting on (the
default), each of these columns silently spawns its **own hidden calendar
table** — a `LocalDateTable_*`, duplicating a full
`DATE(2021,1,1)`–`DATE(2026,12,31)` calendar in miniature, with its own
Year/Quarter/Month/Day hierarchy, sitting alongside the one real,
purpose-built `DimDate` this model already has. Exactly how many you find in
your own model depends on which date-typed columns you've actually touched in
a visual so far — that's what Exercise 32.1 has you count.

The fix is two-part, and Exercise 32.1 has you verify whether it's still
outstanding: **turn Auto Date/Time off** (File → Options → Data Load →
uncheck it, or `Auto Date/Time` at the per-file level before deleting the
existing ones), then **relate each raw timestamp's actual date portion to
`DimDate`** the same way `TaskDateKey` already correctly does on
`FactWarehouseTask` — most of these tables already have a proper `*DateKey`
integer column sitting right next to the offending timestamp, so the
timestamp itself doesn't need a date relationship at all; keep it only for
duration math (`DATEDIFF(TaskStartTs, TaskEndTs, MINUTE)`), hide it from the
report view, and let the existing key column carry the calendar relationship.

**Decimal columns with wide value ranges.** `Revenue_usd`, freight rate
columns, `TargetValue`/`StretchValue`/`ThresholdValue` — real currency
amounts rarely repeat exactly, so these carry high cardinality by nature, not
by mistake. Nothing to "fix" here (you cannot compress away genuine
variation), but it is why `summarizeBy` was corrected from the TMDL default
of `Sum` to `None` on roughly two dozen columns model-wide
(`data_quality_findings.md` §3) — a raw column left summable invites a report
author to drag it straight into a visual instead of using the measure that
already exists for it, doubling the aggregation surface for no benefit.

### Performance Analyzer: how to actually read it

**Start Performance Analyzer** (View ribbon), **Start Recording**, then
interact with a page from Week 3–4's five-dashboard build — change a slicer,
switch a bookmark, whatever a real reader would do. Each visual reports three
numbers: **DAX query**, **Visual display**, **Other**. The one that matters
for model tuning is **DAX query** — that's storage-engine and formula-engine
time, the part a measure rewrite or a relationship fix can actually change.
A slow **Visual display** is a chart-type or formatting problem, not a DAX
problem, and no amount of measure tuning will fix it.

For the slowest DAX query on the page: right-click it → **Copy query**, then
run it in DAX query view (or DAX Studio if you have it) with **Server
Timings** on. That splits the number further into **Formula Engine** (FE —
single-threaded, running the actual DAX logic) versus **Storage Engine** (SE —
the columnar scans, and how much of that scan hit VertiPaq's own result
cache). A query that is FE-heavy usually means the DAX itself is doing too
much row-by-row work (an iterator over something that should have been
pre-aggregated); one that is SE-heavy and cache-cold on every run usually
means the model's cardinality or relationship shape is forcing an expensive
scan repeatedly. Which one you're looking at decides whether today's fix is a
DAX rewrite or a model change — measuring first is what stops you from
"optimizing" the wrong half.

### Star-schema anti-patterns, checked against what's real in this model

**Bidirectional relationships — one candidate, still undecided.**
`data_quality_findings.md` flags `DimWarehouse ↔ DimLocation` as bidirectional
and explicitly **not yet decided**. A bidirectional relationship lets a filter
on `DimLocation` (say, an RLS role from Day 31) reach back through
`DimWarehouse` into every fact table `DimWarehouse` touches — useful when you
genuinely want a location-level filter to constrain warehouse-scoped facts
too, dangerous when it creates an unintended second filter path into a table
that already reaches `DimLocation` some other way, producing the kind of
silently-wrong ambiguous-filter-context result Day 9's `ALL`/`ALLSELECTED`
distinction warned about, just one relationship hop further out. Today is
where you actually decide this, not defer it again (Exercise 32.3).

**A relationship bug already found and fixed, worth knowing about even
though it's resolved:** `FactContainerMove` was originally joined to
`DimDate` on its own surrogate key (`ContainerMoveKey`, a row-sequence
identifier) instead of `EventDateKey` — a relationship that *runs* without
error, but because `ContainerMoveKey` and `DimDate[DateKey]` don't share a
value domain at all (a row number versus a `yyyymmdd` integer), it silently
returns **zero rows on any date filter** rather than something merely
mis-filtered. It was caught during the relationship audit that took the model
from 81 to 108 relationships, and it is exactly the shape of bug Performance
Analyzer will not find for you — it doesn't make a query slow, it makes a
query wrong, and it fails *totally* rather than subtly, which is actually the
easier version of this bug to catch once you know to look. Cardinality tuning
and correctness auditing are different disciplines that happen to use some of
the same tools.

**Calculated columns versus measures.** A calculated column is computed once,
per row, at refresh time, and stored — it adds directly to a table's on-disk
and in-memory size, at that column's own cardinality. A measure is computed
on demand, in whatever filter context a visual creates, and costs nothing at
rest. `SkuAbcClassDynamic` (Day 13) is a case where a calculated column was
the *right* call despite this cost — its quadratic ranking logic is too
expensive to recompute per visual interaction. Most of what a report author
is tempted to add as a calculated column (a concatenated label, a bucketed
range, a flag) belongs as a measure instead, precisely because it does *not*
need Day 13's justification for paying the storage cost.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 32.1 — the Auto Date/Time audit (25 min)
Open the model and count the actual `LocalDateTable_*` hidden tables present
right now. Predict, before checking, whether the count will be exactly 8 (one
per raw timestamp column named above), lower (you haven't touched all of them
in a visual yet), or higher (Auto Date/Time also caught a date-typed dimension
attribute like `OnboardedDate`) — then check and note which. For each of the 8
raw timestamp columns, confirm whether a `*DateKey` sibling column already
exists on the same table that could carry the `DimDate` relationship instead.
Turn Auto Date/Time off, delete the resulting orphaned hidden tables, and confirm
report visuals that used a `LocalDateTable`'s hierarchy still work once
repointed at `DimDate`.

### Exercise 32.2 — Performance Analyzer on a real page (25 min)
Record a full interaction pass on one of Week 4's five dashboard pages.
Predict, before recording, which single visual will report the highest **DAX
query** time — pick your prediction based on which visual touches the widest
fact table or the most measures at once. Verify, then copy that visual's
query and check whether the time is FE-heavy or SE-heavy. State in one
sentence what kind of fix (DAX rewrite vs. model change) that result points
to.

### Exercise 32.3 — decide `DimWarehouse ↔ DimLocation` (20 min)
This relationship has been flagged, not decided, since the data-quality pass.
Build the case both ways in writing before choosing: what does making it
bidirectional enable (name a specific report scenario it would fix), and what
does it put at risk (name a specific fact table where an unintended second
filter path could produce a number nobody asked for)? Make the call, document
it in the Ship section below, and set the relationship's cross-filter
direction accordingly.

### Exercise 32.4 — rank columns by cardinality (10 min)
Using Power Query's Column Distribution view (the same tool from
`data_quality_findings.md`'s methodology), check the distinct-value count on
five columns: `FactBooking[BookingNo]`, `FactWarehouseTask[TaskStartTs]`,
`DimSku[SkuKey]`, `DimCustomer[CustomerCode]`, `FactShipment[Revenue_usd]`.
Predict their rank order by cardinality before checking, then verify. Which
of the five would you flag for hiding from the field list on cardinality
grounds alone, independent of whether it's also a business key someone might
legitimately need?

---

## Ship

Fix the Auto Date/Time bloat found in Exercise 32.1 (Auto Date/Time off,
orphaned `LocalDateTable_*` tables removed, raw timestamps hidden and
repointed via their sibling `*DateKey` columns). Make and document the
`DimWarehouse ↔ DimLocation` decision from Exercise 32.3 in
`03_powerbi/data_quality_findings.md` §4, moving it from "flagged, not yet
made" to a recorded decision with your reasoning — this is real,
already-pending project work, not a hypothetical exercise.

```
git add .
git commit -m "Day 32: Auto Date/Time bloat removed, DimWarehouse<->DimLocation bidirectional decision made and documented"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can state, without notes, why cardinality (not row count) drives a
      VertiPaq column's cost, using two real high-cardinality columns from
      this model as examples.
- [ ] The Auto Date/Time hidden-table count is verified against the model,
      and fixed if it was still outstanding.
- [ ] You ran Performance Analyzer on a real report page and can say, for its
      slowest visual, whether the bottleneck was FE or SE — and what that
      implies about the fix.
- [ ] `DimWarehouse ↔ DimLocation` has an actual, documented decision behind
      it, not just a flag.
- [ ] Predictions recorded, misses annotated.
