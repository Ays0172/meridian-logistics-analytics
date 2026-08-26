# Day 1 — Solutions

## Spaced recall (baseline diagnostic answers)

1. **Primary vs foreign key.** A primary key uniquely identifies a row in its own table (no duplicates, never blank). A foreign key is a column in one table that holds the value of another table's primary key, creating the link between them — it can repeat, and it can legitimately be blank/unknown depending on the model's rules. Meridian's convention: surrogate primary keys are named `<Table>Key` (e.g. `CustomerKey`), and the same name is reused as the foreign key on any fact table that references that dimension.
2. **The arrowhead.** The relationship line tells you two tables are joined; the arrowhead tells you which direction filters *propagate*. A single arrowhead means filtering the "one" side filters the "many" side automatically, but not the reverse, unless you change cross-filter direction. This is filter context, not just "which tables are connected" — connection and propagation direction are two different facts about the same line.
3. **Grain** (or "level of detail" / "level of granularity"). Whatever attribute(s) you group by define the grain of the visual's result — here, one row per customer, even though the underlying fact table is at a much finer grain (one row per transaction).
4. **Calculated column vs measure.** A calculated column is computed once, at data-refresh time, for every row, and stored in the model (it takes memory, and it doesn't respond to slicers). A measure is computed at query time, in the current filter context, every time a visual renders — it takes no storage, but it costs CPU on every interaction. Rule of thumb: if the answer should change when a slicer changes, it's a measure; if it's a fixed per-row attribute, it's a column.
5. **First suspect: the relationship, not the DAX.** Wrong totals after adding a slicer are the single most common symptom of a broken or missing relationship path — an inactive relationship, a relationship going the wrong direction, ambiguity from more than one active path, or the slicer's table not actually being connected to the table the measure reads from. Check the model view before you re-read a single line of DAX.
6. **Wide, one-row-per-transaction tables are the wrong shape to filter/group by** because: (a) the same customer's name is repeated on every one of their transaction rows, wasting memory and inviting inconsistent spellings of the same value; (b) you can't cleanly ask "how many distinct customers" without extra logic; (c) any attribute you'd want to slice by (region, segment, tier) has to be repeated on every transaction row too, and if that attribute *changes over time* (an account manager reassignment, say) a flat transactional table has no clean way to represent "as of when." This is the entire motivation for splitting attributes into a separate dimension table — which is exactly Day 3's subject.

If you got 4–6 right: good baseline, the programme will sharpen rather than introduce. If you got 0–3 right: that's expected for "some Power BI, weak modelling" — Days 3 and 5 are built for you specifically, don't panic.

---

## Drill 1 — Chain and cardinality

(a) **One** `FactBooking` row. A booking, however it's eventually fulfilled, is one row at booking grain — the LCL consolidation happens downstream of the booking, not within it.

(b) **One** `FactShipment` row — the house bill issued to this specific SME shipper for their portion of the consolidated container. The forwarder's/NVOCC's consolidation activity doesn't multiply this shipper's own house bill; it only affects how many *other* house bills share the same physical box.

`HouseBlNo` and `MasterBlNo` are **different** values. Because this cargo is LCL and consolidated by a forwarder acting as an NVOCC, the SME's house bill is issued by the forwarder, while the master bill for the underlying container is issued by Meridian to the forwarder/NVOCC entity. If this were a straightforward BCO FCL shipment with no intermediary, house and master could coincide — but the scenario explicitly states consolidation by a forwarder into a shared container, which is the textbook NVOCC-split pattern from §3.

(c) **Three** other house bills share that `MasterBlNo` — the scenario states cargo "from three other shippers" sharing the same 40' box, so four house bills in total sit under the one master bill (this shipper's plus three others).

(d) `DimMode.ModeCode = 'LCL'` — explicitly stated as consolidated cargo sharing a container, the defining feature of LCL (`IsConsolidated = 1`), as opposed to FCL where one shipper's cargo fills the box alone.

**Why this is the drill it is:** the trap most learners fall into is assuming "one booking, one shipment" always means house and master bill are the same thing. They coincide only when there's no intermediary consolidating multiple shippers into one box. The moment you see "consolidated," "forwarder," "NVOCC" or "shared container" in a scenario, house ≠ master is the default assumption until proven otherwise.

## Drill 2 — Actor incentives

**Most likely segment: NVOCC** (Freight Forwarder acting in an NVOCC-like capacity is a defensible second answer, but NVOCC is the cleanest fit).

Justification, using at least two of the four data points:

- **High volume + thin `GrossMarginPct` per shipment** is the classic NVOCC economic signature: they make money on the *spread* between the wholesale rate they negotiate with Meridian and the retail rate they charge their own downstream shippers, applied across large volume — not on a fat margin per box. A BCO wouldn't show up in Meridian's `GrossMarginPct` at all in the same way, because Meridian's margin on a BCO's shipment reflects Meridian's own cost structure, not a resale spread; an NVOCC's low margin-per-shipment-to-Meridian is compatible with the NVOCC *itself* still being highly profitable one layer downstream, which Meridian's data can't see.
- **Bookings spread across four different carriers in one quarter** fits an NVOCC (or forwarder) far better than a BCO. A BCO typically has a single supply chain to manage and tends to concentrate volume with carriers who service their specific trade lane reliably. An entity spreading volume across multiple carriers in the same period is behaving like a capacity *reseller* — booking wherever the rate and space are best that week, which is exactly the NVOCC/forwarder playbook, not a manufacturer's.

**Why "healthy" and "low margin" are not in tension for this segment:** the account manager is (correctly, if this is read right) evaluating the relationship on volume, retention and reliability of pipeline — the things that matter to Meridian's own planning — not on per-shipment margin, because per-shipment margin was never going to be the NVOCC relationship's value driver. A low margin-per-shipment NVOCC that reliably delivers large predictable volume every quarter can be a far more valuable account than a high-margin, unpredictable SME. The mistake would be reading "low margin" in isolation as "underperforming account" without checking volume and consistency — the account manager's "healthy" call is about the whole relationship, and the data supports it rather than contradicting it.

## Drill 3 — Demurrage, day by day

Free time is 5 days; the container sits **9 calendar days past the last free day** (i.e., 9 chargeable days, all of which are inside the tier structure that starts counting from day 1 *past* free time).

| Days past free time | Tier | Rate/day | Days in this tier | Subtotal |
|---|---|---|---|---|
| 1–5 | Tier 1 | $35 | 5 | $175 |
| 6–9 | Tier 2 | $55 | 4 | $220 |

**Total demurrage: $175 + $220 = $395** for the 9 days.

Two things to check your own working against:

1. The container never reaches tier 3 (day 11+), because it only accrued 9 days past free time — a common error is assuming "9 days" automatically triggers all three tiers, or misreading the tier boundaries as calendar days from stuffing rather than days *past free time*.
2. The single most common wrong answer here is a flat calculation: 9 days × $55 (picking one rate and applying it to everything) = $495, or 9 × $35 = $315. Both are wrong because the tiering is designed to escalate — the whole commercial point of tiered D&D is that day 9 should cost more than day 1, and a flat-rate calculation erases that signal entirely. If you got $495 or $315, re-read §6 before Day 6, because the SCD2 and tiered-logic pattern of "the rate depends on where in a range you are" recurs there too.

## Drill 4 — The load factor question

A defensible three-sentence answer:

> This is primarily a structural problem, not a sales execution failure: Rotterdam-to-Asia is a backhaul leg, and the contract's own target band puts backhaul load factor at 55–70% against a headhaul band of 88–96%, so 61% is within the expected structural range rather than an anomaly to "fix." The lever that actually exists here isn't harder selling on this specific leg — it's aggressive spot pricing to fill whatever incremental volume is available (since an empty repositioning move costs money regardless, any revenue-bearing backhaul cargo, even at ~0.52× headhaul revenue per FFE, is better than sailing empty), combined with tracking whether 61% is *worse than this lane's own historical backhaul average*, which is the only fair benchmark. Setting a target of "fix it to 88% by Q3" misapplies a headhaul expectation to a backhaul lane and will produce either false alarm or, worse, pressure to discount so heavily that the marginal cargo actively loses money to carry.

Partial credit if your answer identifies "structural, not sales" and names pricing/repositioning economics as the real lever — the exact wording doesn't need to match.
