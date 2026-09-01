# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two things bolted together on purpose:

1. **A seeded synthetic logistics dataset generator** (`01_generator/` → `02_data/`) — 19
   dimensions, 11 facts, 7.5M rows, byte-for-byte reproducible from `SEED = 20260824`.
2. **A 6-week, 42-day Power BI / DAX / SQL curriculum** (`04_learning/`) built to run
   entirely against that dataset, ending in a 5-page Power BI report (`03_powerbi/`),
   a DuckDB/SQL module (`05_sql/`), and a portfolio write-up (`06_portfolio/`).

The dataset is the curriculum's only source of truth: every drill answer, every KPI
target band, every "verified number" in `README.md` §6 was computed from this exact
seeded build, not illustrative. Read `00_docs/SCHEMA_CONTRACT.md` (the frozen 19-dim/
11-fact spec), `00_docs/KPI_DICTIONARY.md` (72 KPIs, split into 5 domains, with DAX
given verbatim), and `00_docs/LANDMINES.md` (10 deliberately seeded data-quality
defects — do not read this before Week 1 Day 4 if you're doing the curriculum
yourself, the exercise is finding them) before changing generator or KPI content.

## Commands

### Full setup (build data + run all checkers + bootstrap live feed)
```bash
pip install -r 01_generator/requirements.txt
python setup_all.py                    # cross-platform; SETUP.ps1 is the Windows-native equivalent
python setup_all.py --skip-build       # verify an existing build without rebuilding
python setup_all.py --skip-feed        # build + validate, skip the live-feed bootstrap
python setup_all.py --no-fail-fast     # keep going past a checker error instead of stopping
```

### Generator pipeline, run individually (order is load-bearing — see Architecture)
```bash
cd 01_generator
python build_dims.py                   # step 1: 19 dimensions
python revise_voyage_rotations.py      # step 2: ADR-001, lengthens rotations to ~15 calls
python build_facts.py                  # step 3: 11 facts, 7.5M rows
python validate.py                     # step 4: 14 contract gates — expect 14/14
python audit.py                        # step 5: 67 adversarial checks — expect 66/67, 0 errors
python crosscheck.py                   # step 6: 45 cross-table checks — expect 35/37 pre-feed
python live_feed.py                    # step 7: bootstrap watermark, append every day since 2026-08-20
python crosscheck.py                   # step 8: re-run — expect 44/45 (8 checks need live rows to exist)
```
A warning from `validate`/`audit`/`crosscheck` is expected (one benign warning each,
documented in `README.md` §1). An **error** from any of them is not — stop and diagnose,
don't skip.

### Live feed (daily append; this is what `.github/workflows/live-feed.yml` runs)
```bash
cd 01_generator
python live_feed.py                     # append every day up to today
python live_feed.py --status            # show watermark, last date, row counts
python live_feed.py --until 2026-09-30  # simulate forward
python live_feed.py --redo 2026-08-24   # regenerate one day byte-identically
python build_manifest.py                # regenerate manifest.json Power BI reads for folder discovery
```

### Tests
```bash
python -m pytest 01_generator/tests/test_util.py -v          # 19 unit tests: RNG, check-digit algorithms
python -m pytest 01_generator/tests/test_determinism.py -v   # build-is-a-pure-function-of-the-seed guard (see ADR-002)
```
`test_util.py` also self-runs via `unittest` (`python 01_generator/tests/test_util.py`).
`test_determinism.py` runs the generator twice under deliberately different
`PYTHONHASHSEED` values and diffs the output — it's slow (spawns subprocesses) but is
the only thing that catches an order-dependent-hash regression before a clean-room
build silently diverges from what was verified.

### KPI answer key
```bash
python 04_learning/week2/build_reference_answers.py
```
Regenerates `04_learning/week2/_reference_answers.json` (109 ground-truth values
drills are checked against). **Run this after any change to the generator** — the
answer key is derived from the data, not hand-maintained, and silently stops matching
if the data changes underneath it.

## Architecture

### Generator (`01_generator/`)

Build order is enforced by `build_dims.py`/`build_facts.py` and is not arbitrary —
later dims/facts take earlier ones as constructor args (e.g. `DimVoyage` needs
`DimVessel`, `DimService`, `DimLocation`; `DimSku` needs `DimCommodity` and
`DimCustomer`). Fact build order within `build_facts.py`:
```
FactExchangeRate → FactBooking → FactShipment → FactShipmentMilestone   (facts_core.py, §2.1-2.3, 2.10)
FactPortCall → FactContainerMove → FactFreightCharge                    (facts_ops.py, §2.4-2.6)
FactTransportLeg · FactWarehouseTask · FactInventorySnapshot · FactTarget (facts_land.py, §2.7-2.9, 2.11)
```
`FactExchangeRate` must exist before anything else — every money column downstream is
converted at the rate in force on the transaction date. All fact generation is
vectorised; a Python-level loop over fact rows is a bug, not a style choice (loops
over dimension members — 44 services, 22 currencies — are fine).

`meridian/config.py` holds the master seed, calendar bounds, fiscal-year start month,
and the unknown-member sentinel values — the single place per-run constants live.
`meridian/util.py` holds the seeded-RNG discipline and business-key check-digit
algorithms shared by every builder. `meridian/factio.py` writes Hive-partitioned
Parquet (`02_data/raw/<Table>/year=YYYY/month=MM/part-*.parquet`) with partition
columns *not* duplicated inside the file, by design — Power Query's folder-combine
and Parquet's Hive discovery both recover them from the path.

**Determinism is the load-bearing property of the whole package** (ADR-002): the
archive ships a 4 MB generator instead of 515 MB of Parquet because anyone running
`setup_all.py` gets a byte-identical dataset. The failure mode that broke this once
(iterating a Python `set` of strings, whose order depends on per-process
`PYTHONHASHSEED`) produced identical row counts and passed 13/14 gates while being
silently wrong — read `00_docs/ADR/ADR-002-build-determinism.md` before touching
anything in `meridian/` that iterates a collection and reaches an RNG.

**Live-feed guarantees** (`00_docs/LIVE_FEED.md` has the full manual): history rows
dated ≤ 2026-08-20 are immutable and proven so by SHA-256 fingerprint across
appends/redos; each date draws from its own seeded RNG stream and reserved key block,
so `--redo` is byte-identical; gap-healing is a set-difference against recorded run
dates, so a watermark rewind can't double-append; every append is verified (row
count, key uniqueness, date range) before the watermark moves, rolled back on failure.

### Curriculum (`04_learning/`)

42 day files across `week1`–`week6`, one topic per day, every one following the same
structure: **Spaced recall → Concept → Drill → Ship → Log → Exit criteria**. Every day
file has a matching worked-solution file in `04_learning/solutions/week*/D##-solutions.md`
— written with real numbers computed from this exact dataset, meant to be read only
after attempting the drill. `04_learning/CURRICULUM_ROADMAP.md` is the topic/deliverable
index for Weeks 3–6.

Weeks 1–2 (`D01`–`D14`) build the dimensional model, Power Query, and DAX mechanics.
Week 3 (`D15`–`D21`) turns the KPI dictionary's 72 codes into the ~150-measure
`_Measures` library. **Folder taxonomy is two levels, both load-bearing, defined in
`week3/D15`:** top level is KPI domain (`05 Ocean Liner` … `09 Cross-Cutting`,
mirroring `KPI_DICTIONARY.md` §1–§5 and Week 4's five dashboard pages 1:1); nested
inside each domain is a function subfolder derived deterministically from the KPI
code's own middle segment — `VOL/MIX/WT/INV → Volume & Mix`, `UTL/REL/TRN/OPS/PRD →
Rate & Utilisation`, `REV/CST/FIN/SLS/CUS → Revenue & Cost` (`CUS` only because
`XCT.CUS.CONC`, Revenue Concentration, is a revenue-share measure despite the
customer-flavoured segment name — check the dictionary, not just the segment
string, for anything that doesn't obviously fit), `QLT/SVC/CAR/SUS → Quality &
Service`. **Not every domain gets all four subfolders** — a bucket only exists if
one of its segments actually appears in that domain's own KPIs (Power BI won't
render an empty folder anyway), and only Warehouse's 18 KPIs touch all four; Ocean,
Landside and Air & LCL each produce 3, Cross-Cutting only 2. Treat "which buckets
does domain X get" as something to verify against `KPI_DICTIONARY.md`'s actual
segments before stating it, not something to assume uniformly — an earlier version
of this taxonomy claimed "exactly four everywhere" and was wrong for 4 of 5
domains, caught only by an explicit adversarial review. Every measure also carries
a `[KpiCode]` prefix in its Description property — the join key back to the
dictionary, checked by Day 21's checkpoint (every one of the 72 codes must appear
in exactly one measure's description, or be logged as a deliberate gap, and
`XCT.SCOR.MAP` is the one code that isn't a measure and never gets foldered at
all). A `[DO NOT USE] <Name> (naive)` measure always ships in the *same*
domain+function subfolder as its correct sibling, never a separate "deprecated"
folder — the trap needs to be visible to the next person who opens that folder,
not hidden.

Week 4 (`D22`–`D28`) builds the five report pages this folder taxonomy feeds, one
page per KPI domain plus an Executive Summary; each day's file specifies every
visual, its exact measure(s), chart type, and the decision it supports. Week 5
(`D29`–`D35`) is automation/RLS/performance/TMDL deployment. Week 6 (`D36`–`D42`) is
SQL (DuckDB), case drills, PL-300 mapping, and portfolio packaging — this is where
`05_sql/` and `06_portfolio/` (empty on disk by design) get filled in.

### Keeping docs in sync

`README.md` §1 ("What is built"), `04_learning/CURRICULUM_ROADMAP.md`, and
`MANIFEST.txt` are status claims about what exists on disk, not just narrative —
all three have gone stale before (README/ROADMAP described Weeks 2–6 as unwritten
after those weeks were already committed; MANIFEST.txt was still listing a build
from before Weeks 3–6 existed, missing 56 files, until it was regenerated).
**Any commit that adds/removes a day file, changes the folder taxonomy, or finishes a
previously-empty `03_powerbi`/`05_sql`/`06_portfolio` deliverable should update
README/ROADMAP in the same commit**, not as a follow-up; regenerate `MANIFEST.txt`
(sha256sum + byte count per `git ls-files`, excluding `02_data/raw/` — see its own
header — and excluding itself from its own listing) whenever the file set changes
non-trivially. Grep for the specific claim you're invalidating before writing the
fix, rather than assuming the rest of the file is still accurate — and don't just
assume the *new* claim is right either: a claim like "every domain gets N of these"
needs checking against the actual data it generalizes over (here,
`KPI_DICTIONARY.md`'s real segment lists), not just internal consistency with the
surrounding prose. Wrong-but-consistent is still wrong.

### The lesson prose itself needs the same discipline, not just the status docs

A full adversarial pass over Weeks 4–6 (42 day files + solutions, previously
unaudited beyond Week 3) turned up ~30 more real defects, none of them structural
— wrong day-citations (a technique attributed to the wrong day, e.g. "Day 1" for
something that's actually Day 11), KPI/domain counts that don't match
`KPI_DICTIONARY.md`, arithmetic that doesn't reduce (a stated total that isn't the
sum of its own line items), DAX that isn't valid syntax or uses the wrong function
variant, and — the most load-bearing category — the same fact stated two
different, contradictory ways in two different files (a bug's symptom described
as "wrong" in one file and "returns nothing" in another; a design decision from
one day flatly contradicted by a "recap" of it in a later day's solutions). None
of these announce themselves — they read as fluent, confident prose exactly like
the correct material around them. Before trusting or extending any specific claim
in a day/solutions file (a number, a day cross-reference, a DAX snippet, "X is the
largest/smallest of Y"), check it against the file it actually depends on
(`KPI_DICTIONARY.md`, `SCHEMA_CONTRACT.md`, README §6, the cited day itself) rather
than the file that states it.

## Conventions worth knowing before editing generator or model code

- Surrogate keys: `int32`, named `<Table>Key`. Unknown member is always `-1` /
  `#NA` / `Unknown` — except `DimDate`/`DimTime` and two dimensions whose contract
  pins them to a closed real-world code list with no `#NA` slot (see `dims.py`'s
  module docstring for which two, and why).
- Money: `_doc` (document currency) + `_usd` pairs. Always aggregate `_usd`.
- Booleans: `int8` with an `is_` prefix, so they can be averaged into a rate.
- Fiscal year starts 1 October, named for the year it ends in (Oct 2025–Sep 2026 =
  FY26) — `DATESYTD(DimDate[Date], "09-30")` in DAX.
- Date keys: `int32` `yyyymmdd`. `DimDate` deliberately runs wider than the facts
  (2021–2026) so `DATESYTD` doesn't break in the final year.
