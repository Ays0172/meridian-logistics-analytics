# The live feed

`01_generator/live_feed.py` appends new data day by day without ever touching
what is already there. This document is the operator's manual and the design
rationale.

## The two layers

| | Frozen history | Live feed |
|---|---|---|
| Dates | 2021-08-21 → 2026-08-20 (5 years) | 2026-08-21 onwards |
| Built by | `build_facts.py` | `live_feed.py` |
| Write mode | `overwrite` — wipes the table first | `append` — never opens an existing file |
| Filenames | `part-000.parquet` | `part-YYYYMMDD-NN.parquet` |
| Rows | 7,481,188 | ~1,900–5,400 per day |
| Changes when re-run? | Yes, entirely rebuilt | No. Days already on record are skipped |

The split is the point. History is a fixed asset you build once and can always
reproduce byte-for-byte from the seed. The live feed is an append-only log on top
of it. Nothing in the live feed's code path can modify a history file.

## Everyday use

```bash
python live_feed.py              # catch up from the watermark to today
python live_feed.py --status     # what has been appended, and when
python live_feed.py --until 2026-12-31   # fast-forward (generates every day in between)
python live_feed.py --redo 2026-08-25    # undo exactly one day
python live_feed.py --reset      # remove all appended days; history untouched
```

Running it twice in one day is a no-op the second time. Running it after a
week's gap appends the whole week, one day at a time, each day correct.

## The four guarantees, and why each is designed rather than hoped for

**1. Yesterday cannot change.** Every write passes `mode="append"` to
`write_fact`, which allocates a new file and never opens an existing one. There
is no code path from the live feed to a history file. Verified: the SHA-256 of
all 690 `part-000.parquet` files is identical before and after appending six
days, redoing a middle day, and backfilling a gap.

**2. Tomorrow starts where today stopped.** `_state/watermark.json` records every
day ever appended. The work list for a run is

```
dates in [history_end + 1 … today]   MINUS   dates already on record
```

a set difference, not a range from a pointer. That is what makes it correct under
gaps, redos and out-of-order backfills. If you have days 1–10 and day 7 goes
missing, the next run appends only day 7 — it does not re-append 8, 9 and 10.

**3. A given calendar day always produces the same rows.** Each day's data comes
from `child_rng("live:<table>:<date>")`, seeded from the *date* rather than from
run order or run count. Two consequences: a day regenerated after a `--redo` is
byte-identical to the original, and a day missed for a fortnight can be
backfilled later and is still the day it should have been.

Surrogate keys are part of this. They are allocated in a **reserved block per
date** — `history_max + (day_index − 1) × 50,000` — not from a running counter.
A counter would have made a day's keys depend on how many rows preceded it, so
regenerating one day after a redo produced the same business rows with different
keys. Surrogate keys have no requirement to be contiguous, so the gaps between
blocks cost nothing and buy full reproducibility.

**4. Every day is individually reversible.** Append filenames carry their
business date, so one day's files are identifiable from their names alone.
`--redo` deletes exactly those and forgets the run. This was originally
sequential numbering (`part-000`, `part-001`, …) and that was quietly
destructive: delete `part-002` and the next append computes index 3 and
overwrites `part-003`, replacing a different day's data. The bug was found by the
project's own test, which is why the filenames changed.

**Post-append verification.** After each day, the feed re-reads the affected
tables and asserts no duplicate primary keys and that
`FactShipmentMilestone` is still 1:1 with `FactShipment`. If either fails the run
aborts and prints the `--redo` command to undo it. A silent duplicate is far
cheaper to find on the run that created it than in a dashboard three weeks later.

## Scheduling it

### Windows Task Scheduler (simplest, free)

Create `run_feed.bat` in `01_generator`:

```bat
@echo off
cd /d "%USERPROFILE%\Data\Meridian-Logistics-Analytics\01_generator"
python live_feed.py >> ..\02_data\_state\feed.log 2>&1
```

Then: Task Scheduler → Create Basic Task → Daily → Start a program →
point at `run_feed.bat`. Tick "Run whether user is logged on or not" if you want
it to fire on a locked machine.

Because the work list is a set difference, it does not matter if the machine was
asleep. The next run catches up.

### GitHub Actions (free, and gives you an HTTP endpoint)

This is the path chosen for Week 5. A public repository gets unlimited Actions
minutes and a 5-minute minimum cron interval. The workflow runs `live_feed.py`,
commits the new Parquet files, and Power BI reads them over HTTPS from
`raw.githubusercontent.com` — a real API endpoint, no hosting bill.

Two things to know before relying on it:

- Scheduled workflows on the free tier are **best-effort**. Cron can be delayed
  during peak load, and schedules are disabled automatically after 60 days of
  repository inactivity. The set-difference work list means a delayed or skipped
  run self-heals on the next one.
- Do not have the workflow force-push or rebuild history. It should only ever run
  `live_feed.py`, which is append-only by construction.

### What not to build on

Power BI's push and streaming datasets are on a deprecation clock — creation of
new ones stops after 31 October 2027, with Fabric Real-Time Intelligence named as
the successor. A streaming dataset also holds only about an hour of data in a
temporary cache and caps at 15 KB per request, so it can feed tiles but not a
report. Worth one day as a learning exercise in Week 5; not worth being the
foundation.

Power Automate is a fine trigger but a poor engine here: the free and
Microsoft 365 plans give scheduled cloud flows and 6,000 actions a day, but no
custom connectors and no gateway, and the HTTP action's premium status is
inconsistently enforced between tenants.

Cloud scheduled refresh is the part that genuinely costs money — Microsoft
documents 8 refreshes a day on Pro and 48 on PPU or Fabric capacity, with no Free
tier listed. Keeping the automation outside Power BI is what keeps this free.

## Simulation speed

Two independent clocks, and conflating them is the usual confusion:

- **How often the job wakes up** — the cron interval.
- **How much simulated time passes per wake** — one calendar day per invocation
  here, since `live_feed.py` generates whole business days.

To build up a lot of history quickly, drive the second clock directly rather than
waiting for the first:

```bash
python live_feed.py --until 2026-12-31     # ~4 months in about 4 minutes
```

Each day is still generated and verified individually, so fast-forwarding gives
exactly the same result as having waited four months.

## What the feed does not generate

`FactTarget` and `DimCustomer` are deliberately excluded. Targets are set by
planners once a year, not produced by daily operations, and customer master data
changes through a governed process rather than a nightly job. Adding them to the
feed would be modelling the wrong thing. `FactExchangeRate` is read by the feed
but extended only when history is rebuilt.

## Limitations worth knowing

- Live shipments are created and depart on the same day. The frozen history
  models the full booking-to-departure lead time; the feed compresses it, because
  a shipment departing today from a booking placed six weeks ago would require
  carrying forward six weeks of open bookings. Carrying that state is a
  worthwhile extension, and it is Week 5 material.
- Because of the above, live milestone rows show fewer completed milestones than
  history rows for shipments of the same age. That is realistic for in-flight
  cargo but is not the same as history's distribution.
- The congestion event of §3.3 is historical only. The feed does not inject new
  disruptions. Adding a scenario switch is a natural extension.
