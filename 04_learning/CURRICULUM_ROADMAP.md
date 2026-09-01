# Curriculum Index — Weeks 3–6 (Days 15–42)

**Status: complete.** All six weeks (`week1/D01` through `week6/D42`) exist as full
lesson files, each with a matching worked solution in `solutions/`. Every day
follows the same prediction-first method — drills checkable against this exact
dataset, solutions shipped separately — established in Week 1. Most days share the
same six-heading skeleton (Spaced recall → Concept → Drill → Ship → Log → Exit
criteria); checkpoint and Part-A/B/C days (D14, D21, D28, D35) substitute a
verification/checkpoint structure for Concept/Drill/Ship, and D42 substitutes a
retrospective. Checkpoints land on Days 7, 14, 21, 28, and 35; Day 42 is the
capstone retrospective, not a sixth checkpoint.

This file is the topic-and-deliverable map for Weeks 3–6 (Days 15–42) — use it to see
what a week covers before opening the day file, or to find which day covers a given
KPI domain or skill. For Weeks 1–2 (Days 1–14), see the directory map in the root
`README.md` §2.

Grounded in what's actually in the repo: the 72 KPIs in `00_docs/KPI_DICTIONARY.md`
split into 5 domains (Ocean liner ×22, Landside ×16, Warehouse & inventory ×18, Air &
LCL ×9, Cross-cutting ×7) — that split is where the "five dashboards" the README
promises come from. The GitHub Actions live feed the README slots into Week 5 is the
same manifest.json + raw-URL Parquet pattern already wired into `FactWarehouseTask_Live`
in the live model — Week 5 formalizes and automates what's already partially built.

---

## Week 3 — Model to Measures (Days 15–21)

The DAX skills from Week 2 (row/filter context, CALCULATE, iterators, time intelligence,
snapshot patterns, calculation groups) get applied to build the real measure library —
`03_powerbi`'s ~150 measures, organized by KPI domain, then by function within each
domain (not every domain uses all four function buckets — see Day 15).

| Day | Topic | Deliverable |
|---|---|---|
| D15 | KPI → DAX translation method; measure-table pattern (`_Measures`, created Day 8, not measures scattered across fact tables); two-level domain/function display folder taxonomy | `_Measures` carries its first domain-foldered, function-subfoldered measures; folder structure agreed |
| D16 | Ocean liner measures (22 KPIs) — schedule reliability on the rolling 8-week window, headhaul/backhaul load factor, slot utilisation | ~22 measures, checked against `00_docs/KPI_DICTIONARY.md` §1 |
| D17 | Landside measures (16 KPIs) — DIFOT, deadhead %, carrier composite score | ~16 measures, checked against §2 |
| D18 | Warehouse & inventory measures (18 KPIs) — OTIF decomposed as DIF × DOQ × DOT, ABC class mix, inventory turns | ~18 measures, checked against §3 |
| D19 | Air & LCL measures (9 KPIs) — the 1:6000 vs 1:5000 chargeable-weight variants, yield per kg | ~9 measures, checked against §4 |
| D20 | Cross-cutting / executive measures (7 KPIs) — company-wide perfect order rate, cash-to-cash cycle time, margin dispersion, the SCOR level-1 map | ~7 measures, checked against §5 |
| D21 | **Checkpoint 3** — every measure spot-checked against a known value (the numbers in README §6 — schedule reliability 0.6598, delivery on-time 0.9130, OTIF ~0.867, etc. — are the answer key); Day 14's calculation groups cross-checked against this week's measures so every measure gets MTD/QTD/YTD for free instead of ×4 duplicated measures | Full measure library, verified against the dictionary and calc-group time intelligence |

## Week 4 — Report Design & the Five Dashboards (Days 22–28)

| Day | Topic | Deliverable |
|---|---|---|
| D22 | Report design principles — page-level filters, a navigation shell, theme, one page = one decision it supports | Report shell + nav |
| D23 | Ocean Liner dashboard | Page 1 |
| D24 | Landside dashboard | Page 2 |
| D25 | Warehouse & Inventory dashboard | Page 3 |
| D26 | Air & LCL dashboard | Page 4 |
| D27 | Executive / cross-cutting summary — the "what would you put in front of a CFO" page, drilling through into the 4 domain pages; this is also where the Rotterdam/LA congestion story (README §6) becomes a visual | Page 5 (exec summary) |
| D28 | **Checkpoint 4** — UX pass: tooltips, bookmarks, drillthrough wiring, mobile layout, basic accessibility (contrast, alt text) | 5-page report, polished |

## Week 5 — Automation, Security, Performance (Days 29–35)

| Day | Topic | Deliverable |
|---|---|---|
| D29 | GitHub Actions live feed — turn the manual `live_feed.py` run into a scheduled workflow that publishes to the same raw-URL manifest pattern `FactWarehouseTask_Live` already reads | Working GitHub Actions workflow, daily append verified |
| D30 | Scheduled refresh in Power BI Service — refresh limits (8/day Pro, 48/day PPU), incremental refresh policy design over `02_data/raw` | Refresh policy documented and applied |
| D31 | Row-level security — security roles (e.g. per-customer, per-region), DAX filter patterns, tested with View As | 1–2 working RLS roles, tested |
| D32 | Performance tuning — VertiPaq-style cardinality thinking, Performance Analyzer on the 5 report pages, star-schema anti-patterns to check for (this ties directly back to the relationship/hide/format cleanup already done this session) | Slowest visuals identified and fixed |
| D33 | Deployment pipeline — `.pbip`/TMDL source control (the format this whole project already uses on disk), a git-friendly workflow for model changes | Model under version control end to end |
| D34 | Data-quality landmine audit, formalized — turn what was found this session (the `#NA` placeholder bug, the dead `ContainerNo` columns) into a repeatable checklist; cross-check against the 10 seeded defects in `00_docs/LANDMINES.md` and find whichever you haven't caught yet | Checklist doc + landmine scorecard |
| D35 | **Checkpoint 5** — end-to-end dry run: fresh refresh, RLS re-tested, performance benchmark re-run | Everything green |

## Week 6 — Capstone & Interview Readiness (Days 36–42)

This is where `05_sql` (empty until Day 36) and `06_portfolio` (empty on disk, but
already collecting design-rationale notes since Day 9) get their main content —
not as a separate track, but as this week's actual work.

| Day | Topic | Deliverable |
|---|---|---|
| D36 | SQL primer over the same dataset via DuckDB — re-derive 3–4 of the measures you already wrote in DAX, in SQL, to prove the concepts transfer | First SQL queries against `02_data/raw` |
| D37 | Case-style drills — timed "here's a business question, build the answer" exercises using the finished model | Drill log with timings |
| D38 | PL-300 exam-pattern review — map what Weeks 1–6 covered onto the PL-300 skill areas, identify real gaps | Gap list |
| D39 | STAR story-writing — turn this project's actual debugging into interview stories (the mis-wired `FactContainerMove` relationship, the `"#NA"`-vs-blank bug, the congestion-event KPI finding) | 3–4 STAR stories drafted |
| D40 | Portfolio packaging — case-study writeup for `06_portfolio`, screenshots/GIFs of the 5-page report | Portfolio piece drafted |
| D41 | Mock interview / mock exam, full run | Scored mock results |
| D42 | Capstone review + retrospective — what changed since Day 1, what's genuinely still weak, what's next | Retrospective written |

---

## What's left

The curriculum itself (all 42 day files + 42 solution files) is written and in place.
What's still genuinely open, and owned by whoever is running the curriculum rather than
by these files, is the actual work each day asks for:

- `03_powerbi` — the .pbip/TMDL semantic model, dimensions, relationships, and the
  ~150-measure DAX library. Started in Week 1, built out through Week 3, and still
  empty on disk until you do the days that fill it in. Only `data_quality_findings.md`
  is pre-shipped there.
- `05_sql` — the DuckDB build and graded exercises are Day 36's deliverable, not
  something shipped in advance.
- `06_portfolio` — empty on disk, but not purely a Week 6 deliverable: design-
  rationale notes get written there starting Day 9, and again on Days 11, 22, 23,
  28, 29 and 35. The case drills, PL-300 gap analysis, STAR stories, case-study
  writeup, mock-interview log and capstone retrospective are Week 6's (Days 37–42).

In other words: the guide is complete, the guided work is not — that's by design.
