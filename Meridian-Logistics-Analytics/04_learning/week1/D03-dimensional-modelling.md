# Day 3 — Dimensional Modelling, Properly
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

1. Write the ISO 6346 check-digit algorithm from memory, in five steps (you don't need to compute one, just state the method).
2. What are the four sea/waterway-only Incoterms, and what do they have in common structurally?
3. Explain the difference between CIF and CFR in one sentence.
4. What does `DimMilestone.EventJourney = 'Equipment'` tell you about an event that `'Shipment'` wouldn't?
5. Why is 6 digits the safe HS code join level and 8–10 digits not?
6. Why should you never assume `Left(ContainerNo, 4)` equals a carrier's SCAC?

## Concept

### Grain: the decision everything else depends on

**Grain is the answer to one question: what does a single row of this table represent?** Not "roughly what" — exactly what, stated as one unambiguous sentence, before a single column gets designed. Every measure, every relationship, every aggregation rule in a fact table inherits its correctness from whether the grain statement is actually true of every row. Get the grain wrong — or leave it vague — and you will build a model that looks fine in a sample of ten rows and lies to you the moment someone slices by a dimension you didn't test.

Here is the grain of every fact table in this dataset, stated the way you should be able to state it for any table you're handed on day one of a job:

| Fact table | Grain — one sentence |
|---|---|
| `FactBooking` | One row per booking line. |
| `FactShipment` | One row per house bill of lading. |
| `FactShipmentMilestone` | One row per shipment — an accumulating snapshot, updated in place as milestones occur. |
| `FactContainerMove` | One row per equipment event — one physical container, one thing that happened to it, once. |
| `FactPortCall` | One row per vessel call at one terminal. |
| `FactFreightCharge` | One row per charge line. |
| `FactTransportLeg` | One row per truck or rail movement. |
| `FactWarehouseTask` | One row per task line. |
| `FactInventorySnapshot` | One row per SKU × site × day — a periodic snapshot, present whether or not anything happened that day. |
| `FactExchangeRate` | One row per currency × day. |
| `FactTarget` | One row per KPI × region × month × scenario. |

Read `FactShipment` and `FactContainerMove` side by side: a shipment with three containers is **one** row in the first table and **at least three separate journeys' worth of rows** — likely twenty or more, once you count every gate, load, discharge and return event for each box — in the second. If you ever `JOIN FactShipment TO FactContainerMove ON ShipmentKey` and then sum a measure from the *shipment* side without first deduplicating, every shipment revenue figure gets multiplied by however many container-move events that shipment happens to have. This single mistake — joining a coarser grain to a finer grain and summing the coarse-grain measure across the join — is the most common data-modelling error a self-taught Power BI analyst makes, and it is completely invisible in a report until someone checks the total against the general ledger.

**A cautionary worked example.** Suppose someone builds a "shipment summary" table by taking `FactShipment` and bolting on `FactContainerMove.MoveCostUsd` as an extra column, reasoning that "it's still about the shipment." A house bill with three containers, each generating nine equipment events over its life, now has its one true `Revenue_usd` figure sitting next to 27 rows' worth of `MoveCostUsd`. The moment someone drags `Revenue_usd` and sums it grouped by customer, the underlying join has silently exploded that shipment's revenue by a factor of 27 — not because anyone wrote a wrong formula, but because two different grains (one row per shipment, one row per equipment event) were merged into one table without resolving which grain the merged table is actually *at*. The fix was never a DAX fix; it was deciding, before building anything, whether the combined table's grain is "one row per shipment" (in which case container-move costs must be pre-aggregated up to shipment level *before* the merge) or "one row per equipment event" (in which case shipment revenue must be excluded, or deliberately repeated with a documented caveat). This is why grain is called the first decision, not a decision — everything downstream is only correct if it agrees with a grain statement that was fixed before the table existed.

**A second trap worth naming: not every column ending in `Key` is a surrogate key to a dimension.** `FactBooking.QuoteKey` looks, by name, exactly like `CustomerKey` or `CarrierKey` — but it's a degenerate dimension (an `int64` identifier for the quote, with no `DimQuote` table behind it), kept only because it lets you group bookings that came from the same quote. Never assume a `*Key` column implies a relationship to build; check whether the dimension it would point to actually exists in §1 of the contract before you wire anything up.

### Facts vs dimensions: the actual test

A **fact** is something you measure — usually numeric, usually the product of an event, and it's what you sum, average or count. A **dimension** is something you use to slice, filter or label a fact. The test that actually works when a column's role is ambiguous: **would a business person ever want to filter or group by this value? Then it's a dimension attribute (or belongs on one). Would a business person want to add it up, or use it as an input to a calculation? Then it's a fact measure.** `DimCarrier.OnTimeTargetPct` looks numeric, but nobody sums it across carriers — it's a target *attribute of* a carrier, used to filter or compare against, not a measurement of an event. `FactShipment.Revenue_usd` is the opposite: nobody groups by it, everybody sums it.

**Degenerate dimensions** are the exception that proves the rule: identifiers that live directly on the fact table with no separate dimension table behind them, because they carry no descriptive attributes worth a surrogate key — `BookingNo`, `InvoiceNo`, `ChargeLineNo`, `TripNo`, `OrderNo`, `QuoteKey`, `HouseBlNo`, `MasterBlNo`. They exist for grouping and drill-through ("show me every charge line on this invoice"), not for filtering by some separate business attribute — there's nothing to conform, nothing to reuse across fact tables, and no benefit to giving them their own dimension table.

### Additive, semi-additive, non-additive — worked from the contract

This distinction determines exactly one thing, but it's the thing that breaks reports most often: **can you correctly sum this measure across every dimension, including date, or not?**

**Additive** — sums correctly across *every* dimension, date included: `FactShipment.Revenue_usd`. Sum it by customer, by month, by carrier, by all three at once — every aggregation is meaningful, and `SUM()` across any slice gives you a real, addable business number (total revenue).

**Semi-additive** — sums correctly across every dimension *except* date: `FactInventorySnapshot.OnHandUnits`. You can validly sum on-hand units across every SKU in a warehouse on a given day — that's a real inventory position. You **cannot** validly sum on-hand units across *days* — a warehouse holding 500 units every day for a month does not hold 15,000 units; it holds 500. The correct aggregation across date for a semi-additive measure is the value at the **last day in the period** (a closing balance), not a `SUM()`. This is the single most common Power BI beginner mistake with inventory data, and it's exactly why `FactInventorySnapshot` exists as its own fact table rather than being folded into a transactional one — the aggregation rule genuinely differs by dimension, and the model has to respect that.

**Non-additive** — cannot be meaningfully summed across *any* dimension: `FactShipment.GrossMarginPct`. Summing a percentage across shipments produces a number with no business meaning (adding 22% and 8% and 41% gives you 71%, which answers no real question). The only correct way to get a "total" margin is to **re-derive it from its additive components**: `DIVIDE(SUM(GrossProfit_usd), SUM(Revenue_usd))`, calculated fresh at whatever grain you're viewing. Ratios, percentages, and rates are always non-additive — store the numerator and denominator as additive facts, and calculate the ratio as a measure, never as a stored column you then try to aggregate.

### The three fact types, and what breaks when you mistreat one

**Transaction fact** — one row per discrete event, written once, never revisited. `FactContainerMove` is the clean example: every gate-in, load, or discharge is a new row; nothing about a past event ever gets updated. Row count grows monotonically with activity.

**Periodic snapshot fact** — one row per entity per fixed time interval, **regardless of whether anything happened**. `FactInventorySnapshot` takes a reading of every SKU at every site on every snapshotted day, even a day with zero movement — the row still exists, because the fact being measured is a *position*, not an event. **What breaks if you treat it like a transaction fact, with numbers:** a SKU sitting at a steady 500 units on hand for 30 straight days generates 30 snapshot rows, each correctly reading `OnHandUnits = 500`. `SUM(OnHandUnits)` across that month returns 15,000 — a number with no physical meaning; the warehouse never held more than 500 units of that SKU at once. The correct read of "on-hand units for the month" takes the value at the **last snapshot date in the period** (500), not the sum. The same logic applies to `OnHandValueUsd`, `OnHandCbm`, and every other measure the contract marks "semi-additive over date" in §2.9 — the marking is not decoration, it's an instruction about which aggregation is legal.

**Accumulating snapshot fact** — one row per process instance, created once and then **updated repeatedly in place** as the process progresses through its milestones. `FactShipmentMilestone` is the textbook case: one row per shipment, with fourteen date-key columns that start at `-1` and get filled in, one at a time, as `EmptyPickupDateKey`, then `StuffingDateKey`, then `GateInOriginDateKey`, and so on, actually occur. **What breaks if you treat it like a transaction fact:** two specific mistakes. First, `COUNTROWS(FactShipmentMilestone)` never tells you "how many milestone events happened this month" — it tells you how many *shipments exist in the table at all*, because the row count doesn't grow with events, only with new shipments starting. To count milestone events in a period, you filter and count based on which date-key column falls in that period, not on the row count. Second — and this is the one that catches people who've only ever worked with append-only fact tables — an accumulating snapshot is *supposed* to be revisited and updated as new information arrives (a shipment that was stuck mid-journey last week now has its `CustomsImportClearedDateKey` populated this week). Mechanically, refreshing an accumulating snapshot is an **UPSERT**, not an **INSERT**: for every shipment already in `FactShipmentMilestone`, you re-check whether any of its 14 date-key columns should now be populated (moving from `-1` to a real `DateKey`), and you update that existing row in place — you do not append a new row for a shipment that already has one. If your ETL logic is written assuming every fact table is append-only (true for `FactContainerMove`, false here), you will either duplicate rows for shipments you should have updated, or silently fail to reflect the shipment's progress at all. `MilestonesCompleted` and `IsJourneyComplete` exist specifically so you can tell, at a glance, which rows are still "in flight" and due for another update versus which ones are finished and can be left alone.

### Star vs snowflake — the actual VertiPaq reason

The hand-wavy answer to "why star, not snowflake" is "it's simpler." That's true, but it's not the engineering reason, and it won't survive a technical interview. The real reason has two parts, both rooted in how Power BI's VertiPaq storage engine actually works:

1. **Compression is column-by-column, and it rewards repetition within a column, not table normalisation.** VertiPaq dictionary-encodes each column (stores each distinct value once, plus a compact index of which row has which value) and then run-length-encodes the result where sorting allows. A wide, denormalised dimension table with a modest number of distinct values per column compresses extremely well *regardless of how many other columns sit next to it in the same table* — `DimLocation.CountryName` compresses just as efficiently sitting next to `LocationName`, `Region` and forty other attributes as it would sitting alone in a separate `DimCountry` table. Splitting it out doesn't meaningfully improve compression; it just moves the same dictionary-encoded column to a different table.
2. **Every relationship hop a filter has to cross at query time is a real cost paid by the formula engine, not the storage engine.** A star schema resolves a filter from a dimension to a fact in one hop. Snowflake that dimension — say, splitting `DimLocation` into `DimLocation` and a separate `DimCountry` — and a filter placed on `DimCountry` now has to propagate through `DimCountry → DimLocation → Fact`, two hops instead of one, for *every single query* that filters by country. That's not a cosmetic inconvenience; it's additional relationship-traversal work the engine performs on every visual render, and it compounds badly once you have several snowflaked levels or a busy report page with many visuals.

The practical rule: keep dimensions flat and wide (a `DimLocation` with country, region and trade-region all as columns, not as a chain of normalised lookup tables) unless a genuinely independent business process needs that sub-entity as its own dimension for a different fact table — at which point it's not really "snowflaking," it's a legitimately separate conformed dimension (see below).

### Conformed dimensions and the bus matrix

A **conformed dimension** is one dimension table, with one consistent meaning and one consistent set of keys, that multiple fact tables share. `DimDate`, `DimLocation`, `DimCustomer` and `DimCurrency` aren't rebuilt per fact table — they're built once and reused everywhere, which is precisely what makes it possible to compare a shipment's revenue against a warehouse task's labour cost by the same calendar, or against the same customer, without reconciling two different ideas of "what a date is."

The **bus matrix** is how you plan this deliberately instead of by accident — business processes (facts) as rows, conformed dimensions as columns, a tick wherever that fact actually carries a foreign key to that dimension. A slice of Meridian's, built directly from the FK lists in the schema contract:

| Fact ↓ / Dimension → | Date | Location | Customer | Carrier | Currency | Mode |
|---|---|---|---|---|---|---|
| `FactBooking` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `FactShipment` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `FactContainerMove` | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| `FactFreightCharge` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `FactTransportLeg` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `FactWarehouseTask` | ✓ | — | ✓ | — | — | — |
| `FactInventorySnapshot` | ✓ | — | ✓ | — | — | — |
| `FactPortCall` | ✓ | ✓ | — | ✓ | — | — |
| `FactExchangeRate` | ✓ | — | — | — | ✓ | — |

Every dash is as informative as every tick. Two things this matrix earns you immediately, before you write a single measure: it tells you exactly which fact tables can be safely compared side by side (any two rows that both tick `Customer` and `Date` can share a customer-and-time slicer correctly), and it tells you exactly where a comparison is a category error (`FactWarehouseTask` has no `Carrier`, and `FactPortCall` has no `Customer` — a report that tries to slice warehouse labour cost by carrier, or port-call turnaround time by customer, is asking a question the model has no honest FK path to answer, and you'll know that from the matrix before a stakeholder asks it in a meeting and you have to explain, live, why the visual is blank). Building the matrix is also how you catch a *missing* conformed dimension early: if you notice that "which trade lane" is a question six different facts should be able to answer but only `DimVoyage`/`DimService` currently carry that attribute, that's a signal to check whether a lane needs to be added to a fact's FK list, not something to patch with a text filter in the report layer.

### Surrogate keys, and why unknown is `-1`, never null

Every dimension in this contract uses an `int32` surrogate key (`CustomerKey`, `LocationKey`, and so on) rather than the business key (`CustomerCode`, `LocationCode`) as the relationship join column — smaller, faster to join on, stable even if a business key format ever changes, and capable of representing history (see Day 6's SCD2 work, where one `CustomerCode` deliberately maps to several `CustomerKey` values over time).

Every dimension also carries a row with key **`-1`**, code `#NA`, name `Unknown` — and every fact table uses `-1` rather than a null when a foreign key genuinely cannot be resolved (`FactBooking.VoyageKey = -1` for a booking with no voyage assigned yet). This is not a stylistic preference; it's a mechanical necessity for two reasons: **a null foreign key does not participate in a relationship at all** — a row with a null `VoyageKey` simply falls outside any filter or slicer built on `DimVoyage`, disappearing from totals rather than appearing under an honest "Unknown" bucket, which silently understates whatever total you're looking at. And **`NULL <> NULL` in join semantics** — two null values are never considered equal, so even if you wanted nulls to collectively behave like "the same unknown category," the join engine won't let them. Pointing the FK at a real `-1` row instead means the row still participates in every relationship, still gets counted, and shows up explicitly as "Unknown" — visible, honest, and fixable, instead of quietly missing.

## Drill

**1. Grain statements (15 min).** Write a one-sentence grain statement, in your own words, for these four fact tables: `FactPortCall`, `FactFreightCharge`, `FactTransportLeg`, `FactExchangeRate`. Done = four sentences, each precise enough that a colleague could tell you whether a specific real-world event would or wouldn't produce a new row.

**2. Additive, semi-additive, non-additive, or not-a-fact-at-all (15 min).** Classify each of these ten columns. Three are deliberately not fact measures at all — say so, and say why, rather than forcing them into one of the three additivity buckets:

1. `FactShipment.Revenue_usd`
2. `FactInventorySnapshot.OnHandUnits`
3. `FactShipment.GrossMarginPct`
4. `FactContainerMove.DwellHours`
5. `DimCarrier.OnTimeTargetPct`
6. `FactPortCall.BunkerConsumedTonnes`
7. `FactBooking.IsConfirmed`
8. `FactInventorySnapshot.DaysOfSupply`
9. `DimVessel.NominalTeuCapacity`
10. `FactWarehouseTask.LabourMinutes`

Done = all ten classified (additive / semi-additive / non-additive / not a fact measure), with a one-clause reason each.

**3. Diagnose the two broken approaches (15 min).** Someone on your team proposes these two calculations. For each, say whether it's correct, and if not, what specifically goes wrong and what the correct approach is:
 (a) "To get total on-hand inventory value across this year, I'll `SUM(OnHandValueUsd)` across every row in `FactInventorySnapshot` for the year."
 (b) "To count how many customs import clearances happened in August, I'll filter `FactShipmentMilestone` to rows where `CustomsImportClearedDateKey` falls in August, and count those rows."
Done = a verdict (correct/incorrect) and a one-to-two sentence explanation for each.

**4. Star vs snowflake, argued properly (10 min).** A colleague proposes splitting `DimLocation` into `DimLocation` (port-level attributes) and a new `DimCountry` (country-level attributes, referenced by `DimLocation`) "to avoid repeating the country name on every port row." Using the VertiPaq reasoning from the Concept section — not "keep it simple" — write a three-to-four sentence response either agreeing or disagreeing, and state the specific query-time cost your answer is trying to avoid or accept.

**5. Bus matrix spot-check (5 min).** Using only the FK lists in `00_docs/SCHEMA_CONTRACT.md` §2 (no guessing), state whether `FactWarehouseTask` and `FactContainerMove` share a conformed `Customer` dimension connection — yes or no — and whether they share a conformed `Carrier` connection. Done = two yes/no answers, each justified by naming the actual FK column (or its absence) on both fact tables.

## Ship

Today's Ship artefact is the document the rest of the week is built on. Create `notes/week1/day3-star-schema.md` in your own repo containing:

1. **A one-sentence grain statement for all eleven fact tables** in the schema contract — not just the four assigned in the drill. This is the reference you will check yourself against for the rest of the programme.
2. **A bus matrix** you build yourself, rows = all eleven fact tables, columns = at least six conformed dimensions of your choosing (you must justify your column choice by checking real FK lists in the contract, not guessing which dimensions "feel" shared).
3. Your five Drill answers.

Commit with:

```
git add notes/week1/day3-star-schema.md
git commit -m "day3: grain statements + bus matrix for all 11 Meridian facts"
```

## Log

- **What clicked**: which of grain / additivity / fact-type / star-vs-snowflake finally has a mechanism behind it now, rather than just a rule you were told?
- **What did not**: which fact table's grain, or which measure's additivity, are you still unsure you'd get right under pressure?
- **What to re-ask tomorrow**: one question about how Power Query actually enforces (or fails to enforce) the grain and types you've just defined.

## Exit criteria

- [ ] All eleven fact-table grain statements written in your own words, in `day3-star-schema.md`.
- [ ] Your own bus matrix built and checked against the contract's actual FK lists, not guessed.
- [ ] All five Drill exercises answered, including the three "not a fact measure" traps in Drill 2 correctly identified as traps.
- [ ] You can explain the VertiPaq reason for star-over-snowflake without saying the word "simpler."
- [ ] You can state why `FactShipmentMilestone`'s row count never tells you how many milestone events happened in a period.
- [ ] `day3-star-schema.md` committed to your own repo.
- [ ] Log entry written.
