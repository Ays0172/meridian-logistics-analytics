# Day 29 — solutions

---

## Spaced recall answers

1. **Four guarantees:** history is immutable (append-only writes, never opens
   an existing file); days are reproducible (each date's rows come from
   `child_rng("live:<table>:<date>")`, seeded from the date, plus a reserved
   50,000-key block per date); gaps self-heal (the work list is a set
   difference against recorded run dates, not a range from a pointer); every
   append is verified before the watermark moves. **Gaps self-heal** is
   specifically what licenses unattended scheduling — a delayed, skipped, or
   doubled-up run always converges to the correct state on its own, with no
   human needed to reconcile it.
2. A running counter would make a day's keys depend on how many rows preceded
   it — regenerating one day after a `--redo` would then produce the same
   business rows under different keys, breaking reproducibility. A reserved
   block per date makes each day's key range independent of run history.
3. It taught that `TREATAS` in the wrong direction does not error — it runs
   and returns a plausible-looking wrong number, because whichever argument
   ends up as the filtered column silently succeeds at filtering *something*,
   just not the thing you intended. That is the dangerous failure mode:
   silent and confident-looking, not loud.
4. A periodic snapshot records a balance repeated at intervals
   (`FactInventorySnapshot` — weekly, then daily); an accumulating snapshot has
   one row per entity updated in place as it progresses
   (`FactShipmentMilestone`).
5. Fiscal year starts **1 October**, and is named for the year it ends in
   (Oct 2025–Sep 2026 = FY26). In DAX: `DATESYTD(DimDate[Date], "09-30")`.

---

## Exercise 29.1 — read the incident history

| Commit | Layer | What broke | What the fix changed |
|---|---|---|---|
| `0cd5b65` | Manifest script (`build_manifest.py`) | `manifest.json` carried a `generated_at` timestamp, so it differed on every run even with zero new data — the workflow's no-op-day guard (`git diff --cached --quiet`) never fired, and every scheduled run produced a commit whether or not anything had actually changed. | Dropped the `generated_at` field entirely. Nothing in the manifest now varies unless the underlying file list does. |
| `baede5f` | Workflow YAML + upstream zip | `unzip` failed on the release zip because its internal paths used Windows-style backslash separators (the zip was built on Windows); the runner is Linux, so `unzip` either mis-extracted or exited non-zero, and an earlier patch had papered over this with `\|\| true`, which silenced *real* extraction failures too. | Fixed the zip itself to use forward-slash paths at the point it was built, removed the `\|\| true` mask, and bumped the cache key (`history-v1` → `history-v2`) so a runner that had already cached the broken extraction wasn't stuck serving it forever. |
| `f1690e3` | Workflow YAML | The frozen-history cache and the git-tracked `02_data/raw` directory were the same path. A `git checkout` (fresh files) and a restored cache (stale files) could both land in that one directory in an order that left it in a mixed, inconsistent state between runs. | Moved the cache target to its own directory (`02_data/_frozen_cache`), isolated from anything git touches, and merged it into `02_data/raw` with an explicit `cp -rn` step afterward — checkout and cache restore can no longer race in the same directory. |

All three bugs lived one layer away from where the symptom appeared:
`0cd5b65`'s symptom (commits on no-op days) looked like a workflow-logic bug
but was actually a manifest-content bug; `baede5f`'s symptom (extraction
failures) looked like a workflow bug but originated in how the zip was built;
`f1690e3` was the one genuinely in the workflow's own directory layout. The
lesson: when a scheduled pipeline misbehaves, check what it's *reading* before
assuming the bug is in the step that's failing.

---

## Exercise 29.2 — trace a no-op day

With the watermark already at today's date, `live_feed.py` finds an empty work
list (`dates in [history_end+1 … today] MINUS dates already on record` = ∅)
and writes nothing new. `build_manifest.py` re-scans `02_data/raw` and writes
the exact same `manifest.json` it wrote yesterday — byte-identical, now that
the volatile timestamp is gone. `git add` stages nothing new (or stages files
whose content is unchanged, which `git diff --cached` correctly reports as no
diff). `git diff --cached --quiet` therefore exits `0` (true), the `||` branch
never runs, and the job ends cleanly with **no commit, no push**.

The bug from `0cd5b65` is exactly the one that would have broken this: with
`generated_at` still present, `manifest.json` would differ from yesterday's
version on content grounds alone, `git diff --cached --quiet` would find a
real diff every time, and this "no-op day" would produce a commit anyway —
a `git log` full of daily commits with an empty diff on everything except one
timestamp field, which is exactly the kind of noise that makes a real change
three weeks later hard to spot in the history.

---

## Exercise 29.3 — extend the pattern to `FactShipment`

```
FactShipmentFrozen
  = Parquet.Document folder-combine over 02_data/raw/FactShipment/**/part-000.parquet

FactShipment_Live =
    let
        Manifest = Json.Document(Web.Contents(
            "https://raw.githubusercontent.com/Ays0172/meridian-logistics-analytics/main/02_data/_state/manifest.json"
        )),
        Urls    = Manifest[tables][FactShipment],
        Tables  = List.Transform(Urls, each Parquet.Document(Web.Contents(_))),
        Combined = Table.Combine(Tables)
    in
        Combined

FactShipment = Table.Combine({FactShipmentFrozen, FactShipment_Live})
```

**Estimate before refreshing:** `manifest.json`'s `FactShipment` array holds
**7** URLs (one live day per entry, `20260821`–`20260827` at time of writing).
`watermark.json`'s `daily_rows.FactShipment` records an average of **269.11**
rows/day. Estimated extra rows: `7 × 269.11 ≈ 1,884`.

**After refresh:** the live query returns the live rows appended so far — the
exact count moves every time the Action fires again, which is the entire
point; a report built on this query gets one row-count larger every night
without anyone touching Power BI.

---

## Exercise 29.4 — what happens if the schedule slips

A six-day gap does not change the final state at all. The next successful run
computes `dates in [last_appended+1 … today] MINUS dates already on record`,
which is now a six-day range instead of a one-day range, and appends all six
— each one generated from its own `child_rng("live:<table>:<date>")` stream,
so each day is identical to what it would have been had the workflow fired on
time every day. `FactWarehouseTask` (or `FactShipment`) ends up with exactly
the same rows either way; only the number of `part-YYYYMMDD-NN.parquet` files
per run differs (one run writing six days' worth, versus six runs writing one
day each).

**Guarantee:** "days are reproducible" (per-date seeding, not run-order
seeding) is what makes each of the six days correct regardless of when it was
generated. **Mechanism:** `watermark.json`'s `last_appended_date` (and its
per-table `next_keys`) is what makes the set-difference computation possible
at all — it is the one piece of state the workflow must commit back to the
repo every run, alongside the parquet and the manifest, or the next run would
have no record of what it already covered.

---

## What to watch for in your own extension

The two failure modes seen in the real history are worth re-checking on
anything you wire up yourself: (1) never let a generated file you diff
byte-for-byte carry a field that changes on its own — a timestamp, a random
UUID, a row-order that isn't stably sorted; (2) never let a cache directory
and a git-tracked directory be the same path — restore order between the two
is not something you control.
