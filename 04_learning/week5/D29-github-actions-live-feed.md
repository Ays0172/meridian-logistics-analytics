# Day 29 — GitHub Actions: turning `live_feed.py` into a scheduled service

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 80 min · Ship 30 min · Log 15 min

Everything until now has been "run this yourself." Today the project gets a
pulse that keeps beating without you. This is also the one Week 5 day where you
are not designing something from a blank page — a working version of this
already runs in the real repo, on a schedule, and has a real incident history in
its git log. Today's job is to understand it precisely enough to extend it, not
to invent it.

---

## Spaced recall (10 min, closed book)

1. Name the four live-feed guarantees from `LIVE_FEED.md` and say which one
   specifically is what makes it safe to fire a scheduled job unattended, even
   if a run gets delayed or skipped.
2. Why does `live_feed.py` allocate surrogate keys from a reserved block per
   date instead of a running counter?
3. What did Exercise 13.4 (`TREATAS` with its arguments swapped) teach you about
   "plausible-looking wrong numbers," and why is that the dangerous failure mode
   rather than an error?
4. State the difference between a periodic snapshot and an accumulating
   snapshot, and name one Meridian fact table of each.
5. Per this project's conventions, what does the fiscal year start on, and how
   is that expressed as the third argument to a `DATESYTD`-family function?

---

## Concept

### Why GitHub Actions, and not Task Scheduler forever

Windows Task Scheduler (from `LIVE_FEED.md`) works, but it only runs while your
machine is on and only helps you — nobody else, and no cloud service, can see
the result. GitHub Actions on a public repo gives three things Task Scheduler
cannot: unlimited free minutes, a cron trigger that fires whether your laptop
is open or not, and — the part that actually matters for Power BI — every file
it writes becomes reachable over plain HTTPS at
`raw.githubusercontent.com/<repo>/<branch>/<path>`, with no server to run and
no hosting bill. That URL is a real API endpoint built entirely out of "this
file exists in this git repo."

Two constraints worth knowing before you rely on it, both from `LIVE_FEED.md`:
scheduled workflows on the free tier are **best-effort** (cron can be delayed
under GitHub's load), and a schedule is **disabled automatically after 60 days
of repository inactivity**. Neither is fatal here, because of the guarantee you
just recalled in Q1 — a delayed or skipped run just means tomorrow's run
appends more than one day, and the set-difference work list handles that
correctly by construction.

### The workflow that is actually running

This is the current, deployed `.github/workflows/live-feed.yml` in the real
repo — not a draft, a working pipeline with several real commits behind it:

```yaml
name: Live Feed

on:
  schedule:
    - cron: '0 1 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Dependencies
        run: pip install -r 01_generator/requirements.txt

      - name: Cache frozen history
        id: history-cache
        uses: actions/cache@v4
        with:
          path: 02_data/_frozen_cache
          key: frozen-history-v1

      - name: Download frozen history (cache miss only)
        if: steps.history-cache.outputs.cache-hit != 'true'
        run: |
          mkdir -p 02_data/_frozen_cache
          gh release download history-v1 --pattern "meridian-history.zip" --dir .
          unzip -q meridian-history.zip -d 02_data/_frozen_cache
          rm meridian-history.zip
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Merge frozen history into raw (never touches live files)
        run: |
          mkdir -p 02_data/raw
          cp -rn 02_data/_frozen_cache/. 02_data/raw/

      - name: Run Live Feed
        run: |
          cd 01_generator
          python live_feed.py
          python build_manifest.py

      - name: Commit New Data
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add 02_data/raw/ 02_data/_state/ 02_data/_validation/
          git diff --cached --quiet || (
            git commit -m "Daily live feed update"
            git push
          )
```

Read every step against what you already know:

**`cron: '0 1 * * *'`** fires once a day at 01:00 UTC. Cron is always UTC on
GitHub-hosted runners — convert your local time before you pick a number.
`workflow_dispatch:` with nothing under it adds a manual "Run workflow" button
in the Actions tab, useful for catching up by hand without waiting for the
clock.

**`permissions: contents: write`** is not optional. The default
`GITHUB_TOKEN` a workflow gets is read-only unless you say otherwise, and
the final step needs to `git push` — omit this and the commit step fails with
a permission error that has nothing to do with your Python code.

**Why frozen history is a GitHub Release, not a git-tracked file.** The 515 MB
of frozen Parquet (`part-000.parquet` under every table) is excluded from git
entirely — check `.gitignore`:

```
02_data/raw/**/part-000.parquet
```

Committing it would make every checkout, and every Actions run, pull 515 MB it
never changes. Instead it ships once as a **GitHub Release asset**
(`history-v1`, a zip), and the workflow downloads it only on a cache miss —
`actions/cache@v4` keyed `frozen-history-v1` means every run after the first
one skips the download entirely and restores the cache instead. The download
step then unzips into `02_data/_frozen_cache`, and a separate step
`cp -rn`s it into `02_data/raw` — deliberately a **different** directory from
the one git tracks, merged in afterward. Cache and git-tracked state used to
share a directory in an earlier version of this workflow, and a stale cache
collided with what `git checkout` had just restored — that is why the two are
kept apart now (see Exercise 29.1).

**Why `git add` names three specific directories, not `.`.** `02_data/raw/`,
`02_data/_state/`, `02_data/_validation/` — and nothing else. An earlier
version of this workflow was less careful, and it is exactly the kind of bug
that looks fine for weeks and then commits something nobody wanted the day
someone adds a stray file to the cache directory.

**Why `git diff --cached --quiet || (...)` and not just `git commit`.** On a
day the watermark is already caught up — you ran the workflow twice, or a
manual `workflow_dispatch` fired right after the scheduled run — `live_feed.py`
does nothing, `build_manifest.py` regenerates the same file, and there is
nothing to commit. `git commit` with nothing staged would fail the whole job.
`git diff --cached --quiet` exits non-zero only when there is a real diff, so
the commit+push only happens when there is something to push.

### `build_manifest.py`, and the bug that taught the "no volatile fields" rule

`01_generator/build_manifest.py` walks every table under `02_data/raw`, keeps
only files matching `part-\d{8}-\d{2}\.parquet` (the live, date-stamped naming
from `LIVE_FEED.md` — never `part-000.parquet`), and writes each one as a
`raw.githubusercontent.com` URL into `02_data/_state/manifest.json`, grouped by
table:

```python
LIVE_FILE_RE = re.compile(r"^part-\d{8}-\d{2}\.parquet$")

def raw_url(rel_path: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/02_data/raw/{rel_path}"
```

An early version of this script also wrote a `generated_at` timestamp into the
manifest, "for debugging." That one field meant `manifest.json` was
byte-different on **every single run**, even a day with zero new data — which
meant `git diff --cached --quiet` above always found a diff, which meant the
no-op-day guard never actually fired, which meant a "no-op" day still produced
a commit and a push. The fix was one line: drop the timestamp. **Anything you
write into a file a downstream check compares byte-for-byte must itself be
free of anything that changes just because time passed** — the same
discipline as this project's seeded-RNG determinism (`ADR-002`), just showing
up one layer up the stack.

### Why this is safe to run unattended: the guarantees, applied

Every one of `LIVE_FEED.md`'s four guarantees is doing real work here, not just
sounding reassuring:

- **History is immutable** → the workflow can crash mid-run, be cancelled, or
  race with a manual trigger, and it can never corrupt a day already on
  record, because nothing in `live_feed.py`'s code path can open an existing
  file.
- **Days are reproducible from seeded RNG + reserved key blocks** → if a run
  is cancelled after generating but before committing, the next run's
  `--redo`-equivalent regeneration of that day produces byte-identical output.
  There is no "which half-finished version did we keep" question.
- **Gaps self-heal** → the 60-day-inactivity auto-disable, or a runner outage,
  or you forgetting this project existed for a week, all resolve the same way:
  the next successful run appends every missing day, each one correct.
- **Every append is verified before the watermark moves** → a bad run aborts
  before `git add` ever sees a corrupted table, so the worst case is "nothing
  got committed today," never "something wrong got committed today."

### The part that matters for Power BI: you don't even need to pull

`FactWarehouseTask` already has this pattern live in the model. Its Power
Query source is two queries `Table.Combine`d together:

```
FactWarehouseTaskFrozen
  = Parquet.Document(...) over the local, folder-combined
    02_data/raw/FactWarehouseTask/**/part-000.parquet tree

FactWarehouseTask_Live =
    let
        Manifest = Json.Document(Web.Contents(
            "https://raw.githubusercontent.com/Ays0172/meridian-logistics-analytics/main/02_data/_state/manifest.json"
        )),
        Urls    = Manifest[tables][FactWarehouseTask],
        Tables  = List.Transform(Urls, each Parquet.Document(Web.Contents(_))),
        Combined = Table.Combine(Tables)
    in
        Combined

FactWarehouseTask
  = Table.Combine({FactWarehouseTaskFrozen, FactWarehouseTask_Live})
```

`Manifest[tables]` is a record whose field names are table names — exactly
what `build_manifest.py` writes — so `Manifest[tables][FactWarehouseTask]` is a
list of URLs, one per live day, and `List.Transform` turns each URL into a
table. Refresh this query in Power BI Desktop, or on a schedule in the
Service, and it re-reads whatever the Action last pushed — **regardless of
whether your own machine has ever run `git pull`.** That decoupling (report
freshness depends on GitHub, not on your laptop) is the entire point of the
raw-URL pattern, and it is worth saying out loud once so it's not just a thing
that happens to work.

### Extending the pattern to the rest of the model

Eleven fact tables exist. `FactTarget` and `FactExchangeRate` are **deliberately
excluded from the live feed** (`LIVE_FEED.md` — targets are set by planners
annually, not produced by daily operations; exchange rates are read but only
extended on a full history rebuild), so they never get a `_Live` query and
never will — `FactTarget`'s Power Query source stays a plain local `Parquet.Document`
forever. `FactWarehouseTask` already has the pattern. That leaves **eight**
fact tables to wire up the same way: `FactBooking`, `FactShipment`,
`FactShipmentMilestone`, `FactPortCall`, `FactContainerMove`,
`FactFreightCharge`, `FactTransportLeg`, `FactInventorySnapshot` — exactly the
nine keys in `manifest.json` today, minus the one already done.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 29.1 — read the incident history (20 min)
Run (or read, if you don't have local `git` access to this repo) `git log
--oneline` on the real project. Find these three commits and, for each, write
one sentence explaining what broke and what the fix actually changed, in your
own words, without re-reading this file:
- `0cd5b65` — "Drop volatile timestamp from manifest.json..."
- `baede5f` — "Fix zip path separators at the source; bump cache key..."
- `f1690e3` — "Isolate frozen-history cache from git-managed raw dir..."

Predict, before checking each diff, which layer of the pipeline the bug lived
in (the generator, the workflow YAML, or the manifest script).

### Exercise 29.2 — trace a no-op day (15 min)
Run `python live_feed.py --status` (or read its output if this project's
watermark is already caught up on your machine). Predict what
`git diff --cached --quiet` would evaluate to on a day where the watermark is
already at today's date, then trace through the workflow step by step and
confirm no commit happens. State which single earlier bug (Exercise 29.1) would
have broken this exact scenario, and why.

### Exercise 29.3 — extend the pattern to one more table (30 min)
Pick `FactShipment` (chosen because it is small enough to iterate on quickly —
491,765 history rows). Write its `FactShipment_Live` Power Query M query
following the `FactWarehouseTask_Live` template exactly, and
`Table.Combine` it with a local `FactShipmentFrozen` query. Predict, before
refreshing, how many extra rows you should see versus the frozen-only version —
check `manifest.json`'s `FactShipment` array length against
`watermark.json`'s `daily_rows.FactShipment` average to build your estimate —
then refresh and compare.

### Exercise 29.4 — what happens if the schedule slips (15 min)
Suppose the Action does not run for six real days (a runner outage, or you
disable it while testing). Predict, in writing, what the very next successful
run appends, and whether the resulting `FactWarehouseTask` in your report
would look any different from six runs firing on time. Name the specific
guarantee that makes your prediction correct, and which file
(`watermark.json`) is what actually makes the "set difference, not a range"
computation possible run to run.

---

## Ship

Wire the `Frozen` + `_Live` Power Query pattern onto at least two more fact
tables beyond `FactWarehouseTask` and `FactShipment` (Exercise 29.3) —
`FactBooking` and `FactPortCall` are good next choices, being on the critical
path for Week 3's ocean-liner measures. For each, name the frozen query
`<Table>Frozen`, the live query `<Table>_Live`, and the combined output
`<Table>` (matching the existing `FactWarehouseTask` naming exactly, so nobody
has to guess the convention later).

Add a short paragraph to `06_portfolio/notes-live-feed.md` recording: the
manifest-timestamp bug and why it matters generally (not just for this
project), and the one sentence you'd give an interviewer for "how do you keep
a demo dataset alive without paying for hosting."

```
git add .
git commit -m "Day 29: live-feed GitHub Action reviewed, Frozen+Live pattern extended to FactShipment/FactBooking/FactPortCall"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can explain, without notes, why frozen history ships as a GitHub
      Release asset instead of a git-tracked file, and what problem the
      `_frozen_cache` / `raw` directory split solves.
- [ ] You can state why a volatile field in a generated file defeats a
      no-op-day commit guard, in general terms that apply beyond this project.
- [ ] `FactShipment`, `FactBooking`, and `FactPortCall` all have working
      `Frozen` + `_Live` Power Query pairs, verified against `manifest.json`'s
      row counts.
- [ ] You can say, from memory, all four live-feed guarantees and which one
      specifically licenses running this unattended.
- [ ] Predictions recorded, misses annotated.
