# Day 36: SQL over the same dataset, DuckDB, and where DAX concepts actually transfer

> Time: 3.5 h · Spaced recall 10 min · Concept 50 min · Drill 95 min · Ship 30 min · Log 15 min

Six weeks of DAX and you have never once written a `JOIN`. Today closes that gap
with the tool most analytics teams actually put next to Power BI: DuckDB, an
in-process SQL engine that reads Parquet directly, no server, no load step. The
point of today is not "learn a second language": it is to re-derive four numbers
you already trust from DAX, in SQL, and see exactly which parts of what you learned
in Weeks 2–3 are DAX-specific machinery and which are the actual underlying idea
wearing different syntax.

---

## Spaced recall (10 min, closed book)

1. State the pooled-vs-naive averaging rule from Day 9: which one weights each row
   by its denominator, and which quantity predicts how far apart they land?
2. What makes `FactTarget` require `TREATAS` instead of a physical relationship to
   `DimLocation` (Day 13), and which column is the real bridge?
3. What is the rolling window this industry reports schedule reliability on
   (Day 11), and why that length?
4. Why is `IsOnTime`, `IsPerfectOrder`, and every other `Is*` column stored as
   `int8` rather than a proper boolean (README §7)?
5. Name the day-13 KPI code and the two grains (`FactTarget`'s and the
   transactional facts') that do not physically join.

---

## Concept

### What actually differs between DAX and SQL

DAX's whole difficulty is that a measure's meaning depends on a **context** that is
assembled invisibly, from wherever the measure gets placed: a matrix row, a slicer,
a `CALCULATE` filter, row context inside an iterator. Six weeks of this course have
mostly been about learning to see that invisible context and control it.

SQL has no equivalent mechanism. A query's result depends on exactly what is
written in its `FROM`, `JOIN`, `WHERE`, and `GROUP BY` clauses: nothing more,
nothing implicit. This is not a limitation: it is a different trade, and SQL trades
DAX's terseness (`[Revenue]` means something different in every visual) for
explicitness (a query means exactly and only what it says, every time it runs).

That trade is why some of what you spent two weeks learning turns out to be
DAX-specific plumbing, and some of it is a real statistical or modelling idea that
was never about DAX at all. Today separates the two:

| DAX mechanism | What it's really doing | SQL equivalent |
|---|---|---|
| Row context inside `AVERAGEX`/`SUMX` | evaluate an expression once per row, then aggregate | a derived per-row expression in the `SELECT`, aggregated with `AVG`/`SUM` |
| `CALCULATE` filter replacement | swap out the ambient filter on a column | a differently-scoped subquery or a fresh `WHERE` (SQL has no ambient filter to replace) |
| `ALLSELECTED`/`ALL` | choose how much of the ambient filter survives | doesn't exist: every SQL query's scope is exactly what you wrote, so there is nothing to "restore" |
| `TREATAS` (virtual relationship) | apply one table's current values as a filter on an unrelated column | an ordinary `JOIN ... ON a.col = b.col` (SQL has no concept of "no physical relationship exists," you just join on the bridge column) |
| Calculation group `SELECTEDMEASURE()` | reshape whichever measure the visual carries, without rewriting it | nothing analogous: you'd write the MTD/YTD/PY logic once per query, because SQL queries aren't reused across visuals the way a DAX measure is |

Two rows of that table are the real lesson. `TREATAS` and calculation groups look
like deep DAX concepts, but they exist to solve problems specific to a model that
has to serve *any* visual with *any* filter selection through one reusable measure.
SQL never has that problem: a query is written for one question, so "no physical
relationship exists" simply means "join on whatever column actually matches," full
stop. The pooled-vs-naive averaging trap, on the other hand, is not a DAX quirk at
all. It is arithmetic, and it will bite you in `pandas`, in SQL, in Excel, in any
tool with a `GROUP BY`. Today proves that by reproducing it in a language that has
no `AVERAGEX`.

### Querying Parquet directly, no load step

DuckDB reads the same files Power BI's Parquet connector reads: the ones laid out
per `SCHEMA_CONTRACT.md` §0: facts are Hive-partitioned under
`02_data/raw/<Table>/year=YYYY/month=MM/part-*.parquet`, dimensions are one flat
`02_data/raw/<Table>/part-000.parquet`. Point `read_parquet` at a glob and it treats
the whole tree as one table, including the partition columns:

```sql
SELECT COUNT(*) AS n
FROM read_parquet('02_data/raw/FactShipment/year=*/month=*/part-*.parquet');
```

For repeated use, wrap that in a view so the rest of the day's SQL reads like
ordinary table names: this is also the shape your `.sql` files should ship in:

```sql
CREATE VIEW FactShipment AS
    SELECT * FROM read_parquet(
        '02_data/raw/FactShipment/year=*/month=*/part-*.parquet',
        hive_partitioning = true
    );

CREATE VIEW DimDate AS
    SELECT * FROM read_parquet('02_data/raw/DimDate/part-000.parquet');

CREATE VIEW DimVoyage AS
    SELECT * FROM read_parquet('02_data/raw/DimVoyage/part-000.parquet');

CREATE VIEW FactPortCall AS
    SELECT * FROM read_parquet(
        '02_data/raw/FactPortCall/year=*/month=*/part-*.parquet',
        hive_partitioning = true
    );

CREATE VIEW DimLocation AS
    SELECT * FROM read_parquet('02_data/raw/DimLocation/part-000.parquet');

CREATE VIEW FactTarget AS
    SELECT * FROM read_parquet(
        '02_data/raw/FactTarget/year=*/month=*/part-*.parquet',
        hive_partitioning = true
    );

CREATE VIEW DimScenario AS
    SELECT * FROM read_parquet('02_data/raw/DimScenario/part-000.parquet');
```

`hive_partitioning = true` recovers `year`/`month` as real columns from the folder
names. You will not usually need them, since every date-bearing fact also carries
its own `*DateKey` column, but it is worth knowing the partition columns exist and
are queryable directly for a cheap pre-filter (`WHERE year = 2025`) before DuckDB
even opens the row groups inside the matching files.

### Re-deriving revenue per FFE: the averaging trap, in SQL

Day 9 built pooled and naive versions of revenue per FFE in DAX and found the gap
was nearly zero because the ratio barely correlates with its own denominator. Same
computation, no DAX:

```sql
-- POOLED, weights each shipment's booking by its FFE (matches DAX's pooled version)
SELECT
    v.Direction,
    SUM(s.Revenue_usd) / SUM(s.Ffe) AS revenue_per_ffe_pooled
FROM FactShipment s
JOIN DimVoyage v ON s.VoyageKey = v.VoyageKey
WHERE s.VoyageKey <> -1
GROUP BY v.Direction;

-- NAIVE, unweighted mean of each shipment's own ratio (matches DAX's AVERAGEX)
SELECT
    v.Direction,
    AVG(s.Revenue_usd / NULLIF(s.Ffe, 0)) AS revenue_per_ffe_naive
FROM FactShipment s
JOIN DimVoyage v ON s.VoyageKey = v.VoyageKey
WHERE s.VoyageKey <> -1
GROUP BY v.Direction;
```

Notice what changed and what didn't. `AVERAGEX(FactShipment, DIVIDE(...))` became
`AVG(a / NULLIF(b, 0))`: SQL's `NULLIF` is doing `DIVIDE`'s job of turning a
zero-denominator row into a `NULL` that `AVG` silently skips, the same way `DIVIDE`
returns `BLANK()` and `AVERAGEX` skips blanks. The *shape* of the two queries
("weight by summing the parts first" versus "average the pre-divided ratio") is
identical to the DAX pair. That is the point: the trap lives in the arithmetic, not
in the language.

### Re-deriving OTIF and perfect order rate: averaging a 0/1 column

This is the easiest re-derivation of the day, and worth noticing *why* it's easy:

```sql
SELECT
    AVG(IsOnTime)      AS on_time_rate,       -- README §6's delivery on-time rate, 0.9130 (not OTIF -- OTIF is ~0.867, WHS.QLT.OTIF)
    AVG(IsPerfectOrder) AS perfect_order_rate  -- README §6, 0.8574
FROM FactShipment;
```

`AVG` of an `int8` column that only ever holds 0 or 1 *is* the rate: no `DIVIDE`,
no `CASE WHEN`, nothing DAX-specific about it at all. This is exactly why
`SCHEMA_CONTRACT.md` mandates `int8`/`is_` for every boolean in this model rather
than a text flag or a proper boolean type: it is what lets both DAX and SQL turn a
population of yes/no facts into a rate with one aggregation function, in either
language, for free.

### Re-deriving the rolling 8-week schedule reliability: window functions

Day 11's `Schedule Reliability Rolling 8wk` filtered `FactPortCall` to a 56-day
window ending on the selected date and divided on-time calls by total calls. SQL's
tool for "a value computed from a moving window of rows" is the same idea DAX's
`DATESBETWEEN` was standing in for: a **window function**:

```sql
WITH daily AS (
    SELECT
        d.Date AS call_date,
        SUM(CASE WHEN pc.IsOnTimeArrival = 1 THEN 1 ELSE 0 END) AS on_time_calls,
        COUNT(*) AS total_calls
    FROM FactPortCall pc
    JOIN DimDate d ON pc.AtaDateKey = d.DateKey
    WHERE pc.CallStatus = 'Completed'
    GROUP BY d.Date
),
rolling AS (
    SELECT
        call_date,
        SUM(on_time_calls) OVER w AS on_time_56d,
        SUM(total_calls)   OVER w AS calls_56d
    FROM daily
    WINDOW w AS (
        ORDER BY call_date
        RANGE BETWEEN INTERVAL '55 days' PRECEDING AND CURRENT ROW
    )
)
SELECT call_date, on_time_56d, calls_56d,
       on_time_56d::DOUBLE / calls_56d AS reliability_rolling_8wk
FROM rolling
WHERE call_date = DATE '2025-08-31';
```

**`RANGE`, not `ROWS`, and this is the sharp edge of the day.** `ROWS BETWEEN 55
PRECEDING AND CURRENT ROW` counts 56 *rows in the result set*, which, once you've
aggregated to one row per calendar date with at least one port call, means 56
*dates that had activity*, not 56 *calendar days*. `RANGE BETWEEN INTERVAL '55
days' PRECEDING` counts actual elapsed time, correctly spanning gap days with zero
port calls. Network-wide the two rarely disagree, because some port has a call on
almost every day. Narrow the window to a single, quieter port and they diverge.
Exercise 36.4 makes you find it.

This is a direct SQL analogue of the `DATESBETWEEN` vs `DATESINPERIOD` distinction
from Day 11, and of `ALL` vs `ALLSELECTED` from Day 9: two tools that look
interchangeable and are not, and the difference only shows up once the data has a
gap or an edge case to expose it.

### Re-deriving the TREATAS join: budget vs actual, no virtual relationship needed

Day 13 built `Actual Schedule Reliability (via TREATAS)` because `FactTarget` and
the transactional facts share no physical relationship: `FactTarget[Region]` is
plain text with no FK, and the model has to serve arbitrary future visuals so it
needs a *reusable* virtual join. SQL has no such constraint: you are writing one
query for one question, so "no physical relationship" just means "join on whichever
column actually matches." The bridge is still `DimLocation[TradeRegion]`, exactly
as Day 13 made you verify with `DISTINCT`, but there is no special function for it:

```sql
SELECT
    ft.KpiCode,
    ft.Region,
    ds.ScenarioCode,
    ft.TargetValue
FROM FactTarget ft
JOIN DimScenario ds ON ft.ScenarioKey = ds.ScenarioKey
WHERE ft.KpiCode = 'OCN.REL.SCHED'
  AND ft.Region = 'Americas'
  AND ds.ScenarioCode = 'ACT'
  AND ft.TargetMonthDateKey = 20250601;
```

(`FactTarget` itself carries `ScenarioKey`, not `ScenarioCode` -- the code lives
on `DimScenario`, per `SCHEMA_CONTRACT.md` §1.19/§2.11, so the scenario filter
needs this join; `KpiCode`, `Region` and `TargetMonthDateKey` are already columns
on `FactTarget` directly and need no join at all.)

versus the recomputed figure, joined the ordinary way through `DimLocation`:

```sql
SELECT
    l.TradeRegion,
    SUM(CASE WHEN pc.IsOnTimeArrival = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS reliability
FROM FactPortCall pc
JOIN DimLocation l ON pc.LocationKey = l.LocationKey
JOIN DimDate d ON pc.AtaDateKey = d.DateKey
WHERE l.TradeRegion = 'Americas'
  AND d.Year = 2025 AND d.Month = 6
  AND pc.CallStatus = 'Completed'
GROUP BY l.TradeRegion;
```

Both queries are ordinary joins. Nothing in either one needed a name like
`TREATAS`: that name only exists because DAX needed a word for "join two things
that have no relationship object in the model," and SQL was never missing that
capability in the first place.

---

## Drill

Predict first, every time: write the prediction down before you run anything.

### Exercise 36.1, set up DuckDB, count the tables (15 min)
Install DuckDB (`pip install duckdb`, or the CLI) and create the views for
`FactShipment`, `FactPortCall`, `FactTarget`, `DimDate`, `DimVoyage`, `DimLocation`,
`DimScenario` as shown above. Before running `COUNT(*)` on each, predict which of
the **three fact tables** (`FactShipment`, `FactPortCall`, `FactTarget` — the rest
in the list are dimensions) will have the most rows and which the fewest, ranking
all three from memory of README §1's row-count table. Then verify. Note which
ranking you got wrong, if any.

### Exercise 36.2, the averaging trap, in SQL (20 min)
Build both revenue-per-FFE queries. Predict, before running: will the SQL pooled
figure match Day 9/Week 2's DAX figure for headhaul and backhaul (2,482.78 /
1,286.66) exactly, approximately, or not at all, and why should it match if both
are computing the same aggregation over the same rows? Then predict the naive
query's gap versus pooled, using what you already know about revenue-per-FFE's
near-zero correlation with FFE count. Verify both.

### Exercise 36.3, OTIF and perfect order rate, in one query (10 min)
Run the two-column `AVG` query. Predict both values from memory (Day 9's spaced
recall and README §6) before running. Then add a third column,
`AVG(IsInFull)`, and predict whether it will be closer to the on-time rate or the
perfect-order rate, and why: think about what `IsPerfectOrder` requires that
`IsOnTime` alone doesn't.

### Exercise 36.4, the rolling window, and where `ROWS` lies to you (30 min)
Build the `RANGE`-based rolling 8-week query and read the value at 2025-08-31.
Predict, before running, whether it will land near Day 11's network-wide figure of
0.662. Then build the `ROWS BETWEEN 55 PRECEDING`-based version and compare the two
at the same date, network-wide. Predict whether they'll differ noticeably.

Now repeat both versions filtered to `LocationCode = 'NLRTM'` only (one of Day 11's
two crisis ports). Predict first whether `ROWS` and `RANGE` will diverge more here
than they did network-wide, and why a single port's call calendar is more likely to
have gap days than the whole network's. Write one sentence stating which framing
you would ship and why "no port calls happened yesterday" should not silently
shrink your reliability window.

### Exercise 36.5, the TREATAS-equivalent join (20 min)
Build both June-2025-Americas queries above. Predict, before running, whether the
SQL recomputed figure will land closer to `FactTarget`'s own stored `ACT` value, or
closer to the 66.22%-vs-74.71% gap this project's own debugging history found
(Day 39 tells that story in full; for today, just predict whether SQL changes
the answer at all versus the DAX version). It shouldn't: the same rows, joined on
the same bridge column, produce the same number regardless of which query language
asks for it. If your SQL figure disagrees with Day 13's DAX figure, that is a bug
in one of the two queries, not a property of SQL: find which one.

---

## Ship

Create `05_sql/queries/` and save today's five queries as separate `.sql` files,
each with a one-line comment at the top stating which Day-9/11/13 DAX measure it
re-derives and what the expected value is, so a future reader (including you) can
check a query without re-running the whole notebook. Add `05_sql/setup_views.sql`
holding the `CREATE VIEW` block from today so every later SQL day can `.read` it
instead of repeating it.

```
git add .
git commit -m "Day 36: DuckDB primer, revenue-per-FFE / OTIF / rolling reliability / TREATAS-join re-derived in SQL"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can query `02_data/raw` directly from DuckDB with no load/import step and
      explain why the Hive partition layout makes that possible.
- [ ] You can state, without notes, which Week 2 DAX mechanisms are DAX-specific
      plumbing (`TREATAS`, calculation groups) and which are language-independent
      arithmetic (the pooled-vs-naive averaging trap).
- [ ] Your SQL revenue-per-FFE, OTIF, and rolling-8-week figures match the DAX
      figures from Days 9, 11, and 13 you already trust.
- [ ] You reproduced the `ROWS`-vs-`RANGE` divergence on a real gap-prone port and
      can explain why it happens in one sentence.
- [ ] `05_sql/queries/` exists with today's five queries, each documenting what DAX
      measure it checks against.
- [ ] Predictions recorded, misses annotated.
