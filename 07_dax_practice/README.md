# 07_dax_practice - DAX Practice Trainer (v2)

A browser-only DAX course: 12 topics, 102 graded challenges, from `SUM` to long multi-step "big DAX" measures. You type a measure, a built-in mini DAX interpreter runs it on small random logistics data, and the result is compared with a reference measure on the grand total and on every row of a breakdown (by Mode, Region, customer, year, month ...). Common mistakes get a tagged warning (`/` instead of `DIVIDE`, unqualified columns, averaging ratios, the Air/`Ffe = 0` FFE trap, a hard-coded year, a repeated sub-expression).

It is independent of the seeded Meridian dataset in `02_data/`; nothing here reads or changes it.

## How to open it

Open `dax_trainer.html` in any modern browser (double-click, `file://` works). **The JS files must sit next to it in the same layout as in this folder**: `data.js`, `engine.js`, `checks.js`, `selftest.js` and the `topics/` folder. There is no build step, server or library. Progress and drafts are kept in the browser's `localStorage` (key `dax_trainer_v2`).

Files: `dax_trainer.html` (shell, CSS, UI), `data.js` (seeded data and the measure library), `engine.js` (tokenizer, parser, evaluator), `checks.js` (pattern warnings, grading), `selftest.js`, `topics/T01 ... T12` (the course), `AUTHORING.md` (how to add challenges).

## The data and the measure library

Each round generates seeded data (the seed is shown and editable, "New data" rolls a new one): `Shipment` (about 400 rows, 2024-01-01 to 2026-06-30, with `Weight`, `IsOnTime`, `DateKey` and `DeliveryDateKey`), `Customer` (15 rows), `Date` (2024-2026, marked as the date table, fiscal year starts 1 October) and `Target` (monthly revenue target per region, no relationship, for `TREATAS`). `Shipment[DateKey]` is the active relationship to `Date`; `Shipment[DeliveryDateKey]` is inactive (for `USERELATIONSHIP`). From Topic 2 on you may use the library measures `[Total Revenue]`, `[Total Cost]`, `[Profit]`, `[Shipments]`, `[Total FFE]`, `[On-Time %]`.

## The 12 topics (in learning order)

| # | Topic | Challenges |
|---|-------|-----------:|
| 1 | Aggregations | 8 |
| 2 | Measures & DIVIDE | 8 |
| 3 | Iterators | 9 |
| 4 | CALCULATE basics | 9 |
| 5 | Removing filters (ALL, ALLEXCEPT, ALLSELECTED, % of total/parent) | 9 |
| 6 | FILTER & table functions | 9 |
| 7 | Context transition | 8 |
| 8 | Logic & scope (SWITCH, SELECTEDVALUE, ISINSCOPE, COALESCE) | 9 |
| 9 | Variables | 7 |
| 10 | Time intelligence (YTD, fiscal YTD, SPLY, YoY, rolling, USERELATIONSHIP) | 10 |
| 11 | Ranking & Top N (RANKX, TOPN, CONCATENATEX) | 8 |
| 12 | Capstone: big DAX (YoY %, Pareto, ABC, budget vs actual, new customers, moving average, on-time points, price bridge) | 8 |
| | **Total** | **102** |

Each topic opens with a short concept card; its challenges run Beginner to Pro (the level chips filter them). "Next unsolved" walks the course in order, and Practice mode serves a random challenge from the topics you have started, on fresh data.

## Supported DAX subset

Aggregation: `SUM AVERAGE MIN MAX COUNT COUNTA COUNTBLANK DISTINCTCOUNT COUNTROWS ISEMPTY`. Iterators: `SUMX AVERAGEX MAXX MINX COUNTX CONCATENATEX`. Filters: `CALCULATE CALCULATETABLE FILTER ALL ALLEXCEPT ALLSELECTED REMOVEFILTERS KEEPFILTERS VALUES DISTINCT USERELATIONSHIP TREATAS RELATED RELATEDTABLE`, `IN {...}`. Tables: `ADDCOLUMNS SUMMARIZE TOPN RANKX`. Logic: `IF SWITCH COALESCE AND OR NOT` (both `NOT(x)` and prefix `NOT x`) `ISBLANK HASONEVALUE SELECTEDVALUE ISINSCOPE ISFILTERED BLANK TRUE FALSE`. Math: `DIVIDE ABS ROUND INT MOD`. Dates: `DATE YEAR MONTH DAY QUARTER EOMONTH FIRSTDATE LASTDATE DATESYTD DATESQTD DATESMTD TOTALYTD TOTALQTD TOTALMTD DATEADD SAMEPERIODLASTYEAR PARALLELPERIOD DATESBETWEEN DATESINPERIOD PREVIOUSMONTH NEXTMONTH PREVIOUSQUARTER PREVIOUSYEAR`. Plus `VAR`/`RETURN`, `&`, arithmetic, comparisons and omitted arguments.

## Known limits

- A True/False filter in `CALCULATE` uses one column; the other side can be a constant, a scalar `VAR` or a scalar expression without column or measure references. Aggregations and measure references there are rejected, as in real DAX (use a `VAR` or `FILTER`).
- Tables used as filters must have one column (or be a whole table); multi-column virtual tables and multi-column `TREATAS` are rejected.
- No `GENERATESERIES`, `CROSSFILTER`, `IFERROR`, `UNION`, `LOOKUPVALUE`, `FORMAT`, `SELECTCOLUMNS` or user-defined functions. `SUMMARIZE` groups `Shipment` by `Customer`/`Date` columns only.
- Time intelligence reads the visible `Date[Date]` and needs a contiguous selection; results are clipped to the date table (2024-2026); edge cases beyond month ends, fiscal year ends and 29 February may differ from Power BI. A filter on `Date[Date]` removes the other Date filters (marked date table).
- `ALLSELECTED` and `ISINSCOPE` use a simplified model of the visual: the report slicer plus the row's grouping columns.
- `COUNT`, `COUNTROWS`, `DISTINCTCOUNT` over no rows return BLANK, as in DAX. When grading, BLANK and 0 are treated as equal; text results must match exactly (case, spaces, punctuation) and a mismatch is flagged in the result table, while text comparisons inside a formula are case-insensitive.
- Date versus whole-number comparisons (an int `DateKey` against a `Date` value) raise an error, as in DAX.

## Self-test

Open `dax_trainer.html?selftest&seed=N` and read the browser console (`SELFTEST PASS n/n`). `&topic=T05` checks one topic only (add `&engine=1` to include the engine unit tests). Every challenge has an independent plain-JS oracle; the test checks that the reference and every alternative equal the oracle on every graded row, every wrong answer differs on at least one row, and the expected warnings fire. See `AUTHORING.md`.
