# Day 30 — Scheduled refresh in the Service, and an incremental refresh policy over `02_data/raw`

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 75 min · Ship 30 min · Log 15 min

Yesterday's Action keeps the data moving without you. Today's job is the other
half: keeping the *model* moving without you, and doing it without re-reading
five years of frozen history every single time a new day lands.

---

## Spaced recall (10 min, closed book)

1. What three directories does `live-feed.yml` commit, and why would omitting
   `_state` from that list break the next scheduled run even though the
   parquet itself would still be correct?
2. Why does `manifest.json` need to be free of any field that changes on its
   own between otherwise-identical runs?
3. What is Meridian's fiscal year convention, and how is it written in DAX?
4. Why can't `FactTarget` have a physical relationship to `DimLocation`, and
   which column actually bridges the two?
5. State the semi-additive trap in one sentence, and name the fact table it
   applies to.

---

## Concept

### Refresh limits, and why they make incremental refresh non-optional here

Power BI Service refresh is rate-limited, not unlimited (`README` §4,
`LIVE_FEED.md`): **8 refreshes/day on Pro, 48/day on PPU or Fabric capacity**,
with no Free tier listed at all. A full refresh of this model means re-reading
every partition of every table in `02_data/raw` — 7.5M+ fact rows, growing by
roughly 2,000–5,400 rows a day per the live feed — from source, every time.
At even a modest per-refresh cost, doing that 8 times a day burns your entire
daily budget on work that is 99.9% redundant: yesterday's five years of
history did not change, only today's new rows did.

**Incremental refresh** is the fix: split each table into date-range
partitions, refresh only the partitions that can plausibly contain new or
changed rows, and leave the rest untouched. This is also the one lever that
actually matters here — this schema has no dedicated "last modified"
timestamp column on any fact table, so the optional "detect data changes"
accelerator (which needs exactly such a column to skip *unchanged* rows
*within* a still-refreshing partition) is not available to you. That is fine:
the big win is skipping entire historical partitions outright, and that only
needs the range columns you already have.

### The partition scheme already on disk

`02_data/raw/<Table>/year=YYYY/month=MM/part-*.parquet` — Hive-partitioned by
year and month, and it is not a report-layer decision, it is baked into how
`factio.py` writes every fact table:

```python
years  = np.where(known, keys // 10000, 1900).astype(int)
months = np.where(known, (keys // 100) % 100, 1).astype(int)
rel = f"year={yr:04d}/month={mo:02d}"
```

An incremental refresh policy's `RangeStart`/`RangeEnd` partitioning should
mirror this, at monthly granularity, on each table's **primary date key** —
the exact column each table is already physically partitioned by on disk:

| Table | Primary date key (= partition column) |
|---|---|
| `FactBooking` | `BookingDateKey` |
| `FactShipment` | `ShipmentDateKey` |
| `FactShipmentMilestone` | `BookingConfirmedDateKey` |
| `FactContainerMove` | `EventDateKey` |
| `FactPortCall` | `AtaDateKey` |
| `FactFreightCharge` | `ChargeDateKey` |
| `FactTransportLeg` | `ActualPickupDateKey` |
| `FactWarehouseTask` | `TaskDateKey` |
| `FactInventorySnapshot` | `SnapshotDateKey` |

Matching Power BI's partition boundary to the file system's own partition
boundary is not a coincidence to aim for — it means a monthly incremental
refresh window reads whole Parquet partitions cleanly, instead of scanning a
partition and throwing half of it away.

### The sentinel gotcha: `-1` dates and the `year=1900` bucket

Read `factio.py`'s partitioning logic closely — a fact row whose primary date
key is the `-1` sentinel (not yet happened) is **not dropped and not
misfiled**. It is routed to an explicit `year=1900/month=01` partition:

```python
known = keys > 0
years  = np.where(known, keys // 10000, 1900).astype(int)
```

This is deliberate, documented behaviour, not a bug — but it is a real trap
for an incremental refresh policy that isn't built with it in mind. Consider
`FactPortCall`, partitioned by `AtaDateKey` (actual time of arrival). A port
call that hasn't arrived yet has `AtaDateKey = -1` and lives in the
`year=1900` bucket. A "refresh the last 3 months" policy will **never touch
that partition again** — it sits permanently outside the incremental window.
That is almost always fine (an arrival that hasn't happened has nothing to
refresh), but it means: **never assume "oldest partition" is safe to archive
without checking whether it's actually the sentinel bucket** — `year=1900`
will sort first in any naive "oldest first" archival script, and it is not
history, it is "not yet known."

### Designing the policy: archive vs incremental window

The standard Power BI incremental refresh shape, applied to this dataset:

```
Archive:      everything older than N years   → refreshed once, never again
Incremental:  the trailing M months            → refreshed every scheduled run
```

Given the history spans exactly 5 years (`2021-08-21 → 2026-08-20`) and the
live feed adds roughly one day at a time going forward, and given that Power
BI's "archive" setting (**"Store rows in the last..."**) is the *total*
retention window, not an additional period stacked in front of the
incremental one — the incremental window is a trailing subset **inside** the
archive window, refreshed every run, while the rest of the archive window is
loaded once and then left alone:

- **Archive period: 5 years.** Set to cover the entire frozen history, so
  nothing ages out of the model — `LIVE_FEED.md` is explicit that nothing in
  the live feed's code path can touch a history file, so there is zero reason
  to ever re-read the older rows inside this window after their first load,
  but there is also no reason to drop them: a 4-year archive would silently
  exclude the oldest ~12 months of history from the model entirely, which is
  data loss dressed up as a refresh policy.
- **Incremental period: 13 months.** The most recent full year plus the
  current month, refreshed every scheduled run — a trailing subset of the
  5-year archive window above, not an additional period beyond it. Wider than
  "just this month" on purpose: it absorbs a `--redo` of a day inside the last
  few weeks (Day 29's Exercise 29.1 pattern) without needing a manual
  partition-boundary adjustment, and it comfortably covers
  `FactInventorySnapshot`'s slower cadence — its snapshots run weekly for
  anything older than the most recent 12 months and daily only inside that
  window (Day 12), so a 13-month incremental range is what actually
  guarantees every daily-cadence snapshot currently in play gets refreshed.

This means the partition boundary in Power BI's incremental refresh dialog is
`RangeStart = <today> minus 5 years, floored to the 1st of the month` and
`RangeEnd = today`, applied against the table's primary date key from the
list above — wrapped as `DimDate`-equivalent `Date` values in Power Query
(`Date.From`), which is the format Power BI's `RangeStart`/`RangeEnd`
parameters expect. The 13-month incremental setting is a *separate* dialog
value inside that same window, not a second `RangeStart`.

### Full refresh vs incremental refresh, and where each still runs

Incremental refresh only applies to the **Service**, and it needs Power BI
Desktop configured with an `Incremental Refresh` policy per table (right-click
the table → *Incremental refresh*, set `RangeStart`/`RangeEnd`, archive and
incremental windows, and optionally the detect-data-changes column — skipped
here for the reason above). A full refresh in **Desktop** during development
always re-reads everything; that is correct and expected while you're still
building — you only pay the incremental-refresh cost benefit once the model
is published and refreshing on a schedule in the Service.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 30.1 — build the policy for `FactWarehouseTask` (25 min)
Configure incremental refresh on `FactWarehouseTask` in Desktop:
`RangeStart`/`RangeEnd` filter on `TaskDateKey` (converted to a `Date`),
archive period 5 years (the whole history — see why a shorter archive window
silently drops data, above), incremental period 13 months. Predict, before you
apply it, how many monthly partitions this produces given the table's history
span — then check the partition count Power BI reports after the first
refresh.

### Exercise 30.2 — the `year=1900` trap, reasoned through (20 min)
Without building anything, answer in writing: if you applied the exact same
policy (archive 5 years / incremental 13 months) to `FactPortCall` on
`AtaDateKey`, would a port call that departs today but has not yet arrived
ever get refreshed once it eventually does arrive? Trace through what
partition it lives in *before* arrival, and what has to happen for it to move
into a partition your incremental window actually reaches. Is this a bug in
the policy, or a property of the column you chose?

### Exercise 30.3 — pick the wrong column, on purpose (20 min)
Redesign the `FactShipmentMilestone` policy using `GateOutDestinationDateKey`
(a *milestone* column, not the table's actual primary date key,
`BookingConfirmedDateKey`) as the `RangeStart`/`RangeEnd` basis instead.
Recall from Day 12: **9,945 rows** currently carry `GateOutDestinationDateKey
= -1` for shipments still in flight. Predict what fraction of the table would
land in the sentinel bucket under this wrong choice, and explain in 2–3
sentences why the table's *primary* date key almost always beats a
*milestone* date key as a partition basis for a table like this.

### Exercise 30.4 — refresh budget arithmetic (10 min)
Pro tier gives 8 scheduled refreshes/day. If a single incremental refresh of
the 13-month window across all 9 live-fed fact tables takes on average 4
minutes, and you also want to trigger a refresh once right after the nightly
GitHub Action lands (roughly 01:15 UTC, 15 minutes after the `0 1 * * *`
cron), design a refresh schedule that stays inside the 8/day limit while
still getting fresh data to readers at the start of both a US and an EU
business day. Write the actual clock times (UTC) you'd configure.

---

## Ship

Apply incremental refresh policies (archive 5 years / incremental 13 months,
primary-date-key partitioned per the table above) to all nine live-fed fact
tables. Document the choice of partition column per table — including the
`FactPortCall`/`AtaDateKey` sentinel caveat from Exercise 30.2 — in a new
`03_powerbi/incremental_refresh_policy.md`, in the same worked-example style
as `data_quality_findings.md`, so the next person to touch this model doesn't
have to re-derive which column each table uses.

```
git add .
git commit -m "Day 30: incremental refresh policies applied to 9 live-fed fact tables, documented"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can state, from memory, the Pro/PPU refresh limits and explain why
      they make incremental refresh necessary rather than optional at this
      data volume.
- [ ] `incremental_refresh_policy.md` exists, names every table's partition
      column, and explains the `year=1900` sentinel-partition caveat in your
      own words.
- [ ] Incremental refresh is configured on at least `FactWarehouseTask`,
      verified against a real partition count from Desktop.
- [ ] You can explain why this schema's incremental refresh design relies on
      range partitioning alone, with no "detect data changes" column, and why
      that is still the majority of the win.
- [ ] Predictions recorded, misses annotated.
