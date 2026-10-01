# Authoring challenges (DAX trainer v2)

Each topic is one file `topics/Txx_name.js` that calls `registerTopic({id, title, order, concept, challenges:[...]})`. Add challenges only to the `challenges` array of the topic you own; do not edit `engine.js`, `data.js`, `checks.js`, `selftest.js` or the HTML (report engine gaps instead). Concept text is at most 150 words; indented lines (2+ spaces) render as code, `backticks` as inline code.

## Challenge object

```js
{id:'T05-03',            // must start with the topic id, unique
 level:'Intermediate',   // Beginner | Intermediate | Pro (order the topic easy to hard)
 title:'...',
 by:['Customer[Segment]','Customer[CustomerName]'],  // 1 or 2 breakdown columns (Shipment/Customer/Date columns only)
 slicer:[{col:'Shipment[Mode]',vals:['Ocean','Air']}], // optional report slicer (or P=>[...])
 noTotal:true,           // optional: do not grade the grand-total row
 checks:['slash','unqual'],   // pattern rules to run (see below)
 prompt:'text' | P=>'text',   // P = seed-dependent parameters
 hint:'...', why:'...',
 ref:'DAX' | P=>'DAX',        // reference measure, must be real Power BI DAX
 alts:[{code:'DAX', warn:'slash'}] | P=>[...],   // other correct answers; warn = rule that must fire
 wrongs:[{code:'DAX', warn:'avgRatio'}] | P=>[...], // plausible wrong answers (>= 2)
 tolerance:1e-6,         // optional relative tolerance
 v1:'b1',                // only for challenges ported from v1 (progress migration)
 oracle:(D,ctx)=>value } // REQUIRED, see below
```

Rules: `ref` and every alt must be valid real DAX (no engine-only shortcuts, time intelligence takes `Date[Date]`; `NOT` works both as `NOT(x)` and as a prefix operator `NOT ISBLANK(x)`, with lower precedence than comparisons). Every wrong must differ from the oracle on at least one graded row. Library measures (`[Total Revenue]`, `[Total Cost]`, `[Profit]`, `[Shipments]`, `[Total FFE]`, `[On-Time %]`) may be used from Topic 2 on; a measure ref inside an iterator is evaluated with an implicit CALCULATE. BLANK and 0 compare equal when grading. Keep grids at or below 60 result rows (one level by Date[YearMonth] is 31).

Pattern rules (`checks`, `warn`): `slash`, `unqual`, `filterInCalc`, `avgRatio`, `ffeScope`, `allTable`, `sumxRedundant`, `hardcodedPeriod`, `varRepeat`. A ref must not trigger a warn-kind rule (set `refWarns:['rule']` on the challenge to allow one).

## Graded rows and the oracle ctx

The learner's measure is tested on the grand total plus one row per value of `by[0]`, and for two levels a subtotal row and one leaf row per `by[1]` value (only values that have shipments under the slicer). The oracle receives `(D, ctx)`:

```js
ctx = {label, P,          // P = D.params
       level,             // 0 grand total, 1 first level, 2 leaf
       groupBy:['Date[Year]','Date[MonthNo]'],   // columns in scope on this row (ISINSCOPE true for these)
       sel:{'Date[Year]':2025},                  // value of each in-scope column on this row
       slicers:{'Shipment[Mode]':['Ocean','Air']}}  // report slicer values per column
```

`D` has arrays `D.Shipment, D.Customer, D.Date, D.Target`. Extra hidden fields: Shipment `_c` (customer row), `_d` (order Date row), `_dd` (delivery Date row), `_n` / `_dn` (order / delivery epoch day); Date rows have `_n` (epoch day); `Date[Date]` is an interned `DateVal` (`.n` = epoch day). Oracles must be plain JS and must not call the engine.

Helpers in `data.js` (`H`): `H.vis(D,ctx,opts)` shipments visible on the row (opts: `drop:['Shipment[Mode]','Date',...]` removes a column or a whole table's filters, `add:{'Customer[Segment]':['Key']}`, `from`/`to` epoch days, `dateField:'DeliveryDateKey'`); `H.filters(ctx)`; `H.dates(D,ctx,opts)` and `H.dateRange(D,ctx,opts)` (`{min,max}` epoch days of visible dates); `H.inRange(D,ctx,from,to,f,dateField)` (sum ignoring the row's Date filters); `H.sum`, `H.sumOrNull`, `H.div` (BLANK-safe); `H.byCustomer(rows,f)` (sorted `[{key,val}]`); `H.colVal(shipment,'Customer[Segment]')`; date maths `H.epochDay(y,m,d)`, `H.ymd(n)`, `H.shiftMonths(n,k)` (clamps), `H.som/eom/sq/eq(n)` (start/end of month/quarter), `H.yearStart(n,'09-30')`, `H.dateKey(n)`, `H.nOfKey(k)`. Return `null` for BLANK. Time-intelligence oracles: see `topics/T10_time_intelligence.js`.

## Seed-dependent numbers

`deriveParams(D)` in `data.js` returns `D.params` (`P`) and rejects degenerate seeds: `n` (a customer shipment-count threshold, someone has exactly n), `T` (profit threshold with ties), `tieN` (a count shared by two customers), `topN` (3; customer revenue has no tie at rank 3/4 overall and per year), `year` 2025, `prevYear` 2024, `ym` '2025-06', `ymPrev`, `ymLY`. Use them as `prompt:P=>...`, `ref:P=>...`, `oracle:(D,ctx)=>... ctx.P.n`. Need another parameter? Report it; do not edit `data.js`.

## Data

Shipment ~400 rows, 2024-01-01 to 2026-06-30 (`ShipmentID, CustomerKey, Mode, Region, Revenue, Cost, Ffe, Weight, IsOnTime, DateKey, DeliveryDateKey`); Customer 15 rows (`CustomerKey, CustomerName, Segment, Country, AccountManager`); Date 2024-2026 (`DateKey, Date, Year, MonthNo, MonthName, YearMonth, Quarter, FiscalYear, DayOfWeek`, FY starts 1 Oct); Target (`YearMonth, Region, TargetRevenue`, no relationship, use TREATAS). Relationships: Shipment[CustomerKey] -> Customer, Shipment[DateKey] -> Date (active), Shipment[DeliveryDateKey] -> Date (inactive, USERELATIONSHIP). Air shipments have Ffe = 0.

## Running the selftest

Open `dax_trainer.html?selftest&seed=N&topic=T05` (console prints `PASS`/`FAIL`, final `SELFTEST PASS n/n`; `window.__selftest.ok`). With `topic=` only that topic is checked (add `&engine=1` for the engine unit tests too); without it everything runs. It verifies per seed: registry validation (ids, required fields, rules, concept length), ref == oracle and each alt == oracle on every row, each wrong differs on at least one row, the ref triggers no warning rule, and expected `warn` rules fire. Playwright: `chromium.launch({executablePath:'/opt/pw-browsers/chromium', args:['--no-sandbox']})`, then read `window.__selftest`. Run at least 10 seeds (for example 1-10).

## Supported DAX

Aggregation: SUM AVERAGE MIN MAX (also 2-arg scalar MIN/MAX, dates) COUNT COUNTA COUNTBLANK DISTINCTCOUNT COUNTROWS ISEMPTY. Iterators: SUMX AVERAGEX MAXX MINX COUNTX CONCATENATEX(table, expr, delim, orderExpr, ASC|DESC). Filter: CALCULATE CALCULATETABLE FILTER ALL (table, 1 or more columns of one table) ALLEXCEPT ALLSELECTED REMOVEFILTERS KEEPFILTERS VALUES DISTINCT USERELATIONSHIP TREATAS(one target column) RELATED RELATEDTABLE, `IN {..}` and `||`/`&&` in True/False filters. Tables: ADDCOLUMNS SUMMARIZE (group-by columns only) TOPN RANKX(table, expr, [value], [ASC|DESC], [SKIP|DENSE]). Logic: IF SWITCH (value form and SWITCH(TRUE(),...)) COALESCE AND OR NOT ISBLANK HASONEVALUE SELECTEDVALUE ISINSCOPE ISFILTERED BLANK TRUE FALSE. Math: DIVIDE ABS ROUND INT MOD. Dates: DATE YEAR MONTH DAY QUARTER EOMONTH FIRSTDATE LASTDATE DATESYTD DATESQTD DATESMTD TOTALYTD TOTALQTD TOTALMTD DATEADD SAMEPERIODLASTYEAR PARALLELPERIOD DATESBETWEEN DATESINPERIOD PREVIOUSMONTH NEXTMONTH PREVIOUSQUARTER PREVIOUSYEAR. Plus VAR/RETURN, `&`, arithmetic, comparisons, date +/- days, date - date, omitted arguments (`RANKX(t, e, , DESC)`).

## Known limits and deviations from real DAX

- A True/False filter in CALCULATE may use one column of the filtered table. The other side may be a constant, a scalar VAR, or a scalar expression with no column or measure references (`VAR T = 5000 RETURN CALCULATE([Total Revenue], Shipment[Revenue] > T)`); aggregations of columns and measure refs are rejected, like real DAX (store them in a VAR, or use FILTER). A table used as a filter must have one column or be a whole table (multi-column virtual tables and multi-column TREATAS are rejected; use one per column).
- A filter on `Date[Date]` removes the other filters on the Date table (marked date table); the removal also applies to the Date filters of the outer context only, not to other filter arguments in the same CALCULATE.
- Time intelligence reads the visible `Date[Date]`; DATEADD/SAMEPERIODLASTYEAR need a contiguous selection; a whole-month selection shifts to the whole shifted month (Feb 2025 -> all of Feb 2024). A single 29 Feb shifts to 28 Feb. DATESINPERIOD from a month-end uses month-end arithmetic (31 Mar, -3 MONTH = 1 Jan..31 Mar). Results are clipped to the date table (2024-2026). PREVIOUSMONTH/QUARTER/YEAR use the first visible date; NEXTMONTH the last. Real DAX edge cases beyond these may differ.
- PREVIOUSMONTH and DATEADD differ on the grand total (first date vs whole range), so such challenges set `noTotal:true`.
- RANKX: BLANK current value returns BLANK; blank row values are ignored; a bare SUM(...) as the expression does not transition (all rows tie), as in DAX. TOPN keeps ties; blank sorts lowest.
- ISINSCOPE is true for the `groupBy` columns of the row and is cleared when ALL/REMOVEFILTERS/ALLSELECTED on that column or its table is applied in a CALCULATE (approximation of real scope handling).
- ALLSELECTED restores the outer slicer filters of the named columns/table (the shadow filter context); other row filters of the visual stay.
- SUMMARIZE can group Shipment by Customer or Date columns, not Customer by Shipment columns. No GENERATESERIES, CROSSFILTER, IFERROR, UNION, LOOKUPVALUE, FORMAT, SELECTCOLUMNS or user-defined functions. Date vs int comparisons raise the DateKey error; Date vs text is rejected.
- COUNT, COUNTA, COUNTX, COUNTROWS and DISTINCTCOUNT over no rows return BLANK (not 0), like SUM; BLANK = 0 is still TRUE and grading treats them as equal. Text comparison inside formulas is case-insensitive, but a text result is graded exactly (case, spaces, punctuation) and a mismatch is reported in the result table.
- BLANK + number counts BLANK as 0; `/` by zero is Infinity (DIVIDE is blank), as in DAX.
