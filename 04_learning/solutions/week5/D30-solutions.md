# Day 30 — solutions

---

## Spaced recall answers

1. `02_data/raw/`, `02_data/_state/`, `02_data/_validation/`. Omitting
   `_state` would leave `watermark.json` (and `manifest.json`) stuck at
   whatever the last-committed version was — the next run's own local copy
   would advance correctly during the run, but never get pushed, so the next
   *checkout* starts from the stale watermark again. Depending on how the
   generator verifies against on-disk parquet versus the watermark file, this
   risks either silently re-deriving the same "missing" days repeatedly or
   tripping the duplicate-key verification and aborting — either way, a
   working parquet layer with a broken state file behind it.
2. Because a downstream check (`git diff --cached --quiet`) compares it
   byte-for-byte across runs to decide whether anything real changed. A field
   that changes on its own (a timestamp, in the real bug) makes every run look
   different even when nothing meaningful did, defeating the comparison.
3. Fiscal year starts **1 October**, named for the year it ends in.
   `DATESYTD(DimDate[Date], "09-30")`.
4. `FactTarget` is set at monthly, region-level grain; `DimLocation` and the
   transactional facts run at daily, per-location grain — no shared column at
   a shared grain exists for a physical relationship. `DimLocation[TradeRegion]`
   bridges them (matches `FactTarget[Region]`'s five values exactly;
   `DimLocation[Region]`, a finer grain, does not).
5. A snapshot row is a balance sampled repeatedly, not an independent event —
   summing it across dates adds the same stock to itself once per sample date.
   Applies to `FactInventorySnapshot`.

---

## Exercise 30.1 — build the policy for `FactWarehouseTask`

**Prediction basis:** history runs 2021-08-21 → 2026-08-20, which spans
**61 calendar months** (Aug 2021 through Aug 2026 inclusive) — this is not a
guess, it is the exact number `factio.py`'s own history fingerprint records
for every table (`"files": 61` in `watermark.json`'s `history_fingerprint`
block, one `part-000.parquet` per monthly partition).

An archive-4-years + incremental-13-months policy covers `4×12 + 13 = 61`
months — the same number, because the policy is deliberately sized to span the
whole history exactly once on first load. **Predicted partition count: 61**
(plus one more for each additional month the live feed has advanced past
2026-08-20 by the time you build this). Power BI's reported partition count
after the first refresh should land at 61 or 62, confirming the archive and
incremental windows together reconstruct exactly the physical partition
layout already on disk — the alignment is the point, not a coincidence.

---

## Exercise 30.2 — the `year=1900` trap, reasoned through

**The honest answer requires tracing the architecture, not just the column.**
This dataset is append-only end to end — `LIVE_FEED.md`'s first guarantee is
that nothing in the live feed's code path can open and rewrite an existing
row. If `FactPortCall` ever wrote a row with `AtaDateKey = -1` (arrival not
yet known) and then later needed that same row to carry a real arrival date,
there is **no mechanism in this architecture to do that** — the row would
either stay `-1` forever, or a *second* row would need to be appended once
arrival happens, which would break the one-row-per-port-call grain.

The more consistent reading, matching the documented simplification elsewhere
in this project (live shipments are "created and depart on the same day"
rather than modelling weeks of lead time — `LIVE_FEED.md`, *Limitations*), is
that `FactPortCall` rows are only generated once the call has actually
happened, meaning `AtaDateKey` is real at creation time for essentially every
row, and the `year=1900` bucket for this specific table is empty or
near-empty in practice. **Verify this rather than assume it** — a quick
`DISTINCT(FactPortCall[AtaDateKey])` filtered to `-1`, or checking whether
`02_data/raw/FactPortCall/year=1900` exists on disk at all, settles it in
under a minute.

**Is this a bug in the policy, or a property of the column?** A property of
the column, combined with the append-only architecture — and specifically a
reason to check, table by table, whether a candidate partition column can
ever legitimately hold `-1` for rows that exist at refresh time, rather than
assuming every table's sentinel bucket behaves the same way `FactWarehouseTask`'s
does (`TaskDateKey`, which is populated at creation for every real task).

---

## Exercise 30.3 — pick the wrong column, on purpose

Using `GateOutDestinationDateKey` instead of the table's real primary date
key (`BookingConfirmedDateKey`):

**Predicted sentinel fraction:** Day 12 measured **9,945 of ~493,608** rows
(`≈2.0%`) carrying `GateOutDestinationDateKey = -1` — shipments genuinely
still in flight. Under this wrong policy, roughly 2% of the table lands
permanently in `year=1900`, never refreshed once those shipments do
eventually clear that milestone (same append-only argument as 30.2).

**Why the primary date key beats a milestone date key, beyond the sentinel
issue:** the deeper problem is that Power BI's `RangeStart`/`RangeEnd`
partition boundary stops matching the **physical Parquet partition
boundary on disk**, which is fixed by `factio.py` to the table's
`PRIMARY_DATE_KEY` (`BookingConfirmedDateKey` for this table) and nothing
else. A row's `GateOutDestinationDateKey` can fall in a completely different
calendar month than the physical file it lives in. Power BI's incremental
refresh for a given month-window would then have to open Parquet partition
files scattered across many *different* on-disk months to find the rows that
happen to match that window on the wrong column — reading the same physical
partitions repeatedly across multiple "incremental" windows, which is close
to defeating the entire benefit of incremental refresh in the first place.

---

## Exercise 30.4 — refresh budget arithmetic

Data lands from the GitHub Action at roughly 01:00–01:10 UTC (`0 1 * * *`
cron plus install/run time). A workable schedule, well inside Pro's 8/day
cap:

| UTC time | Purpose |
|---|---|
| **02:00** | Safety-buffered first refresh of the day — an hour of headroom past the Action's typical finish time, so a slow Action run doesn't race a refresh that reads half-written state. |
| **07:00** | EU/UK business-day start (≈08:00–09:00 CET/BST). |
| **12:00** | US East business-day start (≈08:00 ET). |
| **17:00** | US West business-day start (≈09:00–10:00 PT). |

Four scheduled slots out of eight, leaving four in reserve for manual
on-demand refreshes during active development or testing — exactly the
headroom you want before committing to a schedule you can't easily change
without burning your own refresh budget to test the change.
