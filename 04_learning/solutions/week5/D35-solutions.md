# Day 35 — solutions

---

## Spaced recall answers

1. History is immutable; days are reproducible (seeded per date + reserved key
   blocks); gaps self-heal (set-difference work list); every append is
   verified before the watermark moves. **Gaps self-heal** is the one that
   specifically makes an unattended run safe after a missed day — a runner
   outage or a paused schedule doesn't corrupt anything or require a manual
   catch-up; the next successful run computes the missing dates as a set
   difference and appends exactly those, no more, no less.
2. `DimLocation[TradeRegion]`. Filtering `DimLocation[Region]` instead does not
   error — it applies a real, valid filter to a real column that simply
   doesn't correspond to `FactTarget[Region]`'s five macro-region values, so
   the RLS role silently shows either everything or nothing depending on
   whether any `Region` value happens to text-match a `FactTarget[Region]`
   value by coincidence. Same failure shape as Day 13's `TREATAS` direction
   mistake: no error, a plausible-looking wrong result.
3. A bidirectional relationship on `DimWarehouse`–`DimLocation` (or the
   equivalent flagged in your own build) was corrected to single-direction,
   because a second ambiguous filter path compounds the same
   `ALL`/`ALLSELECTED` context-scoping risk from Day 9 one hop further from
   the visual, invisibly.
4. It lets a reviewer read a text diff of exactly what changed (which
   measure's DAX, which relationship's cardinality, which RLS role's filter
   expression), the way a normal code review works — a `.pbix` diff only ever
   reports "binary files differ," with no way to review the actual change.
5. This number is genuinely yours to report, not to copy from a key — it
   should match whatever your own Day 34 Exercise 34.1–34.3 work found. If you
   didn't confirm all 10, name the number and say which ones are still open;
   an honest "7 of 10, three still unverified" is a better checkpoint answer
   than a number you didn't actually check.

---

## Part A — reference points to check yourself against

- `live-feed.yml`'s schedule and the three committed directories are whatever
  your own Day 29 Ship step recorded — check your file, not this key.
- The RLS filter expressions are your own Day 31 Ship deliverables; the
  specific mechanism to have present is `USERELATIONSHIP` (or the dedicated
  `FactTarget`-side rule) wherever a role needs to reach through the inactive
  `FactInventorySnapshot`→`DimSku` relationship or an equivalent path in your
  build.
- The incremental refresh RangeStart/RangeEnd should bind to the same
  transaction-date column each fact table's relationship to `DimDate` already
  uses (`ShipmentDateKey`, `TaskDateKey`, etc.) — not a different date column
  that happens to also exist on the table.
- Any one of Day 32's confirmed anti-pattern fixes counts; the point of this
  recall is proving you can name a specific one from your own build, not
  reciting a generic list.

---

## Part C — what "pass" looks like

A genuinely complete dry run leaves you with **zero unchecked boxes with no
note** — not zero unchecked boxes. An honest "RLS re-test: fails after
incremental refresh, root cause not yet found, revisiting Day 36" is a correct
checkpoint outcome; a silently skipped box is not. The single most common real
failure this checklist is designed to catch: an RLS role written and tested on
Day 31, before the incremental refresh policy existed, that never gets
re-verified against a table that now refreshes in partitions instead of all at
once — the role can pass its original View As test and still fail to cover a
newly-added partition, because the two pieces of work were built and tested
five days apart and never checked together until today.
