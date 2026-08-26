# Day 7 — Checkpoint 1: Solutions

Full reasoning for all 25 questions, including why each incorrect option is wrong — mark yourself against this only after attempting the full quiz closed-book.

## Spaced recall

1. Booking → Shipment (1 → 0/1, occasionally 1 → many) → Container (1 → 1/many) → Equipment event (1 → many, sequential); House B/L → Master B/L is many → 1.
2. If the weighted sum mod 11 gives a remainder of 10, the check digit is 0 (there is no single digit for "10").
3. One row per equipment event — one physical container, one thing that happened to it, once.
4. Parquet embeds its own schema and matches columns by name; CSV has no embedded schema and combines purely by position, so a reordered CSV partition would silently misalign values.
5. It changes which relationship a specific measure's calculation uses, for that calculation only; it does not change which relationship a slicer or visual-level filter travels through.
6. Because fact rows whose FK points at a non-current (historical) dimension version are excluded from any total once the dimension is filtered to `IsCurrent = 1`, silently understating historical totals for any entity that has since changed.

---

## Q1 — House bill of lading

**Correct: B.**

- A. Master bill of lading is issued by the vessel-operating carrier (Meridian) *to* the NVOCC — the wrong direction and wrong party for this question.
- **B. Correct.** The house bill is what the NVOCC issues to the actual underlying cargo owner beneath it — the document that creates the "split" discussed on Day 1.
- C. A sea waybill is a non-negotiable alternative to a bill of lading used in some direct BCO relationships; it isn't the NVOCC-to-shipper document being asked about here.
- D. A manifest is a summary listing of cargo for regulatory/customs purposes, not a contract of carriage issued to a specific shipper.

## Q2 — Backhaul structural imbalance

Model answer: Backhaul load factor sits in a structurally lower target band (55–70%) than headhaul (88–96%) because the volume of cargo available to fill the return direction is a function of global trade flow — how much a region exports versus imports — not of how well Meridian's sales team sells that specific leg, and no amount of commercial effort manufactures export volume that doesn't exist.

## Q3 — Sea/waterway-only Incoterms

**Correct: D (CIP).**

- A. FAS is correctly one of the four sea-only rules — incorrect distractor.
- B. FOB is correctly one of the four sea-only rules — incorrect distractor.
- C. CIF is correctly one of the four sea-only rules — incorrect distractor.
- **D. Correct — CIP is "Any Mode," not sea-only.** It's easily confused with CIF because both require the seller to arrange insurance, but CIP applies to any mode of transport (including multimodal/air/road) and requires all-risk cover, whereas CIF is sea-only and requires only minimum cover — two separate axes of difference that this question is testing whether you kept straight.

## Q4 — Demurrage location

**Correct: A.**

- **A. Correct.** Demurrage is the port-side clock — the container sitting inside the terminal (CY) beyond free time, before the customer has even taken it away.
- B. That's detention, the street-side clock — a container out with the customer beyond free time, a different charge entirely.
- C. Damage is a separate operational/claims issue (`FactContainerMove` / `FactShipment` have their own `IsDamaged` flags); demurrage is purely about dwell time, not condition.
- D. A missing VGM declaration is a safety/compliance failure that could delay a container from even being loaded — it isn't what demurrage charges for.

## Q5 — Why rising D&D revenue can mean the operation is failing

Model answer: Demurrage only accrues because a container is sitting still rather than moving through the network — it's a symptom of dwell, not a business outcome to celebrate on its own. During the modelled congestion event (14 Jul–14 Sep 2025 at Rotterdam and Los Angeles), demurrage charge *volume* triples (×3.1) at exactly the same time on-time arrival collapses from 68% to 31% and container dwell hours at those ports run 2.6× normal — meaning the revenue spike and the operational collapse are the *same underlying event*, not two independent facts. A dashboard that reports "D&D revenue up 210%, great quarter" without also surfacing dwell time and on-time performance is presenting a symptom of network failure as if it were commercial success, which is precisely the framing this contract is built to test whether you can resist.

## Q6 — NVOCC identification

**Correct: B.**

- A. A BCO typically concentrates volume with carriers reliable on their specific trade lane rather than spreading across four carriers in a quarter, and BCOs generally don't show "thin margin-per-shipment" in Meridian's own data the way a reseller does.
- **B. Correct.** High volume, thin margin-per-shipment, and carrier-spreading is the textbook NVOCC signature: they profit from the spread between wholesale and retail ocean rates, applied across volume, and shop across carriers for the best rate/space each period.
- C. A 3PL's economics live inside warehouse operations, not ocean freight carrier selection — this pattern doesn't fit a 3PL's typical footprint at all.
- D. An SME Direct customer has low volume and low negotiating leverage almost by definition — "high volume" directly contradicts this option.

## Q7 — DCSA's three journeys

**Correct: B.**

- A. "Origin, Transit, Destination" describes geography/journey stages, not DCSA's named journey categories.
- **B. Correct** — Equipment, Transport, Shipment are DCSA's three journeys, matching `DimMilestone.EventJourney`.
- C. Planned/Actual/Estimated are the three *event classifiers*, a different axis of the same model, not the three journeys — a common mix-up this question is specifically testing.
- D. Booking/Shipment/Delivery describes a commercial process flow, not DCSA's journey taxonomy.

## Q8 — CODECO

**Correct: C.**

- A. IFTMIN is the instruction message sent upstream of a firm booking, not a terminal gate report.
- B. IFTSTA is the general multimodal status report — plausible-sounding, but not the terminal-specific gate message.
- **C. Correct** — CODECO is specifically the container gate-in/gate-out report message, sent by a terminal or depot.
- D. BAPLIE is the vessel stowage/bayplan message — about where a box sits on a ship, not about a gate event.

## Q9 — OnHandUnits additivity

**Correct: B.**

- A. Additive would mean it sums correctly across every dimension including date — false, since summing across snapshot days multiplies the same stock by however many days it sat there.
- **B. Correct** — the contract explicitly marks `FactInventorySnapshot` measures "semi-additive over date": valid to sum across SKU/site on one day, invalid to sum across days.
- C. Non-additive would mean it can't be meaningfully summed across *any* dimension — false, since summing across SKUs on one day is perfectly valid.
- D. It is a genuine fact measure (a measured quantity from an event/position), not a dimension attribute.

## Q10 — FactShipmentMilestone grain

Model answer: One row per shipment, an accumulating snapshot fact — created once when the shipment begins and updated in place as each of its fourteen milestone date-key columns is populated over the shipment's life, rather than a new row being written for each milestone event.

## Q11 — Star vs snowflake, VertiPaq reason

**Correct: C.**

- A. "Violates Kimball's rules" is a style/authority appeal, not an engineering reason — and Kimball's own methodology explicitly discusses when snowflaking is acceptable, so this is simply not a defensible framing.
- B. "Tidier" is the hand-wavy non-answer this question is specifically designed to reject.
- **C. Correct** — this is the two-part mechanism from Day 3: VertiPaq compresses per column regardless of which table it sits in, so normalising doesn't improve compression, while every relationship hop is real formula-engine cost paid at query time.
- D. Incremental refresh is a partition/policy setting largely orthogonal to whether a dimension is snowflaked or flat.

## Q12 — FactShipmentMilestone fact type

**Correct: C.**

- A. A transaction fact is written once per discrete event and never revisited — the opposite of how this table works (its rows are updated repeatedly as milestones occur).
- B. A periodic snapshot takes a reading at fixed time intervals regardless of activity (like `FactInventorySnapshot`) — this table's rows aren't tied to a fixed time interval, they're tied to one shipment's whole lifecycle.
- **C. Correct** — one row per shipment, created once, updated in place as milestones accumulate: the defining accumulating-snapshot pattern.
- D. A factless fact records that an event happened with no numeric measures at all — this table has plenty of measures (the lag columns, `MilestonesCompleted`), so it isn't factless.

## Q13 — Why `-1` exists

**Correct: B.**

- A. "Looks tidy" is not a mechanical reason and is the kind of answer this checkpoint is designed to catch.
- **B. Correct** — this is the precise mechanism from Day 3: nulls don't participate in relationships and can never match each other in a join, so unresolved rows would silently disappear from totals rather than appearing as an honest "Unknown."
- C. Power BI does not, as a platform rule, require FK columns to be non-null — this is a modelling *convention* the contract adopts, not a tool-enforced requirement.
- D. SCD2 versioning is a separate concern (surrogate keys per version) and doesn't specifically require a `-1` Unknown member — the Unknown member exists for unresolved FKs generally, with or without SCD2 in play.

## Q14 — Summing GrossMarginPct

Model answer: `GrossMarginPct` is a non-additive ratio — summing it (or averaging that sum) across 10,000 shipments produces a number with no valid business meaning, because a percentage isn't a quantity that accumulates; two shipments at 10% and 40% margin don't combine into "25% margin" unless their revenue bases happen to be identical, which they generally aren't. The correct calculation is to re-derive the ratio from its additive components at the grain being reported: `DIVIDE(SUM(GrossProfit_usd), SUM(Revenue_usd))` across those same 10,000 shipments, which correctly weights each shipment's contribution by its actual revenue rather than treating every shipment's percentage as equally significant regardless of size.

## Q15 — QuoteKey

**Correct: B.**

- A. There is no `DimQuote` table in the schema contract — the "Key" suffix is misleading here, since it doesn't point at any dimension.
- **B. Correct** — it's a degenerate dimension: an identifier retained on the fact table purely for grouping/drill-through, with no descriptive attributes worth a separate dimension.
- C. A role-playing dimension is one dimension table referenced by multiple FK roles on the same fact (like `DimDate` via four date keys on `FactShipment`) — `QuoteKey` isn't a role of any existing dimension.
- D. A conformed dimension is shared consistently across multiple fact tables — `QuoteKey` isn't a dimension at all, conformed or otherwise.

## Q16 — View Native Query unavailability

**Correct: B.**

- A. Nothing about the file's integrity is implied by folding availability — a perfectly valid Parquet file still won't produce a native query view.
- **B. Correct** — folding, in the "View Native Query" sense, is a relational/OData-style concept; folder and flat-file connectors have no native query language to translate M into.
- C. Power BI does support Parquet (it's this dataset's entire storage format) — this option is simply false.
- D. Step count is unrelated to whether folding/native-query viewing is available for this *class* of source at all.

## Q17 — Fixing the credit-note landmine

**Correct: B.**

- A. This is the landmine itself, not the fix — it destroys every legitimate credit note.
- **B. Correct** — `try … otherwise` distinguishes genuine conversion failures from valid negative numbers, which a sign-based filter cannot do.
- C. Taking the absolute value doesn't remove the value, but it corrupts it just as badly — a credit note recorded as a positive charge is now indistinguishable from a real charge, which is arguably worse than deleting it since it's now silently wrong rather than absent.
- D. Rounding negatives to zero also destroys the correction, just via a different mechanism than filtering.

## Q18 — Fixing the locale landmine

**Correct: B.**

- A. This is the landmine itself — the default conversion silently swaps day and month for any day ≤ 12.
- **B. Correct** — an explicit `"en-GB"` culture parameter forces day-before-month parsing regardless of the refreshing machine's own regional settings.
- C. Manually re-typing every date doesn't scale and isn't how a refreshable pipeline should work — the point of the fix is that it survives an automated refresh unattended.
- D. "Usually works" is exactly the false confidence the landmine is designed to expose — the failure is silent precisely because it doesn't announce itself.

## Q19 — Folder-combine step order

Model answer: `Year`/`Month` must be recovered from `[Folder Path]` **before** the per-file combine function is invoked (i.e., while you're still working with the file-listing/navigation table, before the files are actually parsed and stacked together). The order matters because once files are combined into one in-memory table, you'd have to derive the partition value from something *inside* each row instead of from the path it actually came from — which only happens to give the right answer if file content and folder path always agree, a guarantee you have no way to enforce for a row that might legitimately be processed into a different partition than its own event date implies.

## Q20 — Why Parquet survives reordered columns

**Correct: B.**

- A. Power Query does not reorder or auto-sort a source's columns before combining — it reads what the file gives it.
- **B. Correct** — Parquet's self-describing schema means columns are matched to your table by name, regardless of physical position in the file.
- C. Parquet files can absolutely be written with different column orders — that's exactly what happened in landmine #9's partition, and it's a legal, valid Parquet file.
- D. Power Query does not ignore column order "for every file format" — CSV combination is precisely the counterexample, since it's positional.

## Q21 — What USERELATIONSHIP changes

**Correct: B.**

- A. Slicers always filter via whichever relationship is currently active, regardless of any measure's `USERELATIONSHIP` — this is the exact misconception Day 5 warns against.
- **B. Correct** — it activates a specific inactive relationship for the duration of one measure's calculation, and only that calculation.
- C. Cardinality is a structural property of the relationship itself, set when the relationship is created — `USERELATIONSHIP` doesn't touch it.
- D. The change is scoped to the single calculation it's used in — it does not make the relationship active in the model generally, or permanently.

## Q22 — Simultaneous multi-role slicing

**Correct: C.**

- A. `USERELATIONSHIP` only affects a measure's own calculation, not what a slicer filters through — it cannot deliver two independently-slicing roles on one page.
- B. A single bidirectional relationship doesn't solve the "two different roles, two different columns" problem at all — bidirectionality is about filter *direction*, not about representing multiple distinct roles of the same dimension.
- **C. Correct** — importing the dimension multiple times, each renamed to its role with its own always-active relationship, is the only way to get independent, simultaneous slicer-level filtering by each role.
- D. There's no many-to-many relationship involved here at all — this is a role-playing one-to-many problem, not a bridge-table scenario.

## Q23 — Inactive relationship filter propagation

**Correct: C.**

- A. Bidirectional propagation requires an *active* relationship explicitly set to filter both ways — an inactive relationship isn't a bidirectional one left dormant, it's dormant in both directions.
- B. Single-direction propagation also requires an active relationship — inactive means neither direction works by default.
- **C. Correct** — no filter propagates through an inactive relationship unless a measure specifically activates it with `USERELATIONSHIP`.
- D. There's no such rule limiting inactive relationships to numeric columns — filter propagation isn't column-type-dependent in this way.

## Q24 — The inactive-relationship symptom

Model answer: A visual (e.g. a card showing a summed measure) that is correctly wired to a slicer, with the slicer visibly showing a selection, but whose displayed number does not change at all when the slicer selection changes — it continues to show the grand total, unfiltered, with no error message, no blank result, and nothing else about the visual looking obviously wrong. A "wrong DAX formula" bug typically produces a *specific* incorrect number that does change with the filter, just to the wrong value — the inactive-relationship symptom is distinguished by the number not responding to the filter *at all*.

## Q25 — The ambiguity triangle

Model answer: `DimCustomer` relates directly to both `FactBooking` and `FactShipment`, and `FactBooking` and `FactShipment` are also directly related to each other via `BookingKey` — a triangle. Making the `DimCustomer`–`FactBooking` edge bidirectional opens a second route by which a filter on `FactShipment` could reach `DimCustomer` (directly, and via `FactBooking`), which is exactly the ambiguous-cycle shape Power BI's engine is built to prevent — it will either refuse to create the relationship as specified, or produce results that depend on internal evaluation order in a way that's hard to reason about from the report layer. The safer alternative is to build the specific "respond to shipment-level filters" behaviour as an explicit measure (e.g., using `CALCULATE` with a targeted table-filter argument reaching into `FactShipment` for that one calculation) rather than a standing bidirectional relationship that changes filter behaviour for every visual on every page, including ones that never needed it.

---

## Scoring guidance

Give yourself one point per question (Q1–Q25), with short-answer and written-explanation items marked correct if they capture the *mechanism*, not just a correct-sounding conclusion — e.g. for Q5, "because demurrage is bad" without naming the specific dwell/on-time/volume magnitudes from §3.3 is a partial answer at best. **18/25 is the pass mark.** If you're between 15 and 17, you're close — use the remediation map in the module before assuming you need to redo the whole week. Below 15 across more than one section is a genuine signal to slow down and rebuild, not to push forward into Week 2 hoping it resolves itself.
