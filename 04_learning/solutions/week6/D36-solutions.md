# Day 36: solutions

All queries run against the `prod`-scale build via DuckDB. Figures cross-checked
against the DAX values already shipped in Weeks 2–3 and against README §6.

---

## Spaced recall answers

1. The pooled version weights each row by its own denominator (`SUM(num)/SUM(den)`);
   the naive version gives every row's ratio equal weight regardless of size
   (`AVERAGEX` of per-row `DIVIDE`). The gap between them scales with the
   correlation between the ratio and its own denominator.
2. `FactTarget[Region]` is a plain text column with no foreign key to
   `DimLocation`: it sits at Region×Month×Scenario grain, not Location×Date.
   `TREATAS` bridges it because DAX needs a *reusable* virtual join that survives
   any visual; the correct bridge column is `DimLocation[TradeRegion]`, not the
   finer-grained `DimLocation[Region]`.
3. A trailing 8-week (56-day) window, because a vessel schedule runs on a weekly
   cycle and eight cycles is enough to average out weekly noise without smoothing
   away a real shift.
4. `int8` with values 0/1 means `AVG()` of the column *is* the rate directly, in
   both DAX and SQL, with no `CASE`/`DIVIDE` translation step.
5. `KpiCode = 'OCN.REL.SCHED'`; `FactTarget` sits at Region/Month/Scenario grain,
   the transactional facts (`FactPortCall`) sit at Location/Date grain: no shared
   key at a shared level of detail.

---

## Exercise 36.1, row counts

```sql
SELECT COUNT(*) FROM FactShipment;   -- 491,765
SELECT COUNT(*) FROM FactPortCall;   -- 131,097
SELECT COUNT(*) FROM FactTarget;     -- 51,900
SELECT COUNT(*) FROM DimVoyage;      -- 9,270
SELECT COUNT(*) FROM DimLocation;    -- 420
```

Ranking (largest to smallest, of the four facts queried): `FactShipment` >
`FactPortCall` > `FactTarget`. If your prediction ranked `FactPortCall` above
`FactShipment`, the likely reason is intuitive but wrong: one shipment usually
touches several port calls indirectly through its voyage, so it *feels* like port
calls should outnumber shipments. But a port call is one vessel-at-one-terminal
event shared across many shipments' voyages, while a shipment is a whole house
bill of lading. Sharing, not multiplying, is what keeps `FactPortCall` smaller.

---

## Exercise 36.2, revenue per FFE

| Direction | Pooled (SQL) | Naive (SQL) | Pooled (DAX, Week 2) |
|---|---|---|---|
| Headhaul | **2,482.78** | ≈2,489 (+0.2%) | 2,482.78 |
| Backhaul | **1,286.66** | ≈1,289 (+0.2%) | 1,286.66 |

The SQL pooled figures match the DAX figures **exactly**, because both are
computing `SUM(Revenue_usd) / SUM(Ffe)` over the identical set of rows: the
aggregation itself carries no language-specific behaviour, only the syntax that
requests it differs. This is the whole point of the exercise: a DAX measure and a
SQL query are two different ways of asking a database engine to do the same sum.

The naive gap is small in both languages, for the same reason Day 9 found: revenue
per FFE barely correlates with FFE count on a booking (`corr ≈ 0`), so weighting by
FFE barely changes the answer. Confirm you did **not** see a large gap here: a
large gap would mean you'd built the wrong pair of queries, most likely joining on
the wrong key or mixing headhaul and backhaul together before grouping.

---

## Exercise 36.3, OTIF and perfect order rate

```sql
SELECT AVG(IsOnTime) AS on_time_rate,        -- 0.9130
       AVG(IsPerfectOrder) AS perfect_rate,  -- 0.8574
       AVG(IsInFull) AS in_full_rate         -- ≈0.987
FROM FactShipment;
```

`IsInFull` lands close to the **perfect-order** rate (0.8574), not the on-time
rate (0.9130), because `IsPerfectOrder` is a conjunction of four conditions
(`IsOnTime AND IsInFull AND NOT IsDamaged AND IsDocumentationClean`) each of which
independently knocks a few shipments out. `IsInFull` alone (~98.7%) is the highest
of the four component rates, so it is the *least* limiting factor: on-time
(91.3%) is the one doing most of the work dragging the composite down to 85.7%.
This is the SQL-side confirmation of exactly the OTIF-decomposition idea the KPI
dictionary uses for warehouse OTIF (DIF × DOQ × DOT): a composite rate is bounded
above by its weakest component, never its strongest.

---

## Exercise 36.4, rolling 8-week window, `RANGE` vs `ROWS`

Network-wide at 2025-08-31:

| Framing | Reliability |
|---|---|
| `RANGE BETWEEN INTERVAL '55 days'` | **0.662** |
| `ROWS BETWEEN 55 PRECEDING` | **0.662** (identical to 3 d.p.) |

Network-wide the two agree, because with 96 active locations and ~131,000 port
calls network-wide, essentially every calendar day has at least one completed call
somewhere: there are no gap days in the aggregated `daily` CTE, so `ROWS BETWEEN
55 PRECEDING` and `RANGE BETWEEN INTERVAL '55 days'` cover the same 56 rows either
way. This matches Day 11's own rolling-8-week figure exactly, which is the whole
point: same rows, same arithmetic, different query language.

Filtered to `NLRTM` only:

| Framing | Reliability |
|---|---|
| `RANGE BETWEEN INTERVAL '55 days'` | **0.412** |
| `ROWS BETWEEN 55 PRECEDING` | **0.398** |

Now they diverge. A single gateway port does not have a completed call every
single day; some days have zero. `ROWS BETWEEN 55 PRECEDING` silently walks back
56 *rows with activity*, which on a sparse calendar spans more than 56 actual
calendar days, pulling in calls from further back in time than the "trailing
8 weeks" label promises, and diluting the crisis-window figure toward the
better-performing weeks just outside it. `RANGE BETWEEN INTERVAL '55 days'` is the
one that actually means "the last 56 calendar days," which is what "trailing
8-week window" is supposed to mean, and it is the only framing to ship.

**The one-sentence answer:** `ROWS` counts observations, `RANGE` counts time, and
any rolling window computed on a series with possible gaps must use `RANGE` (or an
explicit calendar join) or it will quietly widen itself on exactly the sparse,
troubled members of the population you most need it to be precise about: the SQL
mirror of Day 9's `ALL`-vs-`ALLSELECTED` and Day 11's `DATESBETWEEN`-vs-naive-
weekly-average lessons.

---

## Exercise 36.5, the TREATAS-equivalent join

| Source | Value |
|---|---|
| `FactTarget` stored `ACT`, Americas, June 2025 | **74.71%** (unweighted mean across lanes, per Day 13) |
| Recomputed via `DimLocation[TradeRegion]` join | **66.22%** |

The SQL figure matches the DAX `TREATAS`-based figure from Day 13 **exactly**:
66.22% either way, because both queries are joining `FactPortCall` to
`DimLocation` on the same `TradeRegion` bridge and computing the same pooled ratio
over the same rows. If your SQL number came out different from your Day 13 DAX
number, check these two things first: (1) did you filter `CallStatus = 'Completed'`
in both, and (2) did you join on `TradeRegion` and not the finer-grained `Region`
column, the same trap Day 13 flagged, now reappearing with zero DAX-specific
machinery to blame it on.

The 8.5-point gap between the recomputed figure and `FactTarget`'s own stored
"Actual" is real and is not a query bug. Day 39 turns it into a full worked STAR
story. The short version: `FactTarget`'s `ACT` scenario is itself an **unweighted
mean across lanes**, so it carries the same naive-averaging error Day 9 taught you
to distrust, just recorded once as a static planning figure instead of computed
live. Two independent things went wrong at once: the wrong grain of column
almost got joined, and the number being compared against was itself built with the
naive-average trap, which is exactly the kind of compounding failure a single
query, however carefully written, cannot protect you from on its own.

---

## Reference values used above

| Quantity | Value |
|---|---|
| FactShipment rows | 491,765 |
| FactPortCall rows | 131,097 |
| FactTarget rows | 51,900 |
| Revenue per FFE, headhaul (pooled) | 2,482.78 |
| Revenue per FFE, backhaul (pooled) | 1,286.66 |
| On-time rate (`IsOnTime`) | 0.9130 |
| Perfect order rate | 0.8574 |
| Schedule reliability, rolling 8wk, network, 2025-08-31 | 0.662 |
| Schedule reliability, rolling 8wk, NLRTM only (RANGE) | 0.412 |
| Schedule reliability, rolling 8wk, NLRTM only (ROWS, wrong) | 0.398 |
| TREATAS/JOIN recomputed, Americas, June 2025 | 66.22% |
| FactTarget stored ACT, Americas, June 2025 | 74.71% |
