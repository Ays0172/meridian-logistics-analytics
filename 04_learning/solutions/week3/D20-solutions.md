# Day 20: solutions

---

## Spaced recall answers

1. `MAX(GrossWeightKg, VolumeCbm)` returns `GrossWeightKg` for essentially every
   real air shipment, because `VolumeCbm` (a bare cubic-metre count) is
   dimensionally almost always smaller than `GrossWeightKg` (a kilogram count),
   the volume branch would only win at a density below ~1 kg/cbm, physically
   impossible for real cargo.
2. `TREATAS(VALUES(A[col]), B[col])` applies `A`'s current values as a filter onto
   `B[col]`, `A` supplies values, `B` gets filtered. Reversed, it filters the
   wrong table silently: no error, a plausible-looking wrong number, and any
   measure on the un-filtered side stops responding to the filter context at all.
3. It walks backward from the current filter context's last date until it finds
   the most recent date the fact table actually has rows for, then applies that
   single date as the filter, "most recent known balance," correct even across a
   sampling-cadence gap.
4. `DimCustomer` is SCD2, one durable customer can have several `CustomerKey`
   surrogate versions over time, but only one `CustomerCode`. Ranking or grouping
   by `CustomerKey` can split one real customer's revenue across multiple "top 10"
   slots under different key versions, understating true concentration.
5. FYTD (through 30 Sep 2025, Oct 2024–Sep 2025) was **45.0% larger** than plain
   calendar YTD through the same date ($435,565,820 vs $300,286,005), a
   $135,279,815 difference entirely from the extra Q4 2024 quarter FYTD includes
   and calendar YTD doesn't.

---

## Exercise 20.1: Cash-to-Cash, built and labelled

```dax
Days Inventory Outstanding (proxy) := [Days on Hand]

Days Sales Outstanding (contractual-terms proxy) :=
DIVIDE (
    SUMX ( FactShipment, FactShipment[Revenue_usd] * RELATED ( DimCustomer[PaymentTermsDays] ) ),
    SUM ( FactShipment[Revenue_usd] )
)

Cash-to-Cash Cycle Time (partial) :=
[Days Inventory Outstanding (proxy)] + [Days Sales Outstanding (contractual-terms proxy)]
-- description: [XCT.FIN.C2C] PARTIAL FIGURE, DIO + DSO only. DPO is not
-- computable under this contract (no vendor payment-terms field, no
-- accounts-payable fact); dropping it always makes this number look longer
-- (worse) than the true cash-to-cash cycle would be. Never relabel without
-- this caveat.
```

**A hardcoded `- 0` "DPO" is strictly more dangerous than an honestly-named
partial figure.** `[DIO] + [DSO] - 0` produces a measure whose name and formula
both *look* complete, three terms, matching the textbook `DIO + DSO − DPO`
structure exactly, while silently asserting "vendor payment terms are zero days,"
a specific, false, and unstated business claim, rather than "this component is
unknown." A reader glancing at a formula bar sees what looks like the real
formula and has no reason to suspect anything is missing; a reader glancing at
`Cash-to-Cash Cycle Time (partial)` sees the word "partial" and knows to ask. **The
rule:** never substitute a hardcoded value for a genuinely missing component,
even a value (like zero) that seems conservative or neutral, name the gap in the
measure itself, in a way that survives a report author copying the measure without
reading its DAX.

---

## Exercise 20.2: Top-10 concentration, both ways

```dax
[DO NOT USE] Top-10 Customer Share (naive) :=
VAR Top10Static = { "CUS0001", "CUS0002", "CUS0003", "CUS0004", "CUS0005", "CUS0006", "CUS0007", "CUS0008", "CUS0009", "CUS0010" }
RETURN
    DIVIDE (
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), DimCustomer[CustomerCode] IN Top10Static ),
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), ALL ( DimCustomer ) )
    )

Top-10 Customer Share :=
VAR CustomerRevenue = ADDCOLUMNS ( VALUES ( DimCustomer[CustomerCode] ), "CustRev", CALCULATE ( SUM ( FactShipment[Revenue_usd] ) ) )
VAR Top10Revenue = SUMX ( TOPN ( 10, CustomerRevenue, [CustRev], DESC ), [CustRev] )
VAR TotalRevenue = SUMX ( CustomerRevenue, [CustRev] )
RETURN DIVIDE ( Top10Revenue, TotalRevenue )
```

**The naive static-list version tends to read *lower* than the correct dynamic
version over time**, not higher, a hardcoded list captures whichever ten
customers were largest *at the moment the list was written*, and as new large
customers grow into genuine top-10 territory afterward, the static list keeps
crediting its original ten (some of whom may have shrunk) while the dynamic
version always re-ranks to the *current* top ten, whose combined share is by
definition at least as large as any other fixed set of ten customers' share. Over
a multi-year book with real customer churn and growth, the true top 10 will
usually out-earn a stale fixed list. `README` §6 states the current build's
correct figure at **27.8%**.

Ranking by `CustomerKey` instead of `CustomerCode` should produce a **different
(and structurally understated) top-10 figure** whenever one of the true top-10
customers has more than one SCD2 version in scope, the customer's revenue splits
across two or more `CustomerKey` rows, each individually smaller and each
competing separately for a `TOPN` slot, so that customer is under-represented (or
misses the top 10 entirely) relative to ranking by their durable `CustomerCode`.
Confirm the split against your own build by checking whether any `CustomerCode`
among your top 10 has more than one row in `DimCustomer`.

---

## Exercise 20.3: the SCOR map, applied

Counting directly from `KPI_DICTIONARY.md`'s full SCOR mapping table (§5,
`XCT.SCOR.MAP`):

| Attribute | KPI count |
|---|---|
| Reliability | **13** |
| Responsiveness | 9 |
| Agility | 5 |
| Cost | 9 |
| Asset Management | **13** |

**Reliability and Asset Management are tied at 13 KPIs each**, the two largest
attribute buckets, not one clearly larger than the other. If your prediction
picked one over the other, the honest answer is that a confident guess between two
tied categories is exactly the situation where counting the dictionary's own table
beats intuition, Reliability *feels* like it should dominate a logistics
scorecard because it's the attribute most often discussed in executive reviews, but
Asset Management (load factors, utilisation, turns, inventory efficiency) is
structurally just as large in this KPI set, because so much of Ocean and Warehouse
is fundamentally about capacity utilisation.

---

## Exercise 20.4: Margin Dispersion, the trap it's designed to catch

```dax
Gross Margin % Std Dev := STDEVX.P ( FactShipment, FactShipment[GrossMarginPct] )
Gross Margin % P10-P90 Spread :=
VAR P90 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.9 )
VAR P10 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.1 )
RETURN P90 - P10
```

Filtered to the Jul–Sep 2025 congestion window versus a calm comparison period, the
**mean gross margin should move relatively little**, margin is driven mostly by
the commercial rate/cost structure, which the congestion event does not directly
target, while the **P10–P90 spread should widen noticeably**, because the
operational disruption (rolled bookings, demurrage exposure, expedited-cost
scrambling on affected lanes) disproportionately drags down the *worst*-performing
shipments in the book without moving typical ones much. That combination, flat or
gently-moving mean, widening spread, is precisely the "stable-looking average
hiding a growing loss-making tail" scenario the KPI exists to catch, and is a
genuine, checkable pattern worth confirming against your own build's exact numbers
for the two periods you choose.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Perfect Order Rate, company-wide (README §6) | 0.8574 |
| Top-10 customer revenue share (README §6) | 27.8% |
| FYTD vs calendar YTD through 30 Sep 2025 | $435,565,820 vs $300,286,005 (+45.0%) |
| SCOR attribute KPI counts | Reliability 13, Responsiveness 9, Agility 5, Cost 9, Asset Management 13 |
| Gross margin validation gate | 14–22% mean, documented left tail below zero |
