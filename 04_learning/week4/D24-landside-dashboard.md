# Day 24: The Landside Dashboard

> Time: 3 h · Spaced recall 10 min · Concept 40 min · Drill 90 min · Ship 30 min · Log 15 min

Page 2. Ocean liner's page answered "is the network healthy." Landside's job is
narrower and more commercial: which road/rail carriers earn more freight, and which
get put on notice, at the next carrier review. That means today's page is built
around a ranking, not a trend, even though trends still appear inside it.

---

## Spaced recall (10 min, closed book)

1. State the pooled formula for `Deadhead %` and explain why the naive `AVERAGEX`
   version is wrong (Day 9's trap, restated for a landside metric).
2. What does `LND.SVC.DIFOT`'s definition require you to count that a naive
   "`On-Time %` times `In-Full %`" calculation does not?
3. From Day 22: which two filters sync onto every page, and why does `Carrier` not
   join them?
4. What is `Truck Utilisation %`'s relationship to `Deadhead %`, and why does the
   KPI dictionary insist on computing both independently from `LoadedKm`/`EmptyKm`
   rather than deriving one as `1 -` the other?
5. Name one Day 23 design choice (visual type, not measure) you are reusing on this
   page, and why it transfers.

---

## Concept

### This page's one job

*Which carriers earn more freight next quarter, and which get put on notice.* That
is a ranking decision, made in a recurring carrier review, usually against a
composite scorecard rather than any single KPI - which is exactly why
`LND.CAR.SCORE` exists and why it, not any individual rate or reliability figure,
anchors this page.

### The visuals, and what each is for

| # | Visual | Measure(s) | Chart type | Decision it supports |
|---|---|---|---|---|
| 1 | Header cards | `DIFOT %`, `On-Time Pickup`, `On-Time Delivery`, `Truck Utilisation %` | Cards | Five-second read on network-wide landside health. |
| 2 | Carrier Composite Score, ranked | `Carrier Composite Score`, its four normalised components | Ranked bar, sorted descending, drillthrough enabled | The actual carrier-review artefact: who is winning and losing, and on which of the four weighted components. |
| 3 | Deadhead % vs. Truck Utilisation, by carrier | `Deadhead %`, `Truck Utilisation %` | Stacked bar (**not** 100%-stacked — see below), fixed 0-100% axis, by carrier | Reconciliation check (do the two sum near 100%, per the KPI dictionary's own watch-out) and a fleet-efficiency comparison in one visual. |
| 4 | DIFOT trend, by carrier (small multiples) | `DIFOT %` | Small multiple line charts | Is a given carrier's service level trending down before it shows up in the aggregate score. |
| 5 | Cost per km, by lane | `Cost per km` | Bar, by `TradeLane`/corridor | Where is landside cost structurally higher, informing lane-level rate negotiation. |
| 6 | Detention at site, by warehouse | `Avg Detention at Site Hours` | Table, sorted descending, flagged at the ~1-hour threshold | Which sites need an appointment-scheduling fix, a warehouse-side lever, not a carrier-side one. |
| 7 | Fuel surcharge recovery | `Fuel Surcharge Recovery` | Gauge or card against a 90-100% target band | Is fuel cost pass-through actually happening, a finance-facing check. |

The ranked bar (#2) is deliberately not a table of 16 raw KPI numbers. A carrier
review needs one ordered list a group can argue about, not a spreadsheet dump - the
composite score exists precisely so sixteen KPIs' worth of signal collapses into
one number people can rank, and the four component bars behind each carrier's total
let the conversation move immediately from "who is #12" to "why is #12 #12."

### Reusing Day 23's pattern: the reconciliation check as a visual

Visual #3 repeats a technique from yesterday in spirit, if not in specifics: the
KPI dictionary flags that `Truck Utilisation % + Deadhead % != 100%` is a genuine
data-quality signal (unaccounted distance) rather than a rounding artefact, and
that the two measures should be computed independently from `LoadedKm`/`EmptyKm`
rather than one derived from the other, precisely so a break is visible instead of
silently forced to reconcile. **This is why the chart is a plain stacked bar, not
a 100%-stacked one:** Power BI's 100%-stacked variant renormalises every carrier's
two segments to sum to exactly 100% of the bar's height by construction, which
hides precisely the gap this check exists to surface — every bar would reach the
top regardless of the underlying numbers. A plain stacked bar with the value axis
fixed to 0-100% shows each carrier's *actual* combined height: if a carrier's
stack doesn't reach the 100% gridline, that gap *is* the unaccounted distance,
sitting in the visual itself rather than in a footnote nobody reads. This is the
same instinct as Day 23's scatter plot: pick a chart type that makes the trap
visible rather than one that requires trusting a number in isolation — but it
means checking, before building, which of Power BI's two stacked-bar variants
actually preserves the thing you need to see.

### Carrier Composite Score, and why it needs a drillthrough

`LND.CAR.SCORE` is a min-max normalised weighted index
(`0.40 x NormOnTime + 0.25 x NormFirstAttempt + 0.20 x NormCostIndex +
0.15 x NormSubcontractDiscipline`, per the dictionary's own formula — note there is
no extra `(1 - ...)` wrapping the last two terms: the inversion for "lower cost and
lower subcontracting share score higher" is already baked into how `NormCostIndex`
and `NormSubcontractDiscipline` themselves are computed, so applying `1 -` again on
top of the already-inverted `Norm*` value would invert it a second time and make
cheaper carriers score *lower*), and the KPI dictionary's own watch-out is
explicit: **min-max normalisation is sensitive to the carrier population in
scope** - adding or removing one extreme carrier re-scales everyone else's score.
That means a single ranked bar chart, however well built, cannot show *why* carrier
#7 scored what it did without a second view. The fix is a drillthrough: right-click
a carrier bar, land on a "Carrier Detail" drillthrough page (built this week,
wired next week's model-performance pass if it's slow) showing that carrier's four
raw components, their normalised values, and where they sit against the current
population's min/max - so a reviewer can immediately tell whether a carrier's low
score is a real performance problem or an artefact of one outlier carrier dragging
the normalisation range.

### Filters on this page

Per Day 22's audit: `Period` and `TradeRegion` sync in from the shared set.
`Carrier` is page-specific (no other page's fact tables carry a carrier key) and
lets a reviewer pin the page to a shortlist ahead of a QBR. Add `DimCarrier[Mode]`
(road vs. rail, if the dimension carries it) or `PreferredTier` as an additional
page-local slicer if your build's `DimCarrier` supports it - check the actual
column list rather than assuming.

---

## Drill

### Exercise 24.1: the ranked composite score visual (30 min)
Build visual #2. Before wiring the drillthrough, predict: will the carrier ranked
#1 overall also rank #1 on every individual component, or will you see a carrier
with a strong on-time record and a weak cost index still land near the top because
of the weighting? State your prediction, then verify against your own Week 3
measures.

### Exercise 24.2: the reconciliation stacked bar (25 min)
Build visual #3. Predict, before checking, whether any carrier's stack visibly
fails to reach 100%. If none do in your build, that is a legitimate result (a
clean dataset for this particular check) - write one sentence on how you would
prove the check was actually run and not just assumed to pass, for a reader who
wasn't there when you built it.

### Exercise 24.3: carrier drillthrough page (25 min)
Build the "Carrier Detail" drillthrough page: the four raw components, their
normalised values, and the current population's min/max for cost index and
subcontract rate. Wire the drillthrough filter field (`CarrierCode`) and a Back
button. Test it by drilling from two different carriers and confirming the min/max
values shown are correctly population-wide (identical across both drills), not
carrier-specific.

### Exercise 24.4: detention-at-site audit (10 min)
Build visual #6. Identify which sites, if any, cross the ~1-hour average detention
threshold the KPI dictionary names as a trigger for an appointment-scheduling
review. Write one sentence distinguishing this from ocean detention (`OCN.REV.DET`)
- what unit each is measured in and why they must never be combined into one
"detention" card, per Day 1's demurrage/detention framing.

---

## Ship

Build page `2 Landside` with all seven visuals and the Carrier Detail drillthrough
page wired. Add any new measures (drillthrough-supporting normalisation-range
measures from Exercise 24.3) to `_Measures`, display folder `06 Landside\Quality &
Service` (alongside `Carrier Composite Score` itself, per Week 3 Day 15's
taxonomy).

```
git add .
git commit -m "Day 24: Landside dashboard, carrier scorecard and drillthrough"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Page `2 Landside` exists with all seven visuals, on-theme, nav bar intact.
- [ ] The ranked Carrier Composite Score visual exists and its drillthrough to
      Carrier Detail works from at least two different carriers.
- [ ] The Deadhead/Truck Utilisation reconciliation bar exists and you can state,
      from your own build, whether any carrier's stack falls short of 100%.
- [ ] You can explain, without notes, why the composite score's sensitivity to
      population changes makes a drillthrough necessary rather than optional.
- [ ] Detention-at-site sites flagged above the ~1-hour threshold, and you can
      state in one sentence why it must not be combined with ocean detention.
