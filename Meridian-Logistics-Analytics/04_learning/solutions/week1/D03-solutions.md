# Day 3 — Solutions

## Spaced recall

1. (1) Map each letter to a number, A=10 upward, skipping every multiple of 11. (2) Take the first 10 characters of the container number. (3) Multiply each character's value by 2 raised to its position (0-indexed from the left). (4) Sum the 10 products. (5) Divide by 11; the remainder is the check digit, unless the remainder is 10, in which case the check digit is 0.
2. FAS, FOB, CFR, CIF. Structurally, all four transfer risk at a point defined relative to a **vessel at a port** (alongside, or on board) — they're the only rules written specifically around sea/inland-waterway carriage, which is why `DimIncoterm.ModeApplicability` marks exactly these four "Sea and Inland Waterway" and every other rule "Any Mode."
3. Both transfer risk at the same point (on board at the port of shipment) and both have the seller pay freight to the destination port; the only difference is that under CIF the seller must also arrange (minimum) cargo insurance, while under CFR insurance is left to the buyer.
4. `EventJourney = 'Equipment'` tells you the event happened to the physical box itself, independent of any specific commercial shipment — it would still occur on an empty repositioning move with no `ShipmentKey`. `'Shipment'` tells you the event is a commercial/document milestone attached to the booking or house bill, with no direct link to which physical container is involved.
5. Because the WCO's Harmonized System is only internationally standardised through the 6-digit subheading; digits 7 and beyond are each country's own national tariff schedule, built independently, so two countries' 8–10 digit codes can diverge in meaning even when their first six digits match, and definitely cannot be assumed comparable when they don't.
6. Because a carrier's SCAC (from the NMFTA/trucking-derived registry) and a container's owner code (the first 3–4 letters of `ContainerNo`, registered with the BIC) are two separate registries with no guaranteed relationship — the entity that owns/leases a box is not necessarily the entity operating the vessel service it's currently travelling on.

---

## Drill 1 — Grain statements

- **`FactPortCall`**: one row per vessel's one call at one terminal within one voyage — a new call at the same port on a later voyage is a different row, and two different vessels calling the same port on the same day are two different rows.
- **`FactFreightCharge`**: one row per individual charge line — one invoice with ten charge types generates ten rows, and a credit note against one of those lines is itself a separate row, not an edit to the original.
- **`FactTransportLeg`**: one row per single truck or rail movement — a shipment requiring drayage at both origin and destination generates at least two separate `FactTransportLeg` rows, not one.
- **`FactExchangeRate`**: one row per currency, per day — every currency in `DimCurrency` gets its own row every day the rate is recorded, whether or not that currency was used in any transaction that day.

## Drill 2 — Additivity classification

| # | Column | Classification | Reason |
|---|---|---|---|
| 1 | `FactShipment.Revenue_usd` | **Additive** | Sums correctly across customer, carrier, date, or any combination — a real total. |
| 2 | `FactInventorySnapshot.OnHandUnits` | **Semi-additive** | Sums correctly across SKU or site on one day; summing across days multiplies the same physical stock by however many days it sat there. |
| 3 | `FactShipment.GrossMarginPct` | **Non-additive** | A ratio — must be re-derived as `SUM(GrossProfit_usd) / SUM(Revenue_usd)` at whatever grain is being viewed, never summed directly. |
| 4 | `FactContainerMove.DwellHours` | **Non-additive** | A duration measured per event; summing dwell hours across unrelated events produces a number with no business meaning (you'd want an average, and even that needs care about which events to include). |
| 5 | `DimCarrier.OnTimeTargetPct` | **Not a fact measure** | It's a dimension attribute of a carrier (a target you filter or compare against), not an event measurement — it lives on `DimCarrier`, not on any fact table, and nobody sums a target across carriers. |
| 6 | `FactPortCall.BunkerConsumedTonnes` | **Additive** | A physical quantity consumed per port call — sums correctly across calls, vessels, or time to a real total fuel-consumption figure. |
| 7 | `FactBooking.IsConfirmed` | **Additive (as a count)** | A 0/1 flag is a special, useful case: summing it counts the number of confirmed bookings. It's "additive" in the narrow sense that `SUM()` gives you a meaningful count, but it isn't a measured quantity in the way revenue is — worth naming both properties. |
| 8 | `FactInventorySnapshot.DaysOfSupply` | **Non-additive** | A derived ratio-like measure (roughly, on-hand ÷ average daily usage) — summing it across SKUs or dates produces no valid interpretation; each SKU's value must be looked at on its own or re-derived. |
| 9 | `DimVessel.NominalTeuCapacity` | **Not a fact measure** | A descriptive attribute of a vessel (used to filter/group vessels by class or capacity band), not a measured event — it lives on `DimVessel`. |
| 10 | `FactWarehouseTask.LabourMinutes` | **Additive** | Sums correctly across tasks, employees, shifts or dates to a real total labour-minutes figure. |

If you classified #5 or #9 as semi-additive or non-additive rather than flagging them as "not a fact measure at all," re-read the facts-vs-dimensions test in the Concept section — the giveaway in both cases is that the column describes a *thing* (a carrier, a vessel), not an *event*, and lives on a dimension table in the contract, not a fact table.

## Drill 3 — Diagnosing the two proposals

**(a) "SUM(OnHandValueUsd) across every row in FactInventorySnapshot for the year" — INCORRECT.** `OnHandValueUsd` is marked semi-additive over date in the contract (§2.9). Summing it across every snapshot day in the year adds the same on-hand stock to itself once per snapshot date it happened to still be sitting there — for a SKU held steadily all year, this could inflate the "total" by roughly 52× (weekly snapshots) to 365× (daily snapshots) its real value. The correct approach for a year-end or point-in-time inventory value is to take the value **at the last snapshot date in the period** (or, for a genuinely time-weighted question like "average inventory investment across the year," an explicit average-over-days calculation — never a plain `SUM()`).

**(b) "Filter FactShipmentMilestone to rows where CustomsImportClearedDateKey falls in August, and count those rows" — CORRECT.** This is the right way to count events out of an accumulating snapshot: rather than counting the fact table's rows generically (which would just tell you how many shipments exist in the table, growing only as new shipments start, not as milestones occur), the approach filters on the specific date-key column that records *when the event of interest happened* and counts rows matching that filter. This correctly isolates "how many shipments had their customs import clearance event occur in August" — precisely the accumulating-snapshot-aware technique the Concept section describes. The one caveat worth flagging in a full answer: this counts *shipments whose clearance happened in August*, not "clearance events" in some more general sense — but since each shipment can only be customs-cleared once, that distinction doesn't cause an error here.

## Drill 4 — Star vs snowflake, argued properly

A strong answer disagrees with the colleague and argues from VertiPaq mechanics, something close to: "Splitting `DimLocation` into `DimLocation` and `DimCountry` doesn't meaningfully improve compression — VertiPaq dictionary-encodes `CountryName` as its own column regardless of which table it sits in, so the repeated country name compresses just as well inside the wider `DimLocation` table as it would in a separate one. What the split *does* introduce is an extra relationship hop: any report that filters or slices by country now has to propagate that filter from `DimCountry` through `DimLocation` and only then into the fact tables, instead of resolving in one hop directly from a flat `DimLocation`. That's real formula-engine cost paid on every query that filters by country, for a compression benefit that doesn't actually exist. I'd keep `DimLocation` flat and accept the 'repeated' country name — that repetition is exactly what a columnar engine is built to absorb cheaply."

A partial-credit answer correctly rejects the split but only cites "simplicity" without naming the compression-is-per-column-not-per-table point, or the specific relationship-hop cost — both need to be present for full marks, since the drill explicitly asks you not to reach for the hand-wavy version.

## Drill 5 — Bus matrix spot-check

**`FactWarehouseTask` and `FactContainerMove` — shared Customer connection: YES.** `FactWarehouseTask`'s FK list (§2.8) includes `CustomerKey` directly. `FactContainerMove`'s FK list (§2.4) also includes `CustomerKey` directly. Both point at the same conformed `DimCustomer`, so a report can legitimately slice both fact tables by the same customer.

**Shared Carrier connection: NO.** `FactContainerMove` carries `CarrierKey` in its FK list (§2.4). `FactWarehouseTask`'s FK list (§2.8) — `WarehouseKey`, `SkuKey`, `EmployeeKey`, `CustomerKey`, `ShipmentKey` — has **no `CarrierKey` at all**. A report attempting to slice warehouse task labour by carrier has no honest join path to do so; that question simply isn't answerable from this fact table without adding a new relationship (e.g., via `ShipmentKey → FactShipment → CarrierKey`, which is a legitimate but indirect path through a different fact table, not a direct conformed-dimension connection, and brings its own grain-mismatch risk of the kind covered earlier today).
