# Day 32 — solutions

---

## Spaced recall answers

1. `TREATAS`, mapping a table's current values onto a column with no physical
   relationship (Day 13's `FactTarget`/`DimLocation[TradeRegion]` bridge).
   Day 31 wrapped it as a **table-level role filter** on `FactTarget` itself
   (evaluating to a boolean per row via `COUNTROWS(CALCULATETABLE(...)) > 0`)
   rather than as a measure's `CALCULATE` argument — the mechanism is
   identical, only where it's attached changes.
2. Because RLS filters propagate through relationships exactly like any other
   filter — only through **active** ones. A fact table with more than one
   foreign key into the same dimension can have at most one active path
   (Power BI's single-active-relationship rule); a role reaches the dimension
   only along that path, so a measure built on the *inactive* one shows the
   full, unrestricted total instead of a scoped number.
3. Because no fact table in this schema has a dedicated "last modified"
   timestamp column, which is what the detect-data-changes accelerator needs
   to skip unchanged rows *within* a still-refreshing partition. The design
   relies on range partitioning alone — skipping whole historical partitions
   outright, which is still the majority of the win.
4. `year=1900/month=01`, in every table partitioned by a column that can hold
   the `-1` sentinel. A normal "refresh the last N months" window is anchored
   to real recent calendar dates and structurally cannot include a bucket
   pinned at year 1900.
5. A calculated column is computed once per row at refresh time and stored,
   adding directly to the table's cardinality and memory footprint; a measure
   is computed on demand in whatever filter context is active, and costs
   nothing at rest.

---

## Exercise 32.1 — the Auto Date/Time audit

**Reference count:** the model's last TMDL export carries **14**
`LocalDateTable_*` tables. Whether your live model still matches that number
is the real check — Auto Date/Time creates a new one automatically the
moment an *unmarked* date/datetime column is dragged into a visual for the
first time, so the count can silently grow past 14 without anyone deciding to
add a table.

**Sibling `*DateKey` mapping, checked against the schema directly** (7 of the
8 raw timestamp columns have one; the eighth needs a genuine calculated
column):

| Timestamp column | Sibling `*DateKey` on the same table |
|---|---|
| `FactWarehouseTask.TaskStartTs` | `TaskDateKey` |
| `FactWarehouseTask.TaskEndTs` | `TaskDateKey` (same key — one task, one date) |
| `FactContainerMove.EventTs` | `EventDateKey` |
| `FactPortCall.PromisedEtaTs` | `PromisedEtaDateKey` |
| `FactPortCall.AtaTs` | `AtaDateKey` |
| `FactPortCall.AtdTs` | `AtdDateKey` |
| `FactPortCall.BerthTs` | `BerthDateKey` |
| `FactPortCall.UnberthTs` | **none** — no `UnberthDateKey` exists in the schema |

Seven columns can be hidden and repointed at `DimDate` for free, through a
key that already exists and is already correctly typed. `UnberthTs` is the
one genuine exception: giving it a `DimDate` relationship needs a real
calculated column (`Date.From(UnberthTs)` in Power Query, or
`DATEVALUE(...)` as a calculated column) if a date-level relationship is
actually needed for it at all — worth asking first whether any measure
genuinely needs `Unberth` at daily grain, versus just needing the raw
timestamp for a duration calculation, in which case no date relationship is
needed and the column can simply be hidden.

---

## Exercise 32.2 — Performance Analyzer on a real page

This one is genuinely yours to run — the actual millisecond numbers depend on
your machine, your model's current relationship/index state, and which page
you picked, so there is no single "correct" number to check against. What
*is* checkable is the **method**, worked through on a realistic example:

Suppose the slowest visual on an executive-summary page is a matrix showing
`Revenue`, `Schedule Reliability Rolling 8wk`, and `Gross Margin` by
`TradeLane` × `Month`, and Performance Analyzer reports it at **480ms DAX
query** versus 40ms for every other visual on the page. Copying that query
into DAX query view with Server Timings on and finding **410ms Formula
Engine / 70ms Storage Engine** tells you the bottleneck is FE-heavy — the
DAX itself is doing expensive row-by-row work (plausibly the rolling 8-week
schedule-reliability measure's `DATESINPERIOD` window recalculating per
`TradeLane`×`Month` cell instead of being pre-aggregated), not a storage-scan
problem. The fix in that case is a DAX rewrite — a variable hoisting the
window calculation out of the innermost iteration, or a calculation-group
item reused instead of a bespoke rolling-window expression per cell — not a
relationship or cardinality change. The reverse split (SE-heavy, low cache
hit rate) would point you back toward Exercise 32.1 and 32.4 instead — a
cardinality or relationship-shape problem no amount of DAX rewriting fixes.

**What to actually record:** which visual was slowest, its FE/SE split, and
one sentence on which category of fix (DAX rewrite vs. model change) that
split points to. That record is the deliverable, not a specific millisecond
figure.

---

## Exercise 32.3 — decide `DimWarehouse ↔ DimLocation`

**The case for bidirectional:** a location-scoped filter (a region slicer, or
Day 31's `Region - Americas` role) should, in principle, also constrain
warehouse-level facts (`FactWarehouseTask`, `FactInventorySnapshot`) by the
warehouse's physical location — without it, a reader filtering to "Americas"
on a location slicer sees warehouse KPIs for every warehouse worldwide
sitting next to correctly-filtered shipment KPIs on the same page, which is a
real, visible inconsistency a stakeholder would notice immediately.

**The case against:** this model already carries 108 relationships, several
of them role-playing paths through `DimLocation` (Day 31's
Origin/Destination/Pol/Pod), and a bidirectional relationship on
`DimWarehouse ↔ DimLocation` opens a **second** filter path into every
warehouse-touching fact table for any query that also touches `DimLocation`
through one of those other paths — the exact shape of ambiguous, two-path
filter propagation Day 9's `ALL`/`ALLSELECTED` section warned drives
"plausible but not what you think" numbers, just one hop further from the
visual than that lesson's examples.

**Recommendation:** keep it **single-direction** (`DimLocation` filters
`DimWarehouse`, not the reverse), and cover the "warehouse KPIs should
respect the region slicer" requirement with an explicit relationship from
`DimWarehouse[LocationKey]` to `DimLocation` (already exists) filtering
`DimWarehouse` normally — which already achieves the one legitimate
one-directional need — rather than making the *whole* relationship
bidirectional to solve a problem the existing single-direction relationship
already solves. Bidirectional is the right call only if a specific report
need requires filtering *DimLocation itself* by something selected on the
`DimWarehouse` side (e.g. "show me only the locations that have a warehouse"),
which is a real but narrower requirement — and if that need is confirmed,
prefer a bidirectional relationship scoped to exactly that one visual via
`CROSSFILTER` in a measure (Day 9) over making the physical relationship
bidirectional model-wide.

---

## Exercise 32.4 — rank columns by cardinality

Measured directly against `02_data/raw` and `02_data/reference`:

| Column | Table rows | Distinct values | % unique |
|---|---|---|---|
| `DimCustomer[CustomerCode]` | 4,171 | **3,200** | 76.7% |
| `DimSku[SkuKey]` | 12,000 | **12,000** | 100% |
| `FactShipment[Revenue_usd]` | 491,400 | **488,207** | 99.35% |
| `FactBooking[BookingNo]` | 575,881 | **575,569** | 99.95% |
| `FactWarehouseTask[TaskStartTs]` | 740,136 | **639,602** | 86.4% |

(`BookingNo`'s gap of 312 between row count and distinct count is not noise -
it's exactly landmine #2, `DUPLICATE_BOOKING_REFS = 312`, Day 34's territory -
312 `BookingNo` values each appearing on more than one row.)

**Ranked ascending by absolute cardinality (the number that actually drives
VertiPaq dictionary size):** `CustomerCode` (3,200) < `SkuKey` (12,000) <
`Revenue_usd` (488,207) < `BookingNo` (575,569) < `TaskStartTs` (639,602).

The instructive surprise: `TaskStartTs` is **less** unique per row than
either `BookingNo` or `Revenue_usd` (86.4% vs. ~99%+), yet has the **largest**
absolute dictionary of the five, because `FactWarehouseTask` simply has more
rows to draw distinct values from. **Absolute cardinality, not
per-row uniqueness ratio, is what you rank by** — a column that's "only" 86%
unique on a 740K-row table can still cost more than a 99%-unique column on a
smaller one.

**Which to flag for hiding on cardinality grounds alone:** `TaskStartTs`.
`SkuKey` and `CustomerCode` are dimension surrogate keys, already the correct
kind of thing to hide as standard practice, not a cardinality call in
themselves. `BookingNo` is a real business key readers legitimately search
and trace by — high cardinality but earned. `Revenue_usd` is the raw column
behind the `Revenue` measure and gets hidden too, but on the general
"hide raw fact columns, expose only measures" convention, not specifically
because of its cardinality. `TaskStartTs` is the one column that is both
genuinely expensive *and* has a cheaper, already-existing substitute
(`TaskDateKey`) for everything a report actually needs from it — the
cleanest case of "hide it, and lose nothing."
