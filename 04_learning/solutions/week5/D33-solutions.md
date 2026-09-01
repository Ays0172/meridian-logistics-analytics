# Day 33 — solutions

---

## Spaced recall answers

1. `FactTarget` has no physical relationship to `DimLocation` at all (Day
   13's grain mismatch — region/month vs. daily/location) — an RLS filter on
   `DimLocation` has no path to reach it, so without an explicit `TREATAS`
   based rule on `FactTarget` itself, that table is left completely
   unrestricted by any location-based role.
2. A calculated column is computed once per row at refresh time and stored on
   disk, adding directly to the table's cardinality-driven memory footprint;
   a measure is computed on demand in whatever filter context is active and
   costs nothing at rest.
3. Three fact-to-fact bridge relationships, and the `DimWarehouse ↔
   DimLocation` bidirectional decision (Day 32 made this call).
4. It was joined to `DimDate` on its own surrogate key instead of
   `EventDateKey` — a relationship that runs without error and returns *some*
   number, just not one filtered by date correctly. Row counts stayed
   identical and 13 of 14 validation gates still passed because the bug is a
   *relationship-wiring* problem, not a data-generation problem — every
   checker that validates row counts, key uniqueness, or referential
   integrity within a table has nothing to say about which column a
   cross-table relationship happens to be drawn on.
5. Archive 4 years / incremental 13 months, partitioned on each table's
   primary date key (`BookingDateKey`, `ShipmentDateKey`,
   `BookingConfirmedDateKey`, `EventDateKey`, `AtaDateKey`, `ChargeDateKey`,
   `ActualPickupDateKey`, `TaskDateKey`, `SnapshotDateKey`) — chosen because
   it's the exact column `factio.py` already partitions the physical Parquet
   files by.

---

## Exercise 33.1 — do the actual export

**Prediction:** the export should show **108** relationship blocks — the
audited, current figure from `data_quality_findings.md` — not the stale
backup's 82 (which is itself close to the "was 81" starting count that
audit measured against, confirming the backup really is a pre-fix snapshot).
`grep -c "^relationship " relationships.tmdl` against the fresh export is the
direct check. If your count lands closer to 82, the export was taken from a
version of the model that hasn't picked up the relationship audit's fixes —
worth re-opening the live model and confirming those 27 additional
role-playing relationships and the `FactContainerMove` rewiring are actually
present before exporting again.

---

## Exercise 33.2 — read a real diff

A description-only or display-folder change on one table produces a diff
touching only that table's `.tmdl` file — a handful of added/changed lines
inside the relevant `column` or `measure` block, nothing else.

**Why the `.Report/` JSON changes anyway, even though nothing visual was
touched:** Power BI Desktop re-serializes report metadata (lineage tags,
internal object ordering, sometimes the file's own save timestamp or schema
version marker) on every save, regardless of what you actually edited. This
is the concrete version of the Concept section's "trust the rendered preview,
don't hand-parse the JSON" warning — a nonzero `.Report/` diff after a
semantic-model-only change is expected noise, not a sign something you didn't
intend to change actually changed in a way that matters.

---

## Exercise 33.3 — branch-per-change, for real

Expect at least a `lineageTag` touch or two even on tables you didn't
directly edit — Desktop assigns and sometimes refreshes these GUIDs as part
of its own internal bookkeeping on save, independent of your actual change.
This is cosmetic and safe to include in the commit; the check that actually
matters is whether any table's **columns, measures, or relationships**
changed beyond what you intended — if `git diff` shows a `column` block with
a different `dataType`, `summarizeBy`, or a relationship's `fromColumn`
changed on a table you never opened, that is a real problem worth
investigating before merging, not cosmetic noise to wave away.

---

## Exercise 33.4 — the review that would have caught the mis-wired relationship

**What a reviewer could have caught from the diff alone:** the original,
buggy relationship's TMDL block would show
`fromColumn: FactContainerMove.FactContainerMoveKey` joined to
`toColumn: DimDate.DateKey` — a surrogate primary key column joined directly
to a date dimension's key. Any reviewer who knows this model's convention
(surrogate keys are `<Table>Key`, date foreign keys are `<Something>DateKey`
— README §7) would recognise on sight that a `*Key` column has no business
relating to `DimDate` at all; every other fact-to-`DimDate` relationship in
the file joins on a column literally named `*DateKey`. **The bug is visible
purely from column-name pattern-matching, with zero DAX execution and zero
knowledge of what the relationship was supposed to accomplish** — which is
exactly the class of review a `.tmdl` diff makes possible and a `.pbix`
binary diff makes structurally impossible, since there is no way to review
"what changed" in a file git can only report as `Binary files a/model.pbix
and b/model.pbix differ`.
