# Day 2 — Code Systems as Data-Modelling Problems
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

1. State the four-hop entity chain from Day 1 and which hops are one-to-many, in which direction.
2. What is the structural (not sales) reason backhaul load factor runs lower than headhaul?
3. Explain, without using the word "late," what a rollover actually is.
4. Demurrage and detention are both "container overdue" charges. What is the one-word difference in *where* the container is that separates them?
5. Name the five `DimCustomer.CustomerSegment` values and, for any two of them, state what each one actually optimises for.
6. Why can rising D&D revenue be a bad sign rather than a good one?

## Concept

### Why codes are a modelling problem, not a memorisation problem

Every code system in this dataset exists because two organisations that don't share a database still need to agree, unambiguously, on what a thing *is* — a port, a vessel, a box, a commodity, a carrier, a risk boundary, an event. A code is a compression scheme for a fact that would otherwise need a paragraph. Your job as a modeller isn't to memorise every code — it's to know *what structure the code encodes*, because that structure tells you what you can validate, what you can derive, what will break if you parse it wrong, and — critically — what a check digit is protecting you against. A check-digit failure on a container number isn't a curiosity; it's the difference between charging the right customer's account and charging a stranger's.

### 1. UN/LOCODE — where a place is, compressed into five characters

`DimLocation.LocationCode` is a 5-character UN/LOCODE: **2 letters for country** (ISO 3166-1 alpha-2) + **3 letters for the location** within that country, assigned by national authorities under UN/CEFACT convention. `INNSA` = `IN` (India) + `NSA` (Nhava Sheva / Jawaharlal Nehru Port). `CNSHA` = `CN` + `SHA` (Shanghai). `USLAX` = `US` + `LAX` (Los Angeles).

The modelling implication: **the first two characters are a free, embedded country code.** You never need a separate lookup to know `INNSA` is in India — you can derive `CountryCode` from `Left(LocationCode, 2)` as a sanity check against `DimLocation.CountryCode`, and if they ever disagree, you've found either a data error or a location that changed sovereignty codes (rare, but it happens in real logistics master data when a UN/LOCODE gets reassigned). This is exactly the kind of derivable-but-also-stored redundancy you'll be asked to validate, not trust blindly, in Day 4's Power Query work.

### 2. IMO numbers — a 7-digit identity with a built-in tamper check

Every registered ship gets a 7-digit **IMO number** that never changes across the vessel's life, regardless of renaming, reflagging, or change of owner — unlike a call sign, which can change. The first six digits are a sequential registration number; the seventh is a **check digit**, computed as follows:

1. Take the first six digits.
2. Multiply them by descending weights **7, 6, 5, 4, 3, 2** (leftmost digit × 7, next × 6, and so on).
3. Sum the six products.
4. The check digit is that sum, **mod 10**.

Worked example — IMO `9319466`:

| Digit | 9 | 3 | 1 | 9 | 4 | 6 |
|---|---|---|---|---|---|---|
| Weight | ×7 | ×6 | ×5 | ×4 | ×3 | ×2 |
| Product | 63 | 18 | 5 | 36 | 12 | 12 |

Sum = 63+18+5+36+12+12 = **146**. 146 mod 10 = **6** — matches the seventh digit of `9319466`. Valid.

`DimVessel.ImoNumber` is generated to pass this test for every one of the 240 vessels. Validation gate #11 in the schema contract exists specifically so that if anyone ever hand-edits or mis-generates a vessel record, the check-digit test catches it before it reaches a report — the same logic you're about to apply, by hand, in today's drill.

### 3. ISO 6346 — the container number, anatomised

This is the one you need to be able to *implement*, not just recognise, because container-number validation is a genuinely common real-world data-quality gate (EDI feeds, terminal systems, and customer portals all mis-key container numbers, and a bad check digit is how you catch it before it corrupts a report).

**Anatomy — 11 characters, four parts:**

| Part | Length | Content |
|---|---|---|
| Owner code | 3 letters | Registered with the BIC (Bureau International des Containers), identifies the leasing/owning entity |
| Equipment category identifier | 1 letter | `U` = freight container (what you'll see nearly everywhere in this dataset), `J` = detachable freight-container-related equipment, `Z` = trailer/chassis |
| Serial number | 6 digits | Owner-assigned, uniquely identifies the box within that owner's fleet |
| Check digit | 1 digit | Computed from the preceding 10 characters |

So `CSQU3054383` decomposes as owner `CSQ`, category `U`, serial `305438`, check digit `3`.

**The check-digit algorithm — implementable in five lines of logic:**

1. **Letter-to-number mapping.** Assign A=10, and continue upward through the alphabet, **skipping every value that is a multiple of 11** (so 11, 22, 33 are never assigned to a letter): A=10, B=12, C=13, D=14, E=15, F=16, G=17, H=18, I=19, J=20, K=21, L=23, M=24, N=25, O=26, P=27, Q=28, R=29, S=30, T=31, U=32, V=34, W=35, X=36, Y=37, Z=38.
2. **Take the first 10 characters** (the 4 letters + the 6 serial digits) and convert each to its numeric value (digits stay as themselves).
3. **Multiply each of the 10 values by 2 raised to its position**, position 0 for the leftmost character up to position 9 for the tenth character: value × 2⁰, value × 2¹, … value × 2⁹.
4. **Sum the 10 products.**
5. **Divide by 11.** The remainder is the check digit — **unless the remainder is 10, in which case the check digit is 0** (there is no single digit for "10").

Worked example — `CSQU305438` (10 characters, check digit still to be found):

| Position | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Char | C | S | Q | U | 3 | 0 | 5 | 4 | 3 | 8 |
| Value | 13 | 30 | 28 | 32 | 3 | 0 | 5 | 4 | 3 | 8 |
| Multiplier (2^pos) | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 |
| Product | 13 | 60 | 112 | 256 | 48 | 0 | 320 | 512 | 768 | 4096 |

Sum of products = **6,185**. 6,185 ÷ 11 = 562 remainder **3**. Check digit = **3**. Full number: **CSQU3054383** — matches.

Python reference (you will write this yourself in the drill, this is here to check your work against, not to copy before you try):

```python
LETTER_VALUES = {}
_v = 10
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    while _v % 11 == 0:
        _v += 1
    LETTER_VALUES[ch] = _v
    _v += 1

def iso6346_check_digit(ten_chars: str) -> int:
    total = 0
    for i, ch in enumerate(ten_chars.upper()):
        value = LETTER_VALUES[ch] if ch.isalpha() else int(ch)
        total += value * (2 ** i)
    remainder = total % 11
    return 0 if remainder == 10 else remainder
```

Every `FactContainerMove.ContainerNo` in this dataset is generated to pass this exact test (validation gate #10). A container number that fails it isn't "probably fine, close enough" — it's either a typo somewhere upstream or a sign your parsing logic split the string wrong (off-by-one on where the check digit starts is the single most common implementation bug here).

### 4. Container size and type codes

`DimEquipment.IsoSizeTypeCode` is a 4-character ISO 6346 size/type code, distinct from the 11-character container *serial* number above — this code describes the **class of box**, not one specific physical unit. Structure: **character 1** = length code, **character 2** = height code, **characters 3–4** = type group + variant.

Two fully worked examples from the contract's own sample values:

- **`22G1`**: `2` = 20-foot length, `2` = 8'6" standard height, `G1` = general-purpose, closed, standard ventilation. This is a standard 20-foot dry van.
- **`45R1`**: `4` = 40-foot length, `5` = 9'6" high-cube height, `R1` = mechanically refrigerated, one specific ventilation/insulation variant. This is a 40-foot high-cube reefer.

Notice `DimEquipment` also carries a second, friendlier column, `EquipmentTypeCode` (`20DV`, `40HC`, `20RF`, `40OT`, and so on). This is not redundant duplication to be collapsed — it's the same pattern you'll see everywhere in logistics data: **one column is the interoperable code** (understood by terminals, shipping lines, EDI feeds worldwide, governed by an external standard you don't control) **and a second column is the business-friendly label** (governed by Meridian, meaningful to anyone reading a report without decoding ISO structure). Never assume you can derive one perfectly from the other with a simple formula — build the mapping table and validate it, because the friendly label is a business decision, not a mechanical transformation.

### 5. HS codes — why 6 digits is a promise and 8–10 digits is not

The Harmonized System (HS) is a hierarchy, and the depth of that hierarchy is where an important modelling trap lives:

| Level | Digits | Governed by | Example |
|---|---|---|---|
| Chapter | 2 | World Customs Organization (WCO), international | `84` — Machinery |
| Heading | 4 | WCO, international | `8471` — Automatic data processing machines |
| **Subheading** | **6** | **WCO, international — the last globally harmonised level** | `847130` — Portable digital ACP machines ≤10kg |
| Tariff line | 8–10 | **National customs authority** — different in every country | India's 8-digit extension vs. the US's 10-digit Schedule B/HTS |

`DimCommodity.HsCode6`, `HsCode4`, `HsCode2` stop deliberately at the 6-digit level, because that's the deepest level guaranteed to mean the same thing in every country in the dataset. **This is why 6 digits is the safe join key across a global dataset and 8–10 digits is not**: two countries' 8-digit extensions of the same 6-digit subheading can classify genuinely different sub-products, apply different duty rates, and are not comparable across borders without a country-specific concordance table. If you ever see an analysis that joins customs data from two countries on an 8-digit HS code without first truncating to 6, treat the output as suspect until proven otherwise.

### 6. SCAC — a 2–4 letter carrier code, and a trap to avoid

The Standard Carrier Alpha Code (SCAC), originally a US trucking-industry registry (administered by NMFTA) and now used far more broadly across modes for EDI identification, is how you say "which carrier" in two to four letters. Meridian's own is `MGLU`. `DimCarrier.CarrierCode` is "SCAC-style" for every carrier in the dataset.

The trap: a SCAC and a container **owner code** (the first 3 letters of `ContainerNo`, registered separately with the BIC) look superficially similar — both are short letter codes identifying a logistics company — but **they are two different registries with no guaranteed relationship.** Meridian's SCAC is `MGLU`; Meridian's container owner code could coincide with that or not, because container ownership (who owns the physical box, possibly a leasing company) and carrier operation (who runs the vessel service) are legally and commercially separate facts. Never assume `Left(ContainerNo, 4) = CarrierCode` — that's a join you have to test, not assume.

### 7. Incoterms 2020 — a decision table, not a list

Eleven rules, in four groups, and the question you're actually answering with an Incoterm is always the same one: **at what point does risk of loss or damage pass from seller to buyer, and who arranges/pays for what up to that point?** Cost allocation and risk transfer are *not always the same point* — CIF is the textbook case: the seller pays freight all the way to the destination port, but risk passes to the buyer the moment the goods are loaded on board at origin. Read the table as a decision tool: find your row by asking "who's arranging the main carriage" and "where does risk end for the seller," not by trying to memorise eleven definitions in isolation.

| Code | Group | Sea/waterway only? | Risk transfers to buyer at | Who arranges main carriage | Who insures |
|---|---|---|---|---|---|
| **EXW** | E | No | Seller's premises, goods made available | Buyer | Buyer's choice |
| **FCA** | F | No | Handover to the carrier nominated by the buyer | Buyer | Buyer's choice |
| **FAS** | F | **Yes** | Goods placed alongside the vessel at the port of shipment | Buyer | Buyer's choice |
| **FOB** | F | **Yes** | Goods on board the vessel at the port of shipment | Buyer | Buyer's choice |
| **CFR** | C | **Yes** | Goods on board the vessel at the port of shipment (same as FOB — seller still pays freight onward) | Seller | Buyer's choice |
| **CIF** | C | **Yes** | Goods on board the vessel at the port of shipment | Seller | **Seller — minimum cover only** (Institute Cargo Clauses C) |
| **CPT** | C | No | Handover to the first carrier | Seller | Buyer's choice |
| **CIP** | C | No | Handover to the first carrier | Seller | **Seller — all-risk cover** (Institute Cargo Clauses A — this is a genuine 2020 upgrade from 2010, where CIP only required minimum cover like CIF still does) |
| **DAP** | D | No | Destination, goods ready for unloading, not yet unloaded | Seller | Buyer's choice |
| **DPU** | D | No | Destination, **after** unloading (replaced "DAT" from Incoterms 2010) | Seller | Buyer's choice |
| **DDP** | D | No | Destination, duties paid, ready for unloading | Seller | Buyer's choice |

Two things worth committing to memory precisely because they're common interview questions:

- **The four sea/waterway-only terms are FAS, FOB, CFR, CIF** — every other term is "any mode," meaning it works for air, road, rail, multimodal, or sea. This maps directly to `DimIncoterm.ModeApplicability` ("Sea and Inland Waterway" for those four, "Any Mode" for the other seven).
- **CIF and CIP diverge on insurance level, not just on whether main carriage is unpaid vs paid-to-destination.** Under CIF the seller only has to buy minimum cover; under CIP the seller must buy all-risk cover. A buyer relying on a CIF seller's insurance is carrying more residual risk than a buyer relying on a CIP seller's, even though both look superficially like "seller pays for insurance."

Validation gate #9 requires all 11 Incoterms to appear somewhere in `FactShipment` — meaning your model needs to handle every row in this table correctly, not just the two or three you'll see most often (FOB and CIF dominate ocean freight in practice, but DAP and DDP show up wherever Meridian's customers want door delivery).

### 8. DCSA milestones — three journeys, three classifiers

The Digital Container Shipping Association (DCSA) — a carrier-led standards body — defines a common event model so that "the container gated in" means the same thing whether it comes from Meridian's own system or a customer's third-party tracking dashboard. Two structural ideas matter more than any individual event name:

**Three journeys** (`DimMilestone.EventJourney`):

- **Equipment journey** — events that happen *to the box itself*, independent of any specific commercial shipment: gate-in, gate-out, empty pickup, empty drop-off, stuffing, stripping. A repositioning move (no `ShipmentKey`) still generates equipment-journey events.
- **Transport journey** — events that happen *to the vessel/voyage*: arrival, departure, load, discharge, waypoint. These are shared across every container on that voyage — one vessel arrival event is relevant to potentially thousands of boxes at once.
- **Shipment journey** — events that happen *to the commercial transaction*: booking confirmed, documents issued, documents surrendered, customs cleared, approved/rejected. These attach to the house bill, not to any individual physical box.

**Three classifiers** (`DimMilestone.EventClassifier`): **Planned** (schedule-driven, known before the fact — a sailing schedule's port call), **Estimated** (a live forecast that can and does change — a revised ETA), **Actual** (has definitively happened, immutable once recorded). The single most valuable thing this distinction buys you: you can measure *forecast accuracy* by comparing Estimated against Actual for the same milestone — which is exactly what `FactPortCall.PromisedEtaDateKey` (never revised) vs `RevisedEtaDateKey` vs `AtaDateKey` lets you do in Week 3.

Why this matters for a job interview, not just this course: a real employer's system almost certainly ingests DCSA-aligned event feeds from multiple counterparties (terminals, other carriers in an alliance, customs brokers) — knowing that "equipment," "transport" and "shipment" are the three lanes those events travel down, and that a milestone's classifier tells you whether you're looking at a promise, a prediction, or a fact, is the difference between sounding like you've read a glossary and sounding like you've actually worked with the data.

### 9. EDIFACT — what a message type tells you about where the data comes from

`DimMilestone.EdifactMessageType` isn't decoration — in a real operational environment, it tells you **which system and which counterparty** actually produced that milestone update, because each EDIFACT message type is generated by a specific party at a specific point in the process:

| Message | Full meaning | Who sends it, and what its existence implies |
|---|---|---|
| **IFTMIN** | Instruction message | Sent by the party giving forwarding/transport instructions (often the shipper or their forwarder) to the party arranging carriage — this is upstream of any carrier confirmation. If a milestone's data source is IFTMIN, expect it before a booking is even firm. |
| **IFTMBF** | Firm booking message | The carrier's confirmation of a booking. If you see this as the source, the booking has moved from a request to a commitment — this is your `BookingStatus = 'Confirmed'` moment, structurally. |
| **IFTSTA** | International multimodal status report message | The general-purpose "here's what happened / here's the current status" feed — this is the message type behind most transport-journey status milestones (loaded, departed, arrived) that get pushed to customer tracking portals. |
| **CODECO** | Container gate-in/gate-out report message | Sent by a terminal or depot confirming a container was physically delivered or picked up. If a milestone's source is CODECO, the data is coming from a *terminal system*, not from Meridian's own booking or vessel-ops systems — which matters enormously if you're ever debugging why a gate event is late or missing (the fault may not be Meridian's at all). |
| **COPARN** | Container announcement message | An order to release, make available, or announce the impending arrival of containers — typically the message that tells a depot "expect this box" or "this box is now available for pickup." |
| **BAPLIE** | Bayplan/stowage plan (occupied and empty locations) message | The vessel's stowage plan — which bay, row and tier every container sits in. If a milestone is tied to BAPLIE, it's describing a *loading/discharge sequencing* fact, not a commercial or gate event — this is the message type that answers "where exactly on the ship is this box." |

The practical takeaway, stated plainly: **the presence of `EdifactMessageType = 'CODECO'` on a milestone tells you that in a live system, a delay or error there is a terminal-side data-quality problem you'd have to escalate externally, not a bug in Meridian's own pipeline.** That distinction — "is this our data or someone else's data arriving through a standard interface" — is a genuinely senior-analyst instinct, and it's one your interviewer can test for directly by handing you a made-up integration problem and watching whether you ask "which system does this milestone actually come from?"

## Drill

**1. Implement and test the ISO 6346 check digit (20 min).** Write the Python function `iso6346_check_digit(ten_chars)` (or your own version of the algorithm — the reference above is there to check against, not copy blind) and test it against three cases: (a) `CSQU305438` → confirm it returns `3`; (b) `MSCU6639871` — treat the first 10 characters as the input and confirm whether the given 11th-character check digit is valid; (c) invent your own 10-character owner+category+serial string and compute its check digit by hand *and* by code, confirming they match. Done = working function, all three cases resolved, and your by-hand working shown for (c).

**2. IMO check digit, by hand (10 min).** Vessel `DimVessel` candidate IMO number `9247398` — verify the check digit using the weighted-sum method. Show the six products and the final mod-10 step. Done = a clear PASS/FAIL verdict with working shown.

**3. HS code truncation and the join trap (15 min).** `DimCommodity` contains an `HsCode6` value of `851712` (a plausible telecom-equipment subheading). State the derived `HsCode4` and `HsCode2`. Then answer: an Indian customs extract carries `85171210` and a US customs extract carries `85176200` for what someone claims is "the same product line" — using only the HS hierarchy rule from §5, explain precisely why you cannot assume these two rows describe the same product, and what the *one* level at which you could safely compare them. Done = both truncations stated correctly, and a two-to-three sentence explanation of the join trap.

**4. Incoterms decision table applied (10 min).** A Meridian customer ships FCL cargo where: Meridian's booking desk arranges the vessel and pays ocean freight through to the destination port, but the customer's own broker arranges and pays for cargo insurance, and risk passes to the buyer the moment the container is loaded on board at origin. Using the decision table in §7 (not memory), identify the one Incoterm code that fits all three facts and state which one fact would change if it had instead been CIF. Done = correct code named, with the CIF contrast stated correctly (insurance arrangement, not risk point).

**5. DCSA journey classification (5 min).** Classify each of these `DimMilestone.EventCode` values into Equipment / Transport / Shipment journey, with a one-clause reason: `GTIN` (gate in), `ARRI` (vessel arrival), `CONF` (booking confirmed), `STRP` (stripping). Done = all four classified with a reason each.

## Ship

Create `notes/week1/day2-code-systems.md` in your own repo containing:
1. Your working `iso6346_check_digit` function (Drill 1), with the three test cases and their results.
2. The IMO check-digit working from Drill 2.
3. The Incoterms decision table, redrawn in your own words, with the E/F/C/D groups and the four sea-only codes highlighted.

Commit with:

```
git add notes/week1/day2-code-systems.md
git commit -m "day2: code systems — ISO 6346 + IMO check digits, Incoterms decision table"
```

## Log

- **What clicked**: which check-digit algorithm made sense once you traced it by hand, that didn't from just reading the rule?
- **What did not**: which code system are you still not confident you could explain cold — UN/LOCODE, HS hierarchy, DCSA journeys, or EDIFACT message types?
- **What to re-ask tomorrow**: one question to carry into Day 3's dimensional-modelling session, especially anything about *why* a code needs its own dimension table versus living as an attribute.

## Exit criteria

- [ ] `iso6346_check_digit` implemented, tested against three cases, and matches expected results.
- [ ] IMO check digit verified by hand for the given number, with working shown.
- [ ] HS code truncation drill answered and the 6-digit-vs-8/10-digit join trap explained correctly.
- [ ] Incoterms decision table applied correctly to the scenario in Drill 4.
- [ ] DCSA journey classification completed for all four event codes.
- [ ] `day2-code-systems.md` committed to your own repo.
- [ ] You can state, without looking, why 6 digits is the safe HS join key and 8–10 digits is not.
- [ ] Log entry written.
