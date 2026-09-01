# Day 25: The Warehouse & Inventory Dashboard

> Time: 3.5 h · Spaced recall 10 min · Concept 45 min · Drill 95 min · Ship 30 min · Log 15 min

Page 3, and the busiest KPI domain (18 of the 72). This page has to answer a
sharper question than "is the warehouse doing well": **is a given site's problem a
people problem (labour, quality) or a stock problem (inventory, obsolescence)?**
Those two failure modes have completely different fixes - training and staffing on
one side, purchasing and demand planning on the other - so the page is built in two
visibly separate halves rather than one undifferentiated KPI wall.

---

## Spaced recall (10 min, closed book)

1. State the multiplicative decomposition of OTIF and the arithmetic-mean mistake
   it corrects for. Quote the actual DIF/DOQ/DOT figures and the resulting gap
   between the naive and correct headline.
2. What sentinel value does `Avg Dock-to-Stock Minutes` need to filter out, and
   what happens to the average if you forget?
3. From Day 13: why is `DimSku[AbcClassStatic]` (the seeded class) expected to
   disagree with a dynamic ABC reclassification, beyond "the business changed"?
4. State the pooled formula for `Lines per Labour Hour` and the naive alternative
   Day 9 measured a ~22% error for.
5. Why is `WHS.UTL.PALLET`/`WHS.UTL.CUBE` described as semi-additive over date, and
   what does that forbid you from doing when trending them across a month?

---

## Concept

### This page's one job

*Is a given site losing service or money, and is the cause a people problem or a
stock problem.* The page's layout should make that split visible before a reader
reads a single number: a "People & Process" zone (labour productivity, pick
accuracy, dock-to-stock, order cycle time) and an "Inventory" zone (turns, ABC mix,
shrinkage, obsolescence), with OTIF sitting at the top as the shared headline both
zones ultimately explain.

### The visuals, and what each is for

| # | Visual | Measure(s) | Chart type | Decision it supports |
|---|---|---|---|---|
| 1 | Header cards | `OTIF %`, `Inventory Accuracy %`, `Pick Accuracy %`, `Inventory Turns` | Cards | Five-second read across both zones. |
| 2 | OTIF decomposition | DIF, DOQ, DOT, and the compound `OTIF %` | Waterfall or three-segment bar, plus the naive arithmetic-mean comparison alongside it | Makes the compounding effect visible instead of asserted - the page's version of Day 23's congestion callout. |
| 3 | Lines per Labour Hour, by role/tenure band | `Lines per Labour Hour` | Small multiples, one per `RoleName`/`TenureBand` | Is a productivity gap a site-wide issue or concentrated in one role/tenure segment (new agency staff, night shift). |
| 4 | Dock-to-Stock distribution | `Avg Dock-to-Stock Minutes` | Histogram, `-1` sentinel excluded, target band shaded | Where receiving-to-available delay actually concentrates, not just the average. |
| 5 | ABC value share vs. SKU count share | `Value Share by ABC Class` | 100%-stacked bar, value share and count share side by side | The Pareto check: is value concentrated the classic ~80/15/5 way, and where does it diverge from `AbcClassStatic`. |
| 6 | Inventory Turns / Days on Hand, by warehouse | `Inventory Turns`, `Days on Hand` | Bar, dual-axis or paired | Which sites are carrying too much stock relative to throughput. |
| 7 | Shrinkage & Obsolete Stock trend | `Shrinkage Rate`, `Obsolete Stock Ratio` | Two lines, shared axis | Quality/loss trend over time, the inventory-zone equivalent of the OTIF trend. |
| 8 | Pallet/Cube utilisation gauge | `Pallet Position Utilisation %`, `Cube Utilisation %` (proxy) | Gauges, target band 80-90% shaded | Space efficiency, labelled clearly since cube is a documented estimate, not an exact figure. |

### The OTIF decomposition callout

This is the page's version of yesterday's and Day 23's "make the trap visible, not
asserted" pattern. The KPI dictionary is explicit that the arithmetic-mean mistake
here is *the single most common OTIF mistake*: averaging three healthy-looking
marginals (DIF ~0.962, DOQ ~0.987, DOT ~0.913) gives ~95.4%, while the correct
multiplicative headline is ~86.7% - an 8.7-point gap purely from the choice of
operator. Build both numbers side by side, not just the correct one alone, because
a stakeholder who has only ever seen someone else's arithmetic-mean version will
find the correct 86.7% "suspiciously low" the first time they see it, and the
comparison is the fastest way to preempt that pushback in the room rather than
after the meeting. Label the naive version explicitly `[DO NOT USE]`, matching the
naming convention Week 2 Day 9 established for exactly this situation.

### Why ABC gets a dual-share visual, not one bar per class

Day 13 built a dynamic ABC reclassification and found it disagreeing with the
seeded `AbcClassStatic` for structural reasons beyond "the business changed":
`AbcClassStatic` is a point-in-time seed, while a dynamic version anchored to a
specific snapshot date reflects only that date's on-hand value, and the two
classify against different populations of "what counts as active." Rather than
pick a side, this page shows **both** the value-share distribution (which should
land close to the classic 70-80/15/20 Pareto split) and, as a secondary cut, the
SKU-count share for the same classes - because a class that holds 78% of value in
just 16% of SKUs is a very different operational story than one holding 78% of
value across 40% of SKUs, and neither figure alone tells you which is true.

### Filters on this page

`Period` and `TradeRegion` sync in. Add `Warehouse` (page-specific, matching Day
22's audit) and an ABC class slicer, since several visuals here specifically need
to be sliceable by class without re-navigating the page.

---

## Drill

### Exercise 25.1: the OTIF comparison visual (30 min)
Build both the naive arithmetic-mean OTIF and the correct multiplicative OTIF as
measures (name the naive one `[DO NOT USE] OTIF % (naive)`), and place them side by
side in a single visual. Predict the gap in percentage points before computing it
against your own data, then compare to the dictionary's documented ~8.7-point gap.

### Exercise 25.2: dock-to-stock histogram, sentinel check (20 min)
Build the histogram twice: once without filtering `DockToStockMinutes <> -1`, once
with it. Predict, before checking, roughly how far the unfiltered average will be
dragged from the filtered one, and in which direction. Note the actual shift.

### Exercise 25.3: Lines per Labour Hour, small multiples (25 min)
Build the small-multiples view by role and tenure band. Predict which segment (per
the KPI dictionary's behavioural spec: night shift, first-six-months agency staff)
will show the lowest productivity before checking, and confirm it is not being
hidden by a site-wide average the way Day 9's naive average would hide it.

### Exercise 25.4: ABC dual-share visual (20 min)
Build the value-share vs. count-share comparison. State, in one sentence, whether
your build's Class A looks closer to "small SKU count, large value share" or
"broad SKU count, large value share," and what that implies for whether a
purchasing team should prioritise SKU-level review or category-level review.

---

## Ship

Build page `3 Warehouse & Inventory` with all eight visuals, laid out in the two
visible zones described above, on-theme, nav bar intact. Add
`[DO NOT USE] OTIF % (naive)` alongside the correct `OTIF %` to `_Measures`,
display folder `03 Warehouse`, exactly matching Day 9's naming convention for
naive variants.

```
git add .
git commit -m "Day 25: Warehouse & Inventory dashboard, OTIF decomposition wired"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Page `3 Warehouse & Inventory` exists with all eight visuals, split visibly
      into people/process and inventory zones.
- [ ] The naive-vs-correct OTIF comparison exists and you can state the gap from
      your own build, plus explain why the naive version is `[DO NOT USE]`-named.
- [ ] Dock-to-stock histogram built both with and without the `-1` sentinel
      filter, and you can state the size and direction of the resulting shift.
- [ ] You can explain, in one sentence, why ABC gets a dual-share visual instead of
      a single bar, referencing Day 13's reclassification disagreement.
- [ ] Small-multiples productivity view confirms (or refutes) the expected
      night-shift/new-agency-staff gap from your own data.
