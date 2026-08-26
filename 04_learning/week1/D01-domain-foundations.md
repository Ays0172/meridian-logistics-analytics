# Day 1 — Domain Foundations: What Meridian Actually Sells
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

These six are drawn from the Day-0 diagnostic you sat before the programme started, not from today's material — you have nothing to revise yet, so this is a baseline check, not a memory test. Write short answers, then mark yourself against your diagnostic notes.

1. In one sentence, what is the difference between a primary key and a foreign key?
2. In Power BI's model view, what does an arrowhead on a relationship line tell you that the line itself does not?
3. You drag `Customer Name` and `Revenue` onto a table visual and get one row per customer with revenue summed. What word describes the level of detail Power BI aggregated *to*?
4. What is the practical difference between a calculated column and a measure, in terms of when each one gets evaluated?
5. If a report visual shows the wrong total when you add a slicer, what is the first model-level thing you should suspect — before assuming the DAX is wrong?
6. Name one reason a table with 50 columns and one row per transaction is usually the wrong shape for a table you're going to filter and group by (e.g. "Customer" or "Product").

If more than two of these are shaky, that is exactly the gap this programme exists to close — say so in today's Log rather than papering over it.

## Concept

### Why this day exists

Every dashboard you will build this programme sits on top of a story about how a box gets from a factory in Ningbo to a warehouse in Nagpur. If you don't know that story cold, you will build technically correct models that ask the wrong questions — and worse, you won't notice, because the numbers will still add up. A Power BI report that treats "shipment" and "container" and "booking" as interchangeable words is a report built by someone who learned the tool without learning the business. Recruiters at Maersk, DSV and Kuehne+Nagel can tell the difference in about ninety seconds. Today fixes that.

Everything below is grounded in the Meridian Global Logistics (MGL) schema — the fictional ocean carrier with an inland arm, contract warehousing, and an air/LCL desk that your whole six weeks runs on. Where a term maps to a specific table or column in `00_docs/SCHEMA_CONTRACT.md`, it's named explicitly, because that mapping is the point: the business concept *is* the reason the column exists.

### 1. What a carrier actually sells

A carrier does not sell "shipping." A carrier sells **capacity on a scheduled string of port calls** — slots on a voyage. That's it. Everything else — the booking, the bill of lading, the container, the customer relationship — is bookkeeping wrapped around that one core transaction: you are buying the right to put a defined amount of weight and volume into a defined space on a vessel that will call at your port of loading and your port of discharge on advertised dates.

This has three consequences that shape the entire data model:

- **Capacity is measured in TEU (twenty-foot equivalent units) and FFE (forty-foot equivalent units), not in "shipments."** A vessel with a nominal capacity of 18,000 TEU has sold out when its *slots* are gone, regardless of how many customers or bookings that represents. `DimVessel.NominalTeuCapacity` and `DimVoyage.AllocatedTeuCapacity` exist because capacity, not shipment count, is the scarce resource.
- **Capacity is perishable.** A slot that sails empty on Tuesday's voyage cannot be sold on Wednesday. This is why carriers will sell an empty container move at a loss rather than sail with unused space, and why `FactContainerMove` carries an `IsRepositioning` flag for the ~32% of moves that carry no revenue cargo at all — someone still has to pay to get the empty box back to where the next customer needs it.
- **The schedule is the product.** A voyage is a published rotation — `DimVoyage.RotationString`, e.g. `CNSHA-CNNGB-SGSIN-INNSA-AEJEA` — repeating on a `DimService.ServiceFrequency` of Weekly or Fortnightly. Customers aren't really buying a container move; they're buying a seat on a train that leaves on a timetable, and the carrier's entire commercial credibility rests on making that timetable mean something.

### 2. The entity chain: booking → shipment → container → bill of lading

This is the single most important structural fact in the whole domain, and it is a chain of **decreasing** cardinality at each hop in one direction and **increasing** cardinality in another. Get this wrong and every join you write for the next five weeks will silently double-count or silently drop rows.

| Hop | From | To | Cardinality | Why |
|---|---|---|---|---|
| 1 | Booking | Shipment (House B/L) | **1 → 0 or 1**, occasionally 1 → many | A booking is a request. Only a `Confirmed` booking becomes a shipment. `Rolled`, `Cancelled`, `No-Show` and `Pending` bookings (22% of the total, per the contract's status mix) never do. Occasionally a confirmed booking's cargo is split across more than one house bill at the customer's request. |
| 2 | Shipment (House B/L) | Container | **1 → 1 or many** | One house bill covers a `ContainerCount` of containers — could be one 40' box, could be twelve. The shipment is the commercial unit; the container is the physical unit. |
| 3 | Container | Equipment event | **1 → many, sequential** | One physical container generates a whole sequence of events over its life — empty pickup, gate-in, load, discharge, gate-out, empty return, and everything in between. `FactContainerMove.MoveSequence` numbers this sequence per container journey. |
| 4 | House B/L | Master B/L | **many → 1** | Multiple house bills, often from different underlying shippers, get consolidated under one master bill for the vessel-operating carrier's paperwork. This is the NVOCC split — see below. |

Read that table again slowly. A single booking (`BookingKey`) can fan out into several containers. Several house bills (`HouseBlNo`) can fan *in* to one master bill (`MasterBlNo`). Those are two different directions of one-to-many in the same physical journey, and they are why a naive `COUNT(ContainerNo)` grouped by customer will never equal a naive `COUNT(BookingNo)` grouped by the same customer — they are counting different grains of the same story.

### 3. Master vs house B/L — the NVOCC split, worked

A bill of lading is a contract of carriage and a receipt for goods. When the entity that issued the B/L to the cargo owner is not the entity that operates the vessel, you get two bills for the same physical move:

- The **master bill of lading (MBL)** is issued by the vessel-operating carrier (Meridian, in our world) to whoever booked the slot — which might be an NVOCC, not the actual owner of the goods.
- The **house bill of lading (HBL)** is issued by that NVOCC (or forwarder acting as one) to the actual cargo owner underneath them.

Worked example: Meridian issues one MBL to "Pacific Consolidators NVOCC" covering a 40' container. Pacific Consolidators has, in turn, sold LCL space inside that same container to four separate small shippers, each of whom gets their own HBL. Meridian's system sees **one** master bill and **one** container move. Pacific Consolidators' system sees **four** house bills covering fractions of that one container's `VolumeCbm`. In `FactShipment`, each of those four house bills is its own row (`HouseBlNo` distinct, `MasterBlNo` identical) — the grain is the house bill, precisely because the house bill is where the actual commercial relationship with the cargo owner lives. This is exactly why `MasterBlNo` sits on `FactShipment` as a *degenerate dimension* rather than the join key: several `FactShipment` rows legitimately share one `MasterBlNo`.

Why does NVOCC business exist at all? Because a vessel-operating carrier's minimum saleable unit is realistically a container, but a huge amount of world trade moves in volumes far smaller than a container. NVOCCs and forwarders absorb that mismatch — they buy in bulk (FCL) and sell in pieces (LCL), pocketing the spread. `DimMode.ModeCode = 'LCL'` and its `IsConsolidated = 1` flag exist for exactly this pattern.

### 4. Who's on the other side of the table

`DimCustomer.CustomerSegment` carries five values, and each one has a genuinely different set of incentives — treating them as "the same, just filtered" is the fastest way to build a KPI that makes no sense to one of them.

| Segment | What they actually are | What they optimise for | What breaks if you ignore this |
|---|---|---|---|
| **BCO** (Beneficial Cargo Owner) | The actual owner of the goods — a retailer, manufacturer, or trader shipping their own product | Landed cost and reliability of *their* supply chain; they care about `IsPerfectOrder`, not about Meridian's slot utilisation | You report "on-time %" without segmenting by BCO vs NVOCC and wonder why BCO-only dashboards look worse — BCOs ship the SLA-sensitive cargo, not the price-sensitive fill-in freight |
| **NVOCC** | A carrier without vessels — buys wholesale ocean capacity, sells retail, issues its own house bills | Margin between the rate they pay Meridian and the rate they charge their own shippers; volume, not any individual box's service level | You attribute an NVOCC's `Revenue_usd` to "the shipper" when the actual decision-maker and payer is the NVOCC, one layer up |
| **Freight Forwarder** | Arranges carriage on behalf of a shipper without necessarily taking on carrier liability (though many also act as NVOCCs) | Service breadth across modes and reliability of the carriers they book with; often multi-carrier, multi-mode for one customer | You assume one forwarder = one carrier relationship, when in reality they spread bookings across `DimCarrier` deliberately to manage risk |
| **3PL** | Runs physical logistics operations (often warehousing, sometimes transport) on a customer's behalf, may not touch ocean freight decisions at all | Operational KPIs inside the four walls — `FactWarehouseTask.IsWithinSla`, labour cost per unit — not ocean freight rates | You put a 3PL's containers into the same freight-rate analysis as a BCO's and dilute a real rate signal with a non-decision-maker |
| **SME Direct** | A small or mid-sized shipper booking directly with Meridian, no intermediary | Price and cutoff flexibility; low volume, high sensitivity to `RolloverCount` because they have no fallback options | You benchmark their `LeadTimeDays` against Global Key Accounts and conclude SMEs are "worse planners" when they're actually working with less negotiating leverage on space |

The general pattern: **the person you're building a report for is not always the person whose behaviour drives the numbers in it.** An NVOCC's shipper doesn't know Meridian exists. A BCO's supply-chain manager has never heard of the forwarder's operations desk. Your model has to be able to answer "whose decision was this?" and that's exactly what `CustomerSegment`, `ParentCustomerCode`, and `AccountManager` are for.

### 5. Headhaul, backhaul, and why the imbalance is structural

**Headhaul** is the direction carrying the dominant trade flow — Asia → Europe, Asia → North America, ISC (Indian Subcontinent) → Europe. **Backhaul** is the return leg. The imbalance between them is not a sales failure; it is the physical shape of world trade, and no amount of "sell harder" fixes it, because the goods that would fill the empty boxes going back don't exist in the volume needed.

The contract's target bands make this concrete:

| | Headhaul | Backhaul |
|---|---|---|
| Load factor | 88–96% | 55–70% |
| Empty container share | baseline | ~41% |
| Revenue per FFE | 1.0× (reference) | ~0.52× |

Read the last row carefully: a backhaul FFE earns roughly half what the same box earns headhaul, on a lane that's *also* running at a much lower load factor. This is why a sales manager who gets told "your Antwerp-to-Shanghai load factor is only 61%, fix it" is often being asked to solve a structural trade-balance problem with a commercial lever that barely moves it — European factories don't manufacture enough export volume to fill the boxes that arrived stuffed with Chinese consumer goods. The correct response to a low backhaul load factor is usually pricing (discount aggressively to move *something*, even at low margin, because an empty box costs money to reposition either way) — not a pep talk to the sales team. `DimVoyage.Direction` and `FactContainerMove.IsRepositioning` exist precisely so you can separate "this leg is structurally imbalanced" from "this leg underperformed its own historical pattern," which is a completely different, and much more useful, question.

### 6. Demurrage and detention: the trap KPI

These two charges are the most commercially important — and most commonly misread — numbers in the entire dataset.

- **Demurrage** is charged for keeping the carrier's *container* inside the terminal (the CY) beyond its free time — i.e., before the customer has even taken the box away for unpacking.
- **Detention** is charged for keeping the carrier's *container* outside the terminal, at the customer's premises or elsewhere, beyond its free time — i.e., after gate-out, before the empty box is returned.

Put simply: demurrage is a port-side clock, detention is a street-side clock, and both exist because a container is *the carrier's asset on loan*, not the customer's property. `DimEquipment.FreeDaysDemurrage` and `FreeDaysDetention` set that free window (5 days for dry, 3 for reefer, 4 for special equipment — reefers get a shorter window because idle reefer plugs are a scarcer, costlier resource). Once the free days are used, `FactContainerMove.IsPastFreeTime` flips and `DemurrageDays` / `DetentionDays` start accumulating against a **tiered** rate structure — cost per day rises the longer the box sits (tier 1: days 1–5 past free time for dry equipment, tier 2: days 6–10, tier 3: day 11+; reefer tiers step at 1–3 / 4–8 / 9+). The tiering exists because the incentive is meant to *escalate* — a flat daily rate wouldn't create urgency in the same way.

Now the framing that actually matters commercially: **D&D revenue rising is very often a sign the operation is failing, not succeeding.** A container only accrues demurrage because it's sitting still when it should be moving. If demurrage revenue spikes, the honest first question is not "great, more revenue" — it's "why are so many boxes stuck?" During the congestion event modelled into this dataset (14 Jul–14 Sep 2025 at Rotterdam and Los Angeles), demurrage charge *volume* triples (×3.1) at exactly the moment on-time arrival collapses from 68% to 31% and dwell hours at those ports run 2.6× normal. A commercial dashboard that only shows "D&D revenue: up 210%, great quarter" without also showing dwell and on-time performance is actively misleading the person reading it. You will build both views in Week 3 and see this pattern with your own eyes; file the concept away now so you recognise it when the numbers arrive.

### 7. The physical journey, term by term

Learn these grouped by *where they sit in the box's actual journey*, not alphabetically — the sequence is the mnemonic.

**Before the box moves — commercial setup**

| Term | What it means |
|---|---|
| Booking | The customer's confirmed (or not yet confirmed) request for space — `FactBooking`, one row per booking line. |
| Quote | A pre-booking rate offer; becomes `QuoteKey` on the booking once accepted. |
| Spot booking | Priced against today's market rate, not a standing contract — `FactBooking.IsSpotBooking`. |
| Named Account Tariff | A pre-agreed rate card for a specific customer, sitting between a full long-term contract and pure spot. |
| Long-Term Contract | A multi-month or multi-year rate agreement — `DimCustomer.ContractType`. |
| SCAC | Standard Carrier Alpha Code — Meridian's is `MGLU`. The universal short identifier for "which carrier." |
| Cutoff (CY cutoff / doc cutoff) | The last date/time cargo or paperwork can be accepted for a given voyage — `FactBooking.CutoffDateKey`. |
| Rollover | Booked cargo that does not make it onto the vessel it was booked for and is pushed to a later voyage — `IsRolled`, `RolloverCount`. Roughly doubles inside the congestion window. |
| No-show | The customer never turns up with the cargo at all, despite a confirmed booking. |
| Lead time | Days between booking and requested departure — `LeadTimeDays`; short lead times mean less flexibility to absorb a rollover. |

**Origin — getting the box ready and gated in**

| Term | What it means |
|---|---|
| FCL (Full Container Load) | The customer's cargo fills (or is billed for) a whole container — `DimMode.ModeCode = 'FCL'`. |
| LCL (Less than Container Load) | Cargo shares a container with other shippers' cargo, consolidated by an NVOCC/forwarder. |
| Empty pickup | The customer collects an empty container from a depot to load it themselves. |
| Stuffing | Physically loading cargo into the container — happens at the shipper's site (FCL) or at a CFS (LCL). |
| CY (Container Yard) | The terminal's storage area for full and empty containers awaiting or having completed a vessel move. |
| CFS (Container Freight Station) | A facility where LCL cargo is consolidated into containers, or deconsolidated out of them — distinct from the CY, which handles whole boxes, not loose cargo. |
| Gate-in | The container physically enters the terminal — the event that starts the terminal's clock. |
| Drayage | Short-haul trucking of a container between the port/rail terminal and a CY, warehouse or customer site. |
| VGM (Verified Gross Mass) | The mandatory declared weight of a stuffed container before it can be loaded — a SOLAS safety requirement, not a Meridian invention. |
| Customs export clearance | The origin-country regulatory release that must happen before the box can leave. |

**Main carriage — the vessel side**

| Term | What it means |
|---|---|
| Voyage | One specific sailing of one specific vessel on one rotation — `DimVoyage`, ~6,800 of them in this dataset. |
| Service / string | The named, repeating rotation a voyage belongs to — `DimService`, e.g. service code `AE7`. |
| Port call | One vessel's one call at one terminal within a voyage — `FactPortCall`, the grain that carries berth and crane productivity measures. |
| Berth | The physical quay position a vessel occupies during a port call. |
| Load factor / utilisation | Slots sold ÷ slots available on a voyage or leg — the number that separates headhaul from backhaul commercially. |
| Transhipment | Discharging a container at an intermediate hub and reloading it onto a different vessel to reach its final port — not a direct sailing. |
| Transhipment hub | A port whose primary function is exactly this — `DimLocation.IsTranshipmentHub`, e.g. Singapore, Colombo-class ports. |
| Blank sailing | A scheduled voyage the carrier deliberately skips (usually to manage overcapacity) — `DimVoyage.IsBlankSailing`; shows up in `FactPortCall` as an `Omitted` call. |
| Slot charter | One carrier buys space on another carrier's vessel (common inside alliances) rather than operating its own tonnage on that leg — `DimVessel.OperatorCarrierCode` can differ from the vessel's owning carrier for exactly this reason. |
| ETA / ATA | Estimated vs Actual Time of Arrival — the gap between them is the entire congestion story in `FactPortCall`. |

**Destination — getting the box back out**

| Term | What it means |
|---|---|
| Discharge | The container is unloaded from the vessel at the port of destination (or a transhipment port). |
| Gate-out | The container physically leaves the terminal. |
| Customs import clearance | The destination-country regulatory release required before the box can be delivered. |
| CFS stripping | Deconsolidating an LCL container's contents at destination for separate delivery to each consignee. |
| Delivery | Final handover of the cargo to the consignee (or their agent). |
| Free time | The number of days the carrier allows before demurrage/detention starts accruing — set per equipment type. |
| Last free day | The calendar date free time expires — the date that actually drives customer urgency, more than the free-time day count itself. |
| Empty return | The customer returns the emptied container to a depot, closing out its journey — the final `MoveSequence` event for that box on that trip. |

**Equipment, storage and cost mechanics**

| Term | What it means |
|---|---|
| TEU | Twenty-foot Equivalent Unit — the universal capacity currency; a 40' box is 2.0 TEU. |
| FFE | Forty-foot Equivalent Unit — the inverse convention (a 20' box is 0.5 FFE); used more in commercial/rate contexts than TEU. |
| Bonded warehouse | Customs-supervised storage where import duty is deferred until goods actually leave the facility — `DimWarehouse.WarehouseType = 'Bonded Warehouse'`, `DimLocation.CustomsRegime`. |
| Reefer plug | A powered connection point for a refrigerated container — a scarce, costlier resource than dry storage, hence reefers' shorter free-time windows. |
| Dwell time | How long a container or its cargo sits at one location before its next move — `FactContainerMove.DwellHours`; the single best early-warning signal for congestion. |
| Demurrage | See §6 — port-side "container sitting in the terminal too long" charge. |
| Detention | See §6 — street-side "container out with the customer too long" charge. |
| Per diem | Informal shorthand for the daily rate applied once free time is exhausted (used loosely for both demurrage and detention). |

**Trade pattern and network shape**

| Term | What it means |
|---|---|
| Trade lane | A named, directional corridor of trade — `DimService.TradeLane`, e.g. "Asia–N Europe." |
| Headhaul | The dominant-flow direction on a lane. |
| Backhaul | The return, structurally lighter direction. |
| Trade imbalance | The structural gap between headhaul and backhaul volume — not a performance problem, a geography-of-manufacturing problem. |
| Repositioning | Moving empty containers to where the next booking needs them, with no revenue cargo attached — `FactContainerMove.IsRepositioning`. |
| Feeder vs mainline | Mainline vessels run the long-haul legs between hubs; feeder vessels shuttle boxes between a hub and smaller regional ports — `DimVessel.VesselClass` spans Feeder through ULCV for exactly this reason. |

That's 62 terms. You will not remember all of them after one read. You are not meant to — you're meant to recognise them cold when they show up in a drill, a client conversation, or an interview, because you've now seen each one anchored to the exact place it happens and the exact column that records it.

### 8. Reading a shipment like an insider — a mini case

A recruiter-grade sanity check: given a real-looking scenario, can you narrate it correctly?

> Booking `BKG25041207`, an FCL booking from a BCO in the automotive vertical, is confirmed for a 40HC container ex-Nhava Sheva (INNSA) to Rotterdam (NLRTM) on service `AE7`, headhaul direction. It rolls once (`RolloverCount = 1`) inside the congestion window, sailing two weeks late on a different voyage. On arrival, the container transships through Singapore. The consignee's customs broker is slow; the box sits four days past free time at the destination CY before gate-out, and a further six days at the customer's yard before the empty is returned.

Correctly narrated: this is one `FactBooking` row and — because it eventually ships — one `FactShipment` row (`HouseBlNo` under some `MasterBlNo`, since it's a BCO, most likely the same as the master unless there's an NVOCC in between). It generates a full sequence of rows in `FactContainerMove` (empty pickup, stuffing/gate-in, load, transhipment discharge, transhipment load, discharge, gate-out, empty return — at minimum eight events for that one box, each on its own `MoveSequence`). The rollover shows up as `IsRolled = 1` on the booking and a real gap between `RequestedDepartureDateKey` and `ConfirmedDepartureDateKey`. The four days past free time at the CY is **demurrage**; the six days at the customer's yard is **detention** — two separate charge lines in `FactFreightCharge`, both tagged `IsDemurrageOrDetention = 1`, with different `ChargeTypeKey` values (`DEM` vs `DET`). None of this is a "late shipment" in some vague sense — it's a specific, countable sequence of events with specific financial consequences, and every one of those consequences is a row you will be able to find, filter and total once your model exists.

## Drill

All four exercises use the entity chain and vocabulary above. Write actual answers — a sentence or a number, not a tick — you'll mark them against the solutions tonight.

**1. Chain and cardinality (15 min).** Booking `BKG25018842` is an LCL booking from a small electronics SME. It gets confirmed and consolidated by a forwarder into a shared 40' container along with cargo from three other shippers under one master bill. State: (a) how many `FactBooking` rows this generates, (b) how many `FactShipment` rows it's part of, and whether that shipment's `HouseBlNo` and `MasterBlNo` are the same value or different, (c) how many *other* house bills share that same `MasterBlNo`, and (d) name the `DimMode.ModeCode` that applies. Done = all four sub-answers stated with a one-line reason each.

**2. Actor incentives (15 min).** A customer's account shows: high volume, thin `GrossMarginPct` per shipment, bookings spread across four different `DimCarrier` values in the same quarter, and an `AccountManager` who reports the relationship is "healthy" despite the low margin. Identify the most likely `CustomerSegment` and justify it from the pattern, then explain why "healthy" and "low margin" are not actually in tension for this segment. Done = segment named, justification references at least two of the four data points given.

**3. Demurrage and detention, done the hard way (20 min).** A 40HC dry container (free time 5 days, tier bands 1–5 / 6–10 / 11+ past free time) sits 9 calendar days past its last free day before gate-out. Using **illustrative** tier rates of $35/day (tier 1), $55/day (tier 2) and $85/day (tier 3) — these are not the seeded values, you'll pull the real ones from `DimEquipment` once the model exists — calculate the total demurrage charge for those 9 days. Show your day-by-day tier allocation, not just a final number. Done = a total figure with the tier breakdown shown, e.g. "days 1–5 at $X, days 6–9 at $Y."

**4. The load factor question (10 min).** Sales asks why the backhaul load factor from Rotterdam back to Asia is only 61% and wants it "fixed by Q3." Using the headhaul/backhaul figures in §5, write a three-sentence response: is this a sales execution problem, a structural problem, or some mix — and what is the one lever that actually exists here?

## Ship

Today's artefact is a written one, not a Power BI file — you haven't opened Power BI yet on this programme, deliberately, because domain fluency has to come first.

Create `notes/week1/day1-domain-notes.md` in **your own** learning repository (not this course repo) containing, **in your own words, not copied from today's Concept section**:
1. The entity chain table from §2, redrawn.
2. Your four Drill answers.
3. A five-line "explain it to a new hire" paragraph covering what Meridian sells and why backhaul load factor is structurally different from headhaul.

Commit it with:

```
git add notes/week1/day1-domain-notes.md
git commit -m "day1: domain foundations — entity chain, actor incentives, D&D drill"
```

## Log

Answer honestly, three lines each:
- **What clicked**: which one concept today finally made a term you'd heard before actually make sense?
- **What did not**: which of the 62 glossary terms, or which drill, are you still fuzzy on?
- **What to re-ask tomorrow**: one specific question to carry into Day 2's code-systems session.

## Exit criteria

- [ ] Spaced-recall answers written and self-marked against your Day-0 diagnostic notes.
- [ ] All four Drill exercises answered with working shown (not just final numbers).
- [ ] `day1-domain-notes.md` committed to your own repo with the required three sections.
- [ ] You can state, without looking, the four-hop entity chain and which hops are one-to-many in which direction.
- [ ] You can explain in one sentence why rising demurrage revenue can indicate a worsening operation.
- [ ] Log entry written.
