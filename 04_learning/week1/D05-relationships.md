# Day 5 — Relationships: Cardinality, Direction, and the Meridian Constellation
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

1. Why does Parquet survive a reordered-column partition and CSV would not?
2. State the `try … otherwise` pattern and what specific category of problem it's meant to catch — and what it must never be used to catch.
3. What is silently wrong about applying Power Query's default date-type conversion to a `dd/MM/yyyy` text column on a US-locale machine?
4. Why is "View Native Query" expected to be unavailable for every query built against Meridian's Parquet folder sources?
5. State the folder-combine pattern's step order — specifically, when do you recover `Year`/`Month` from the folder path relative to when you combine the files?
6. Name two of the seven "other landmines" from Day 4's landscape table and their correct handling.

## Concept

Everything you built yesterday is a set of correctly-typed, correctly-cleaned tables sitting in isolation. Today they become a *model* — and a model is only as correct as its relationships, because a relationship is the mechanism that decides which rows in one table are allowed to affect which rows in another. Get a relationship's cardinality, direction, or active/inactive status wrong, and every measure built on top of it can be individually correct DAX computing a collectively wrong answer — which is precisely why the symptom you'll learn to recognise today ("the slicer works, the number doesn't move") is a model problem dressed up as a DAX problem.

A word on why this day sits precisely here in the sequence, not earlier or later: you couldn't usefully learn relationships before Day 3's grain and fact-type vocabulary, because "cardinality" is meaningless without first knowing what a single row on each side actually represents — and you couldn't build a relationship at all before Day 4's cleaned, correctly-typed tables existed to relate. Today is the hinge between "I have clean tables" and "I have a model that answers questions correctly," and it's also the day most self-taught Power BI users skip past fastest, because a relationship that's merely *present* looks, superficially, exactly like a relationship that's *correct* — right up until someone changes a slicer.

### 1. Cardinality — what it actually constrains

A relationship's cardinality describes how many rows on each side can match a given value. In this dataset:

- **One-to-many** is the overwhelming default — one `DimCustomer` row can be referenced by many `FactBooking` rows, one `DimVoyage` row by many `FactContainerMove` rows. This is the shape a star schema is built around: one dimension row, many fact rows sharing it.
- **One-to-one** is rare, and when you think you've found one, treat it as a design smell rather than a discovery. If two tables genuinely have exactly one row on each side for every match, the honest question is: why are these two tables, not one? (`DimVessel` and a hypothetical `DimVesselTechnicalSpec` with one row per vessel each is a 1:1 relationship that should almost always just be one wider `DimVessel` table instead — splitting it achieves nothing except an extra relationship hop, for the VertiPaq reasons you learned on Day 3.)
- **Many-to-many** needs a **bridge table** and doesn't occur natively anywhere in this contract's fact-to-dimension design — and that's deliberate, not an oversight. `FactShipment` carries exactly one `CommodityKey`, meaning the model has chosen the grain "one dominant commodity per shipment" specifically to avoid needing a many-to-many bridge between shipments and commodities. If Meridian's real business genuinely needed to track several distinct commodities within one house bill, that would force either a lower grain (one row per commodity-within-shipment) or an actual bridge table — recognising when a business fact *requires* many-to-many, versus when a grain decision has quietly avoided it, is a modelling judgement call worth noticing, not assuming away.

One more cardinality-adjacent setting worth naming precisely, because it's easy to toggle without understanding what it does: **assume referential integrity**. When switched on for a relationship (available for import-mode tables against certain sources), Power BI generates an inner-join-style query instead of an outer join when resolving that relationship, on the promise that every fact-side key genuinely matches a dimension-side key — which is exactly the guarantee the `-1` Unknown-member convention exists to provide. If you've correctly routed every unresolved FK to `-1` rather than leaving genuine orphans, turning this on is safe and measurably faster; if you haven't, it can silently drop rows that would otherwise have matched the Unknown member. It's a real performance lever, but only once the data underneath it actually earns the trust the setting extends to it.

### 2. Filter propagation direction, and why single-direction one-to-many is the default

A relationship's arrow tells you which way a filter is allowed to travel. The default for a one-to-many relationship is **single-direction, dimension to fact**: filtering `DimCustomer` to one customer correctly restricts `FactBooking` to that customer's rows. The reverse — filtering `FactBooking` and expecting `DimCustomer` itself to shrink to only customers who appear in the filtered bookings — does **not** happen automatically with single-direction filtering, and that's correct behaviour, not a limitation to "fix" reflexively. A customer list visual should generally still show all customers, not silently vanish rows the moment someone filters bookings to last month; whether you actually want the reverse behaviour is a specific, deliberate report-design decision, not something to switch on by default because it "seems more responsive."

**Bidirectional cross-filtering exists for the cases where you genuinely do want that reverse flow** — but every bidirectional relationship you add doesn't just solve one filtering need, it adds a new path a filter can travel across the *entire* model, and if that new path can combine with any other existing path to reach the same table two different ways, you've created ambiguity (§6). This is why bidirectional is a tool for a specific, checked need, not a default setting to leave on because reports "feel" more correct with it everywhere.

### 3. Active vs inactive relationships

Power BI allows only **one active relationship between any given pair of tables at a time.** The moment you create a second relationship between two tables that already have one, the new one is automatically drawn as **inactive** (a dashed line in Model view) — this isn't an error, and it isn't optional; it's the engine enforcing that filter propagation between any two tables has exactly one unambiguous default path. An inactive relationship propagates **no filter at all** unless a measure explicitly activates it for the duration of that one calculation, using `USERELATIONSHIP`. This single mechanical fact — inactive means silent, not "weaker" — is the root of the diagnostic drill later today: a visual wired to an inactive relationship doesn't error, doesn't warn, and doesn't look wrong at a glance. It just quietly ignores whatever filter you thought was reaching it.

Two independent visual signals in Model view are worth being able to read apart, because someone with "some Power BI, weak modelling" experience often conflates them: **solid vs dashed** tells you active vs inactive; **the `1` and `*` markers at each end** tell you cardinality. A dashed one-to-many relationship and a solid one-to-many relationship look almost identical at a glance if you're not specifically checking the line style — and it's exactly that glance-over that lets an inactive relationship sit unnoticed in a model for weeks.

### 4. Role-playing dimensions: the date pattern, built for real on `FactShipment`

`FactShipment` carries **four** distinct date-key columns pointing conceptually at the same calendar: `ShipmentDateKey` (actual departure), `EtaDateKey`, `AtaDateKey`, and `DeliveryDateKey`. All four need `DimDate`, but only one relationship between `FactShipment` and `DimDate` can be active at once. The standard, correct pattern:

1. Make **`ShipmentDateKey`** the active relationship — it's the natural default "when did this happen" business date for most shipment reporting.
2. Create the other three relationships (`EtaDateKey`, `AtaDateKey`, `DeliveryDateKey` → `DimDate.DateKey`) — Power BI will draw all three as inactive automatically.
3. Write specific measures that need a different date role using `USERELATIONSHIP` to activate the one they need, for that calculation only:

```
Shipments by ETA =
CALCULATE(
    COUNTROWS(FactShipment),
    USERELATIONSHIP(FactShipment[EtaDateKey], DimDate[DateKey])
)

On-Time Delivery Count =
CALCULATE(
    COUNTROWS(FactShipment),
    USERELATIONSHIP(FactShipment[DeliveryDateKey], DimDate[DateKey]),
    FactShipment[IsOnTime] = 1
)
```

**The nuance that catches people who've only read about this pattern rather than built it: `USERELATIONSHIP` changes which relationship a *measure's calculation* uses — it does nothing to which relationship a slicer or visual-level filter travels through.** A date slicer on your report page always filters via whichever relationship is currently active (`ShipmentDateKey`, in this setup), regardless of what any individual measure's `USERELATIONSHIP` says internally. If you need a slicer that visibly filters by ETA at the same time another slicer filters by delivery date, `USERELATIONSHIP` cannot give you that — which is exactly why the *next* pattern exists.

One more mechanical detail worth stating precisely, because it's exactly the one place the `-1` Unknown-member convention from Day 3 does **not** apply the same way: a shipment still `In Transit` has not yet had its `AtaDateKey` or `DeliveryDateKey` event occur, so the fact row carries `-1` in that column, per the contract's global "facts use `-1` rather than null for FKs" convention. But `DimDate` is one of exactly two dimensions in this model (with `DimTime`) that deliberately carries **no** `-1`/Unknown row at all — a synthetic "Unknown" date doesn't fit into a real calendar the way a synthetic "Unknown" label fits into a text dimension, so the contract exempts them. That `-1` FK therefore has nothing to join to inside `DimDate` at all: Power BI's relationship engine falls back on its own automatically generated blank row for the unmatched key, the same mechanism it uses for any FK with no matching dimension row, not a row you control or can format the way the explicit `-1` convention lets you do elsewhere. The practical upshot is still the one worth keeping: the in-transit shipment does not simply vanish from a visual filtered through the `AtaDateKey` role-play relationship, it shows up as a blank bucket — but the mechanism producing that blank is Power BI's default unmatched-key handling, not a `-1` row DimDate actually contains. If `AtaDateKey` were left null instead of `-1`, nothing here would change, since a blank `DateKey` still has no `DimDate` row to match.

### 5. Role-playing dimensions: the location pattern, and why it's solved differently

`FactShipment` also carries **four** location-key columns: `LocationKeyOrigin`, `LocationKeyDestination`, `LocationKeyPol` (port of loading), `LocationKeyPod` (port of discharge). This looks like the same problem as the date roles — but it usually isn't solved the same way, because the *reporting need* is different: you very plausibly want a report page where one slicer filters by origin country **and** a separate slicer, at the same time, filters by destination country. `USERELATIONSHIP` can't deliver simultaneous multi-role slicing, because it only takes effect inside a specific measure's `CALCULATE`, not at the visual/slicer level.

The standard fix here is to **import `DimLocation` more than once**, as genuinely separate tables in the model, each renamed to its role (`DimLocationOrigin`, `DimLocationDestination`, `DimLocationPol`, `DimLocationPod`), each with its own single, always-active relationship to the matching FK column on `FactShipment`. Every one of the four can now sit on the same report page, in its own slicer, filtering simultaneously and independently — because from the model's point of view, they're just four separate dimension tables that happen to share their source data and structure, not four roles competing for one relationship slot.

**The decision rule worth remembering:** if you only ever need *one* role active in a given calculation at a time, and never need to slice by two roles simultaneously in the same visual, `USERELATIONSHIP` on a single shared table is the leaner choice (this is almost always true for date roles — you rarely want to slice the same visual by ETA *and* delivery date at once). If you need genuinely simultaneous, independent slicing by multiple roles, import the dimension multiple times (this is almost always true for the four location roles — origin and destination filtering together is an entirely normal, expected report requirement).

### 6. Ambiguity, and why bidirectional filtering is a last resort

Here's a concrete ambiguous path sitting latent in the Meridian constellation, waiting for a well-meaning bidirectional toggle to activate it. `DimCustomer` relates directly to both `FactBooking` and `FactShipment` (both carry `CustomerKey`). Separately, `FactBooking` and `FactShipment` are *also* directly related to each other, via `FactShipment.BookingKey → FactBooking.BookingKey`. Draw that as a diagram and you get a triangle: `DimCustomer` → `FactBooking` → `FactShipment`, and `DimCustomer` → `FactShipment` directly. Two different routes connect `DimCustomer` to `FactShipment`.

This is not a one-off — the same triangle shape recurs wherever a dimension relates to two fact tables that are themselves directly related, and this dataset has several: `DimCustomer` also sits above both `FactContainerMove` and `FactShipment`, which are again directly linked via `FactContainerMove.ShipmentKey → FactShipment.ShipmentKey`. Recognise the shape once and you'll spot it everywhere: **dimension → fact A → fact B**, plus **dimension → fact B** directly, is a triangle the instant a fact-to-fact relationship exists alongside two ordinary dimension relationships — and this model has several legitimate fact-to-fact relationships (`FactShipment.BookingKey`, `FactContainerMove.ShipmentKey`) precisely because the entity chain from Day 1 is real, not a diagram convenience.

With every relationship left as the single-direction default, this triangle is harmless — filters only ever flow one way (dimension into fact), so there's no route by which a filter could loop back and create a second, conflicting path to the same table. **The moment you make the `DimCustomer`–`FactBooking` relationship bidirectional** (a tempting move if you want a "customers with at least one booking" visual to also respond to shipment-level filters), you've opened a second, opposite-direction lane on one side of the triangle — and now a filter applied to `FactShipment` can potentially reach `DimCustomer` two different ways: directly, and via `FactBooking`. Power BI's engine either blocks the second relationship outright at authoring time specifically because it would create this kind of ambiguous cycle, or — if it allows it — the result becomes dependent on internal evaluation order in a way that is genuinely difficult to reason about from the report layer alone. Either outcome is worse than not having the bidirectional relationship. **This is the actual argument for treating bidirectional filtering as a last resort**: it isn't that bidirectional filtering is "advanced" or "risky" in some vague sense — it's that any triangle or diamond shape already latent in your relationship graph (and a busy operational model like this one has several) turns into a real ambiguity problem the instant you add a second direction to just one edge of it.

### 7. A quick reference: which technique, for which need

| Need | Technique | Why |
|---|---|---|
| One calculation needs a non-default role, occasionally, one at a time | `USERELATIONSHIP` inside a specific measure | Cheapest option; no extra tables; but invisible to slicers |
| Two or more roles must be independently, simultaneously slicer-filterable on the same report page | Import the dimension multiple times, one table per role | The only way a slicer can filter by a role that isn't the active relationship |
| A dimension should restrict which fact rows are relevant, and also be restricted back by fact-level filters | Bidirectional — but only after checking for triangles/diamonds elsewhere in the model | Real, occasional need; never a default |
| A relationship exists but should never propagate a filter at all in normal use | Leave it inactive, invoke only via `USERELATIONSHIP` where needed | This is the *intended*, not accidental, use of inactive — Drill 4 shows you the *accidental* version |

One last thing worth saying plainly before the drills: everything in this Concept section is checkable by building it and watching what happens, not by reasoning about it in the abstract — which is exactly why every drill below asks you to build something and record what you actually saw, not to write an essay about relationships in general. A model built by someone who has genuinely watched a slicer stop working, once, because of an inactive relationship, debugs that symptom in thirty seconds the next time it appears in someone else's report. A model built by someone who has only read the rule debugs the same symptom by re-checking DAX for twenty minutes first, because the model itself never occurred to them as the suspect.

## Drill

**1. Cardinality classification (10 min).** State the cardinality (one-to-many, one-to-one, or many-to-many) for each of these four real relationships, and for the fourth, answer the follow-up question: (a) `DimCarrier` → `FactContainerMove`, (b) `DimEquipment` → `FactShipment`, (c) `FactBooking` → `FactShipment` (via `BookingKey`), (d) *hypothetically*, if Meridian added a `DimVesselCrewRoster` table with exactly one row per vessel, every attribute describing that vessel's current crewing arrangement — what cardinality would connect it to `DimVessel`, and what should you seriously consider doing instead of creating it as a separate table? Done = four cardinalities stated, with (d)'s follow-up answered.

**2. Build the location role-play (15 min).** In your model, import `DimLocation` four times, rename each to its role (`DimLocationOrigin`, `DimLocationDestination`, `DimLocationPol`, `DimLocationPod`), and wire each to its matching FK on `FactShipment`. Place two slicers on one report page — one from `DimLocationOrigin[CountryName]`, one from `DimLocationDestination[CountryName]` — and confirm both filter a shipment-count visual simultaneously and independently. Done = both slicers demonstrably change the visual's total on their own, and combined.

**3. Build the date role-play and a USERELATIONSHIP measure (15 min).** Wire `FactShipment` to `DimDate` with `ShipmentDateKey` active and `EtaDateKey`, `AtaDateKey`, `DeliveryDateKey` inactive. Write the `Shipments by ETA` measure from §4, place it in a table visual next to a plain `COUNTROWS(FactShipment)` measure, both sliced by the same `DimDate` year slicer, and confirm the two measures give different totals for at least one year (they should, since ETA and actual shipment date don't always fall in the same year for shipments near a year boundary). Done = both measures visible side by side with a demonstrated, explained difference for at least one year.

**4. Break it on purpose, then read the symptom (10 min).** Take your working `ShipmentDateKey` relationship from Drill 3 and manually set it to **inactive** (right-click the relationship in Model view, or edit its properties). Place a card visual showing `SUM(FactShipment[Revenue_usd])`, sliced by a `DimDate` year slicer. Change the slicer. Record exactly what you observe — does the number change? Then restore the relationship to active and confirm the same slicer now works. Done = the "before" symptom recorded precisely (not just "it was wrong" — state exactly what the number did or didn't do), and the fix confirmed.

**5. The ambiguity scenario, argued (10 min).** Using the `DimCustomer` / `FactBooking` / `FactShipment` triangle from §6, write three to four sentences explaining why setting the `DimCustomer`–`FactBooking` relationship to bidirectional is risky given the existing `FactBooking`–`FactShipment` relationship, and state the safer alternative if you actually need a "customers with bookings" filter to respond to shipment-level context.

## Ship

Update `pbix/meridian-week1.pbix` (or your Power Query/model file from Day 4) so it contains, and demonstrably works:

1. The four-times-imported `DimLocation` role-play (Drill 2), independently filterable.
2. The single-shared `DimDate` role-play with `ShipmentDateKey` active and the `Shipments by ETA` measure using `USERELATIONSHIP` (Drill 3).
3. A short written note (in the same notes file as previous days, `notes/week1/day5-relationships.md`) recording the exact symptom you observed in Drill 4, in your own words — this is the single most job-relevant sentence you'll write this week: "here is precisely what an inactive relationship looks like from the report side, before you know to check the model."

Commit with:

```
git add pbix/meridian-week1.pbix notes/week1/day5-relationships.md
git commit -m "day5: location + date role-playing dimensions, inactive-relationship symptom documented"
```

## Log

- **What clicked**: which distinction — cardinality, direction, active/inactive, or the two different role-playing techniques — finally has a concrete "I did this and saw it happen" behind it?
- **What did not**: are you still unsure when to reach for `USERELATIONSHIP` versus importing a dimension multiple times? That's the single most commonly confused pair from today — say so if it's you.
- **What to re-ask tomorrow**: one question about how the date dimension you've been role-playing today actually gets built in the first place, and what "mark as date table" is protecting you from.

## Exit criteria

- [ ] Cardinality correctly stated for all four Drill 1 relationships, including the 1:1 design-smell judgement in (d).
- [ ] `DimLocation` imported four times, each role wired and independently filterable in a live visual.
- [ ] `DimDate` role-play built with one active + three inactive relationships to `FactShipment`, and the `Shipments by ETA` `USERELATIONSHIP` measure demonstrably differs from a plain count for at least one year.
- [ ] The inactive-relationship symptom from Drill 4 observed, recorded precisely, and fixed.
- [ ] The ambiguity/bidirectional argument in Drill 5 correctly identifies the triangle and states a safer alternative.
- [ ] `day5-relationships.md` committed with the Drill 4 symptom description in your own words.
- [ ] You can state, without looking, why `USERELATIONSHIP` does not help a slicer filter by a non-active role.
- [ ] Log entry written.
