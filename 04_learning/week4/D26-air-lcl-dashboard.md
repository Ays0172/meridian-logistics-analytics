# Day 26: The Air & LCL Dashboard

> Time: 3 h · Spaced recall 10 min · Concept 40 min · Drill 85 min · Ship 30 min · Log 15 min

Page 4, the smallest domain (9 KPIs) and the one with the most conceptually
dangerous unit-conversion traps in the whole dictionary: three different
chargeable-weight rules (air 1:6000, air 1:5000, ocean LCL 1:1000) that look like
variations on one idea and are not. This page's job is commercial, not
operational: is a lane priced and routed on the right mode, and is the forwarding
desk converting quotes into bookings.

---

## Spaced recall (10 min, closed book)

1. State the pooled formula for `Yield per kg` and why the naive `AVERAGEX`
   version over-weights small shipments.
2. Name the three chargeable-weight conventions in this dataset and their
   divisors/equivalences. Which two are most often confused, and why?
3. What is `ALC.SLS.CONV` actually measuring, and what real-world conversion rate
   does it structurally understate (per the KPI dictionary's own Gaps note)?
4. From Day 24: what visual pattern did the Landside page use to make a
   reconciliation check visible rather than asserted? Where does an analogous
   opportunity exist on this page?
5. Why does `ALC.CST.MODAL`'s watch-out say to restrict the air-vs-ocean cost
   comparison to LCL and air, excluding FCL?

---

## Concept

### This page's one job

*Is this lane priced and routed on the right mode, and is the desk converting
quotes into bookings.* Two different questions, both commercial, both belonging on
one page because a forwarding desk reviews them together in the same conversation:
mode economics first, then sales execution.

### The visuals, and what each is for

| # | Visual | Measure(s) | Chart type | Decision it supports |
|---|---|---|---|---|
| 1 | Header cards | `Yield per kg`, `Quote-to-Book Conversion`, `Gross Profit per House Bill` | Cards | Five-second commercial read. |
| 2 | Air vs. Ocean modal comparison | `Air vs Ocean Cost Index`, `Ocean vs Air Transit Index` | Paired index bars, by lane | The core "which mode" decision, cost multiple next to speed multiple so neither is read in isolation. |
| 3 | Chargeable weight mix | `Chargeable Weight kg (Air 1:6000)`, `(Air 1:5000)`, `Revenue Tons (LCL)` | Donut, segmented by rule, never summed across rules | Which billing convention actually governs this book's volume, and a running visual reminder that the three are not interchangeable. |
| 4 | Yield per kg, by lane, with peak-season overlay | `Yield per kg` | Bar with a peak-season index reference line (1.35x baseline) | Is a lane's current yield in line with seasonal expectation or a genuine rate move. |
| 5 | Volumetric-driven share trend | `Volumetric-Driven Shipment Share` | Line, by mode | Is the book shifting toward space-constrained (cbm-priced) or weight-constrained cargo, a pricing-strategy signal. |
| 6 | Quote-to-book conversion trend | `Quote-to-Book Conversion` | Line, labelled explicitly as a booking-stage proxy | Sales execution trend, with the honest caveat attached every time it's shown. |

### Why the cost index and transit index are paired, never shown alone

`ALC.CST.MODAL` and `ALC.TRN.MODAL` answer two halves of the same commercial
question: air costs roughly 4-8x ocean per kg, and ocean typically runs 4-10x
longer than air on the same lane. Shown alone, the cost index argues for ocean on
every lane; shown alone, the transit index argues for air on every lane. Shown
together, as paired bars per lane, a reader can actually reason about the
trade-off a shipper is making - which is the entire point of this KPI existing.
This directly extends Day 23's and Day 25's running rule: a ratio's watch-out in
the KPI dictionary almost always translates into "pair this visual with its
counterpart," not "trust this number alone."

### The chargeable-weight donut, and the trap it exists to prevent

Three conventions live in this dataset and they are structurally different, not
three flavours of one idea:

| Convention | Formula | When it applies |
|---|---|---|
| Air 1:6000 | `MAX(GrossWeightKg, VolumeCbm x 1,000,000 / 6,000)` | IATA-standard air cargo |
| Air 1:5000 | `MAX(GrossWeightKg, VolumeCbm x 1,000,000 / 5,000)` | Carrier-specific air variant; bulkier cargo charged more than under 1:6000 |
| Ocean LCL 1:1000 | `MAX(WeightKg / 1000, VolumeCbm)` | LCL, a flat tonne-for-cbm equivalence, no divide-by-thousands step at all |

The KPI dictionary calls the air-vs-ocean confusion "the single most common
cross-mode confusion at an entry-level rating desk," because all three "look like
a number you divide volume by" while encoding densities that differ by a factor of
five to six. The donut's job is not decoration: segmenting by rule, with the
segments never summed into one blended "chargeable weight" total, is a standing
visual reminder that a yield-per-kg figure computed across mixed rules is
uninterpretable, exactly as the dictionary's watch-out for `ALC.REV.YIELDKG`
states.

### The conversion-rate caveat, shown every time

`Quote-to-Book Conversion` is a **booking-stage proxy** - `FactBooking` is the only
table carrying `QuoteKey`, and every row in it already reached the booking stage,
so a quote that was requested and never came back at all is invisible to this
measure by construction. The real top-of-funnel conversion rate is lower than what
this KPI can show. Rather than bury that caveat in a tooltip a reader may never
open, put the word "proxy" directly in the visual's title and axis label - the same
philosophy as naming a naive measure `[DO NOT USE]` in `_Measures`: a caveat that
depends on a reader clicking something to find it will eventually get dropped from
someone's screenshot in a deck.

### Filters on this page

`Period` and `TradeRegion` sync in. Add `Mode` (Air/Ocean-LCL) as page-specific -
this is the one page besides Ocean Liner where Mode is meaningful, per Day 22's
audit - plus a `ChargeableWeightRule` slicer, since several visuals here
specifically require segmenting by rule to stay interpretable.

---

## Drill

### Exercise 26.1: the paired modal comparison (25 min)
Build visual #2. Predict, before checking, which lane in your data shows the
*largest* gap between its cost-index rank and its transit-index rank (i.e. a lane
where the mode choice isn't obviously dominated by one factor). Verify and write
one sentence on what that lane's shippers are actually trading off.

### Exercise 26.2: the chargeable weight donut (20 min)
Build visual #3 with the three rule segments. Then deliberately build a "wrong"
version that sums all three rules into one blended chargeable-weight total and a
naive yield-per-kg on top of it. Compare the blended yield figure to the properly
segmented `Yield per kg (Air only)`. State the direction and rough size of the
distortion, and which single line in the KPI dictionary's watch-out predicted it.

### Exercise 26.3: volumetric share trend (20 min)
Build visual #5. Predict whether your data shows a rising, falling, or flat
volumetric-driven share over the period covered, before checking. If rising, write
one sentence on what that implies for whether pricing strategy on that mode should
shift toward cbm-based rating, per the KPI dictionary's own note.

### Exercise 26.4: conversion proxy, labelled honestly (20 min)
Build visual #6 with "proxy" explicitly in the title. Then write, in your own
words, the one sentence you would say out loud in a room if a commercial director
asked "so is 42% our real win rate?" - your answer should name specifically what
the number does and does not capture.

---

## Ship

Build page `4 Air & LCL` with all six visuals, on-theme, nav bar intact, both the
chargeable-weight donut and the conversion-rate label explicitly caveated in the
visual itself, not only in a tooltip.

```
git add .
git commit -m "Day 26: Air & LCL dashboard, chargeable-weight and conversion caveats wired"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Page `4 Air & LCL` exists with all six visuals, on-theme, nav bar intact.
- [ ] Cost index and transit index are shown paired, never as standalone visuals.
- [ ] The chargeable-weight donut segments by rule and you built (and can explain)
      the distortion from wrongly blending the three rules together.
- [ ] `Quote-to-Book Conversion` is labelled "proxy" directly in the visual, and
      you can explain in one sentence what real conversion it cannot see.
- [ ] Volumetric-driven share trend built and read correctly against your data.
