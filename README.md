# Meridian Logistics Analytics — master README

**This file is the single entry point. Everything else hangs off it.**

Ignore every earlier archive you were sent (`meridian-phase1`, `phase1b`, `phase2`,
`phase3`, `final`, `week2`). This package supersedes all six. Delete them once you
have unpacked this one — keeping them around is the only way to end up working from
a stale generator.

Built and verified: **21 August 2026**.

---

## 0. What this is

A synthetic but industry-faithful logistics data platform plus a six-week training
programme, built so you can walk into an Analyst / Manager interview at a container
carrier or 3PL and talk about the model, the metrics and the traps from experience
rather than from a textbook.

Four business domains, one conformed dimensional model:

| Domain | Covered by |
|---|---|
| Ocean liner / container shipping | FactBooking, FactShipment, FactPortCall, FactContainerMove |
| Landside logistics (road/rail) | FactTransportLeg |
| Warehousing / contract logistics | FactWarehouseTask, FactInventorySnapshot |
| Air & LCL freight forwarding | FactShipment (mode-split), FactFreightCharge |

---

## 1. Current state — read this before anything else

### Data

| | |
|---|---|
| History span | **2021-08-21 → 2026-08-20** (5.0 years) |
| Live appended days | **2026-08-21** (1 day, 5,348 rows — today) |
| Fact rows total | **7,487,802** |
| Dimension rows total | **32,878** |
| On-disk size | **515 MB** Parquet (snappy, hive-partitioned) |
| Seed | `20260824` — every byte reproducible |

Fact row counts:

| Table | Rows | Type |
|---|---|---|
| FactContainerMove | 1,939,641 | transaction |
| FactFreightCharge | 1,611,807 | transaction |
| FactInventorySnapshot | 983,262 | periodic snapshot |
| FactWarehouseTask | 737,368 | transaction |
| FactBooking | 573,726 | transaction |
| FactShipment | 491,765 | transaction |
| FactShipmentMilestone | 491,765 | **accumulating snapshot** |
| FactTransportLeg | 437,125 | transaction |
| FactPortCall | 131,097 | transaction |
| FactTarget | 51,900 | budget/target |
| FactExchangeRate | 38,346 | factless/rate |

Nineteen dimensions: DimDate (2,191), DimTime (1,440), DimCustomer (4,171, SCD2),
DimLocation (420), DimVessel (240), DimVoyage (9,270), DimService (44),
DimCarrier (180), DimEquipment (60), DimCommodity (900), DimSku (12,000),
DimWarehouse (26), DimEmployee (1,800), DimChargeType (48), DimCurrency (22),
DimIncoterm (12), DimMilestone (42), DimMode (8), DimScenario (4).

### Verification — all three checkers re-run against this exact package

```
validate.py    14 / 14 contract gates passed
audit.py       66 / 67 checks clean   0 errors   1 warning (benign)
crosscheck.py  44 / 45 checks clean   0 errors   1 warning (benign)
```

The two warnings are known and intentional: `FactTarget.CurrencyKey` is constant
because all targets are set in USD, and one crosscheck flags a spread it cannot
distinguish from a deliberate landmine. Neither is a defect. Reports live in
`02_data/_validation/`.

### Reproducibility — proven, not asserted

The build was run **twice, in separate processes, under deliberately different
`PYTHONHASHSEED` values**, and all **689 Parquet partitions came out bit-identical**.

This is not a formality. A clean-room rebuild before packaging is what caught the
bug in ADR-002: `revise_voyage_rotations.py` was sampling port codes from a Python
`set` of strings, and CPython randomises string hashing per process, so the *order
of the pool being sampled from* changed every run. The seed was fine; the pool was
shuffled. DimVoyage diverged and eight fact tables followed it — while row counts
stayed identical and 13 of 14 gates still passed, which is exactly why it had gone
unnoticed.

Read `00_docs/ADR/ADR-002-build-determinism.md` before you touch the generator.
`01_generator/tests/test_determinism.py` now guards it.

Live-feed guarantees, re-proven on this build: history SHA-256 bit-identical across
an append/redo cycle, and a redone day byte-identical to its first write.

### What is built

- ✅ `00_docs` — schema contract, KPI dictionary (72 KPIs), live-feed manual, landmine list, ADR
- ✅ `01_generator` — full generator, 3 independent checkers, live feed, unit tests
- ✅ `02_data` — the 7.5M-row dataset, built and verified
- ✅ `04_learning/week1` — Days 1–7 + solutions
- ✅ `04_learning/week2` — Days 8–14 + solutions + 109 ground-truth reference answers
- ✅ `04_learning/week3` — Days 15–21 + solutions (the ~150-measure DAX library, by KPI domain then function)
- ✅ `04_learning/week4` — Days 22–28 + solutions (the five report pages)
- ✅ `04_learning/week5` — Days 29–35 + solutions (automation, RLS, performance, deployment)
- ✅ `04_learning/week6` — Days 36–42 + solutions (SQL, case drills, PL-300, portfolio, capstone)
- ✅ `04_learning/CURRICULUM_ROADMAP.md` — topic/deliverable index for Weeks 3–6

All 42 days are written, in the same prediction-first format, with a worked solution
file for each. The curriculum is complete end to end — see §5 for how to work through it.

### What you build as you go — empty by design, not by omission

- ⬜ `03_powerbi` — **empty except `data_quality_findings.md`.** The .pbip/TMDL
  semantic model and the measure library are not shipped pre-built — building them
  *is* Weeks 1–3 (model in Weeks 1–2, the measure library in Week 3). Day 14's
  checkpoint expects real committed measures already; Week 4 (Days 22–28) then
  builds the five report pages on top of that model, and by Day 28 all five should
  be live here.
- ⬜ `05_sql` — **empty.** The DuckDB build and graded exercises are Day 36's deliverable.
- ⬜ `06_portfolio` — **empty on disk; not a Week 6-only deliverable.** First written
  on Day 9 (`notes-averaging.md`), added to again on Days 11, 22, 23, 28, 29 and 35,
  then built out properly in Week 6 (Days 37–42: case drills, PL-300 gap analysis,
  STAR stories, the case-study writeup, mock-interview results, retrospective).

You have everything you need to start Monday and run the full six weeks without
waiting on anyone.

---

## 2. Directory map

```
Meridian-Logistics-Analytics/
├── README.md                     ← you are here
├── SETUP.ps1                     ← Windows: run this once, then walk away
├── setup_all.py                  ← the cross-platform equivalent
├── MANIFEST.txt                  ← every file in this package, with checksums
│
├── 00_docs/
│   ├── start-here.html           ← OPEN THIS FIRST (Day Zero, 9 steps)
│   ├── SCHEMA_CONTRACT.md        ← the frozen spec. 19 dims, 11 facts, 14 gates
│   ├── KPI_DICTIONARY.md         ← 72 KPIs with DAX, targets, watch-outs
│   ├── LIVE_FEED.md              ← operator manual for the daily append
│   ├── LANDMINES.md              ← the 10 deliberate data-quality defects
│   └── ADR/
│       ├── ADR-001-voyage-rotation-length.md
│       └── ADR-002-build-determinism.md   ← read before editing the generator
│
├── 01_generator/
│   ├── requirements.txt          ← pip install -r this first
│   ├── build_dims.py             ← step 1
│   ├── revise_voyage_rotations.py← step 2
│   ├── build_facts.py            ← step 3
│   ├── validate.py               ← step 4  (14 contract gates)
│   ├── audit.py                  ← step 5  (67 adversarial checks)
│   ├── crosscheck.py             ← step 6  (45 cross-table checks)
│   ├── live_feed.py              ← step 7  (daily append, run every morning)
│   ├── config/scale.yaml         ← the scale dial
│   ├── tests/test_util.py        ← 19 unit tests
│   ├── tests/test_determinism.py ← 2 tests: the build must be seed-pure
│   └── meridian/                 ← the library (config, dims, facts_*, factio, util)
│
├── 02_data/
│   ├── raw/<Table>/year=YYYY/month=MM/part-*.parquet   ← CREATED BY SETUP, 515 MB
│   ├── reference/                ← all 19 dimensions as readable CSV (shipped)
│   ├── _state/watermark.json     ← live-feed state, created by setup. DO NOT hand-edit
│   └── _validation/              ← checker reports. My verified run is shipped here
│                                    for comparison; setup overwrites with yours
│
├── 03_powerbi/                   ← your .pbip/TMDL model and measures land here, built Weeks 1–3
│   └── data_quality_findings.md  ← shipped; a worked audit of the live model, read from Days 30–34
│
├── 04_learning/
│   ├── CURRICULUM_ROADMAP.md     ← topic/deliverable index for Weeks 3–6
│   ├── week1/D01…D07             ← domain, codes, modelling, PQ, relationships, dates+SCD2, checkpoint
│   ├── week2/D08…D14             ← contexts, CALCULATE, iterators, time intelligence, snapshots,
│   │                                TREATAS/ABC, calculation groups, checkpoint
│   ├── week2/_reference_answers.json      ← 109 ground-truth values; every drill is checkable
│   ├── week2/build_reference_answers.py    ← regenerates them after any rebuild
│   ├── week3/D15…D21             ← KPI→DAX method, the ~150-measure library by domain, checkpoint
│   ├── week4/D22…D28             ← report shell, five dashboard pages, UX checkpoint
│   ├── week5/D29…D35             ← live-feed automation, refresh, RLS, performance, TMDL, checkpoint
│   ├── week6/D36…D42             ← SQL primer, case drills, PL-300 mapping, STAR stories, portfolio, capstone
│   └── solutions/week1…week6     ← full worked solutions, one per day. read AFTER attempting
│
├── 05_sql/                       ← EMPTY until Day 36
└── 06_portfolio/                 ← EMPTY on disk; first written Day 9, built out in Weeks 4–6
```

---

## 3. Setup — one command

Unpack to `C:\Users\AyushSood\Data\Meridian-Logistics-Analytics\`, then:

```powershell
.\SETUP.ps1
```

That is the whole thing. It creates a virtual environment, installs `pandas`,
`numpy`, `pyarrow` and `pyyaml`, builds all 19 dimensions and 11 fact tables, runs
all three checkers, and brings the live feed up to today. Roughly **25–35 minutes**
and about **550 MB** of disk. Leave it running.

On macOS or Linux, or if you prefer to manage your own environment:

```bash
pip install -r 01_generator/requirements.txt
python setup_all.py
```

### Why the archive does not contain the 515 MB of Parquet

Because it does not need to. The build is fully seeded (`SEED = 20260824`), so
running `setup_all.py` produces a dataset **byte-identical** to the one I built and
verified here. Shipping the generator *is* shipping the data, at 4 MB instead of
515 MB — and it means the three checkers run on your machine, against your build,
which is a stronger guarantee than me telling you the transfer was clean.

The 25 minutes is a one-time cost and it is the last time you will pay it.

If you would rather have the Parquet files transferred directly, say so and I will
split them into chunks and send them across — it is just slower and proves less.

### What `setup_all.py` runs, in order

Order matters. Skipping step 2 leaves voyage rotations too short and gate 14 fails.

| # | Script | What it does |
|---|---|---|
| 1 | `build_dims.py` | 19 dimensions, 32,878 rows, SCD2 on DimCustomer |
| 2 | `revise_voyage_rotations.py` | ADR-001: lengthens rotations to a realistic 15 calls |
| 3 | `build_facts.py` | 11 facts, 7,487,802 rows — the long step |
| 4 | `validate.py` | 14 contract gates. Expect **14/14** |
| 5 | `audit.py` | 67 adversarial checks. Expect **66/67, 0 errors** |
| 6 | `crosscheck.py` | 45 cross-table checks. Expect **35/37, 0 errors** — see below |
| 7 | `live_feed.py` | Bootstraps the watermark, appends every day since 2026-08-20 |
| 8 | `crosscheck.py` again | Expect **44/45, 0 errors** |

Why crosscheck runs twice: eight of its checks compare the appended rows against
the history they extend, so they cannot run before a live day exists. The first pass
skips them and reports 35/37; the second reports the full 44/45. Both are correct,
and the second is the one that actually tests live-vs-history continuity.

Useful flags: `--skip-build` (verify an existing build), `--skip-feed`,
`--no-fail-fast`.

**If any of steps 4–6 reports an error rather than a warning, stop and tell me the
output.** Warnings are expected — there is exactly one benign warning in each of
`audit.py` and `crosscheck.py`, described in §1. Errors are not.

---

## 4. The live feed — your "real system"

This is the piece that makes the model feel alive. Full manual in
`00_docs/LIVE_FEED.md`; the short version:

```powershell
python live_feed.py             # append every day up to today
python live_feed.py --status    # show watermark, last date, row counts
python live_feed.py --until 2026-09-30   # simulate forward
python live_feed.py --redo 2026-08-24    # regenerate one day byte-identically
```

**Four guarantees, each proven empirically, not asserted:**

1. **History is immutable.** Rows dated ≤ 2026-08-20 are never rewritten. Proven by
   SHA-256 fingerprint per table before and after appends, redos and backfills —
   bit-identical every time.
2. **Days are reproducible.** Each date draws from its own seeded RNG stream and its
   own reserved block of 50,000 surrogate keys, so `--redo` produces a byte-identical
   file. This is what makes "today I got 1–10, tomorrow it starts at 11" true rather
   than hopeful.
3. **Gaps self-heal.** Miss three days, run it once, and it appends exactly those
   three — computed as a set difference against recorded run dates, so a watermark
   rewind cannot double-append.
4. **Every append is verified before the watermark moves.** Row count, key
   uniqueness and date range are checked; on failure the append is rolled back and
   the watermark stays put.

**Automate it** with Windows Task Scheduler (recipe in `LIVE_FEED.md`, §"Daily
automation") if you're running this by hand. A GitHub Actions + raw-URL version
already runs daily (`.github/workflows/live-feed.yml`) — Week 5 Day 29 doesn't
build this from scratch, it has you read, understand, and formalize what's already
live, which is where that belongs pedagogically. Task Scheduler is the fallback for
anyone not using GitHub Actions.

**Power BI note.** Point Power BI at the `02_data/raw` folder with Parquet + folder
combine. Do not build on push/streaming datasets: Microsoft is retiring them and
creation stops 31 October 2027. Scheduled refresh gives you 8/day on Pro, 48/day on
PPU — plenty for a daily feed.

---

## 5. Where to start on Monday

1. **Open `00_docs/start-here.html`** in your browser. It is a nine-step Day Zero
   guide written for someone who has never touched this repo. Do all nine steps.
2. Then `04_learning/week1/D01-domain-foundations.md`. One day per file, in order.
3. **Write your predictions before you run anything.** Every module asks for this.
   It is the whole method — a prediction you got wrong teaches you something a
   correct answer you never doubted cannot.
4. Read the matching file in `04_learning/solutions/` only *after* you have
   attempted the drill. Every number in the solutions was computed from this exact
   dataset, so they are checkable, not illustrative.
5. `04_learning/week2/_reference_answers.json` holds 109 ground-truth values. If your
   measure disagrees with it, your measure is wrong — that is the point of shipping it.
   It is regenerated by `04_learning/week2/build_reference_answers.py`, so if you ever
   change the generator, run that script or the answer key silently stops matching.

Budget 15–20 hours a week, six weeks end to end. Week 1 is modelling and Power
Query; Week 2 is DAX semantics, which is where the actual difficulty lives; Week 3
turns that into the full measure library; Week 4 builds the five report pages; Week 5
covers automation, security, and performance; Week 6 is SQL, interview prep, and the
capstone retrospective. Weeks 1–5 each close with a checkpoint day (D07, D14, D21,
D28, D35) that reviews the week before moving on; Week 6 closes with D42, a
retrospective rather than a checkpoint.

---

## 6. The things worth knowing about this dataset

Verified numbers you should be able to quote:

| Metric | Value |
|---|---|
| Schedule reliability (vessel, vs published ETA ±1 day) | **0.6598** |
| Delivery on-time (cargo, vs promised date) | **0.9130** |
| Perfect order rate | **0.8574** |
| Revenue per FFE — headhaul / backhaul | **2,482.78 / 1,286.66** |
| Empty container share | **0.3197** |
| Gross margin, mean | **0.1802** (2.26% of shipments loss-making) |
| Top-10 customer revenue share | **27.8%** |
| Total revenue, all years | **2,040,774,144 USD** |
| Revenue CAGR 2022→2025 | **5.78%** (crosscheck reports 5.89% on its booking-volume series) |

Two facts that trip up almost everyone, both deliberately modelled:

- **Schedule reliability (0.66) and delivery OTIF (0.91) are different metrics on
  different fact tables.** One measures a vessel against its published schedule, the
  other measures cargo against a promise that carries slack. Conflating them is the
  single most common logistics-analytics error, and being able to explain the
  difference cold is worth more in an interview than any DAX trick.
- **A nine-week congestion crisis at Rotterdam and Los Angeles (July–Sept 2025)
  drops those two ports to 0.405 reliability on the industry-standard rolling 8-week
  window, while the network headline barely moves — 0.662 against 0.670 for
  unaffected ports.** 131 calls out of 4,049 is 3.2% of the population, so a 40%
  local failure shifts the average by 1.3%. Day 11 makes you find this yourself —
  including the sting in the tail, that sorting ports ascending by reliability does
  *not* surface the crisis, because sparse ports with eleven calls rank below it.
  It is the best "what would you put on an executive dashboard?" answer you will
  ever have, because you can put arithmetic behind it.

**Ten deliberate data-quality landmines** are seeded into the data — duplicate
booking references, casing and whitespace inconsistencies in location names, two
spellings of one country, late-arriving customer rows, implausible vessel capacity
outliers, unset optional fields, negative credit-note lines, and more. They are
catalogued in `00_docs/LANDMINES.md`. **Do not read that file until Week 1 Day 4
tells you to** — finding them yourself in Power Query is the exercise.

---

## 7. Conventions, so nothing surprises you

- Surrogate keys are `int32`, named `<Table>Key`. Unknown member is always **`-1`**
  with label `#NA` / `Unknown`. `-1` is not a small number and not a date — every
  comparison against it needs an explicit branch (Day 11 Exercise 11.6 proves why).
- Date keys are `int32` `yyyymmdd`. `DimDate` runs 2021-01-01 → 2026-12-31 —
  deliberately wider than the facts, because a date table that stops mid-year makes
  `DATESYTD` wrong in the final year.
- Money is stored as `_doc` (document currency) + `_usd` pairs. Always aggregate the
  `_usd` column.
- Booleans are `int8` with an `is_` prefix, so they can be averaged into a rate.
- **Fiscal year starts 1 October and is named for the year it ends in** — Oct 2025
  to Sep 2026 is FY26. In DAX that is `DATESYTD(DimDate[Date], "09-30")`.
- Not-yet-happened dates in the accumulating snapshot hold `-1`, not null.

---

## 8. What's left, and whose it is

The curriculum is done — all 42 days, Weeks 1–6, each with a worked solution file.
What's left isn't more writing, it's the work each day asks you to do:

1. **`03_powerbi`** — build the .pbip/TMDL semantic model as Weeks 1–3 direct: 19
   dimensions and 11 facts wired (Week 1), then the ~150-measure DAX library
   organised into display folders (Week 3, on top of Week 2's DAX mechanics)
2. **The five dashboard pages** — Week 4, Days 22–28, on top of that model
3. **Automation, RLS, performance, deployment** — Week 5, Days 29–35, including the
   GitHub Actions live feed formalized in Day 29
4. **`05_sql`** — the DuckDB build and its graded exercises, Day 36
5. **`06_portfolio`** — case drills, PL-300 gap analysis, STAR stories, case-study
   writeup, mock interview, and the capstone retrospective, Days 37–42 (on top of
   the design-rationale notes the folder already started collecting from Day 9
   onward)

Start at `04_learning/week1/D01-domain-foundations.md` and work in order — each day
tells you what it needs from the one before it.
